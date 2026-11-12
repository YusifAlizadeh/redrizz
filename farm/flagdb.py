"""
SQLite-backed flag store. The flag string is the primary key, so inserting the
same flag twice (same flag seen from two exploits / two ticks) is a no-op --
natural dedupe, which is exactly what an A-D farm needs.

Statuses:
    QUEUED    freshly captured, not yet submitted
    ACCEPTED  scoring server accepted it (points!)
    REJECTED  permanently rejected (own flag / too old / invalid)
    RETRY     temporary reject (not active yet / rate limited) -> try again
"""
import sqlite3
import time
import threading

QUEUED, ACCEPTED, REJECTED, RETRY = "QUEUED", "ACCEPTED", "REJECTED", "RETRY"

_lock = threading.Lock()


class FlagDB:
    def __init__(self, path):
        # check_same_thread=False + our own lock -> safe across farm threads
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS flags (
                   flag     TEXT PRIMARY KEY,
                   status   TEXT NOT NULL,
                   exploit  TEXT,
                   target   TEXT,
                   first_ts REAL,
                   last_ts  REAL,
                   tries    INTEGER DEFAULT 0,
                   response TEXT
               )"""
        )
        self.conn.commit()

    def add(self, flag, exploit, target):
        """Insert a freshly captured flag. Returns True if it was new."""
        now = time.time()
        with _lock:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO flags "
                "(flag,status,exploit,target,first_ts,last_ts) "
                "VALUES (?,?,?,?,?,?)",
                (flag, QUEUED, exploit, target, now, now),
            )
            self.conn.commit()
            return cur.rowcount == 1

    def take_submittable(self, limit):
        """Return flags that are QUEUED or ready-to-RETRY."""
        with _lock:
            rows = self.conn.execute(
                "SELECT flag FROM flags WHERE status IN (?,?) "
                "ORDER BY first_ts LIMIT ?",
                (QUEUED, RETRY, limit),
            ).fetchall()
        return [r[0] for r in rows]

    def mark(self, flag, status, response=""):
        now = time.time()
        with _lock:
            self.conn.execute(
                "UPDATE flags SET status=?, last_ts=?, tries=tries+1, response=? "
                "WHERE flag=?",
                (status, now, response[:200], flag),
            )
            self.conn.commit()

    def counts(self):
        with _lock:
            rows = self.conn.execute(
                "SELECT status, COUNT(*) FROM flags GROUP BY status"
            ).fetchall()
        return {s: c for s, c in rows}
