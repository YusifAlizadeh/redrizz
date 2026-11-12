"""
SQLite-backed flag store. The flag string is the primary key, so inserting the
same flag twice (same flag seen from two exploits / two ticks) is a no-op --
natural dedupe, which is exactly what an A-D farm needs.

Statuses:
    QUEUED    freshly captured, not yet submitted
    ACCEPTED  scoring server accepted it (points!)
    REJECTED  permanently rejected (own flag / too old / invalid)
    RETRY     temporary reject (not active yet / rate limited) -> try again
    SKIPPED   expired (older than FLAG_LIFETIME) or gave up (over FLAG_MAX_TRIES)
"""
import sqlite3
import time
import threading

QUEUED, ACCEPTED, REJECTED, RETRY, SKIPPED = (
    "QUEUED", "ACCEPTED", "REJECTED", "RETRY", "SKIPPED")

_lock = threading.Lock()


class FlagDB:
    def __init__(self, path):
        # check_same_thread=False + our own lock -> safe across farm threads.
        # WAL + busy_timeout -> a separate dashboard process can read while the
        # farm writes without "database is locked".
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=5)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
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
        """Return flags that are QUEUED or ready-to-RETRY, NEWEST FIRST.

        Newest-first matters under rate limiting: fresh flags are the ones still
        worth points, so they jump the queue ahead of near-expired ones.
        """
        with _lock:
            rows = self.conn.execute(
                "SELECT flag FROM flags WHERE status IN (?,?) "
                "ORDER BY first_ts DESC LIMIT ?",
                (QUEUED, RETRY, limit),
            ).fetchall()
        return [r[0] for r in rows]

    def reap(self, lifetime, max_tries):
        """Retire flags that can no longer score: too old (older than lifetime,
        if lifetime > 0) or tried too many times. Marked SKIPPED so they leave
        the submit queue but still show up in counts(). Returns #reaped."""
        now = time.time()
        with _lock:
            n = 0
            if lifetime and lifetime > 0:
                cur = self.conn.execute(
                    "UPDATE flags SET status=? WHERE status IN (?,?) "
                    "AND first_ts < ?",
                    (SKIPPED, QUEUED, RETRY, now - lifetime),
                )
                n += cur.rowcount
            cur = self.conn.execute(
                "UPDATE flags SET status=? WHERE status IN (?,?) AND tries >= ?",
                (SKIPPED, QUEUED, RETRY, max_tries),
            )
            n += cur.rowcount
            self.conn.commit()
            return n

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

    def stats(self):
        """Aggregates for the dashboard (read-only, cheap)."""
        now = time.time()
        with _lock:
            by_status = {
                s: c for s, c in self.conn.execute(
                    "SELECT status, COUNT(*) FROM flags GROUP BY status"
                ).fetchall()
            }
            # per exploit: total / accepted / rejected
            per_exploit = {}
            for exp, st, c in self.conn.execute(
                "SELECT exploit, status, COUNT(*) FROM flags GROUP BY exploit, status"
            ).fetchall():
                row = per_exploit.setdefault(exp or "?", {"total": 0, "acc": 0, "rej": 0})
                row["total"] += c
                if st == ACCEPTED:
                    row["acc"] += c
                elif st in (REJECTED, SKIPPED):
                    row["rej"] += c
            # per target totals
            per_target = {
                (t or "?"): c for t, c in self.conn.execute(
                    "SELECT target, COUNT(*) FROM flags GROUP BY target"
                ).fetchall()
            }
            acc_last_60 = self.conn.execute(
                "SELECT COUNT(*) FROM flags WHERE status=? AND last_ts >= ?",
                (ACCEPTED, now - 60),
            ).fetchone()[0]
        return {
            "by_status": by_status,
            "per_exploit": per_exploit,
            "per_target": per_target,
            "accepted_last_60": acc_last_60,
        }
