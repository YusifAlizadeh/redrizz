"""
Central configuration for the redrizz Attack-Defense toolkit.

EVERYTHING the farm, submitter, sniffer and checker need lives here so that on
match day you only edit ONE file. Values marked  <<< EDIT  are the ones you will
almost certainly change once the rules / scoring API are handed out.
"""

# ---------------------------------------------------------------------------
# Team identity
# ---------------------------------------------------------------------------
TEAM_TOKEN = "CHANGEME_TEAM_TOKEN"      # <<< EDIT  your team's submission token
OUR_TEAM_ID = 0                          # <<< EDIT  your own team id (skipped when attacking)

# ---------------------------------------------------------------------------
# Flag format
# ---------------------------------------------------------------------------
# Classic jeopardy/A-D format: 31 upper/alnum chars + '='.  Replace with the
# real regex the moment you see a sample flag.
FLAG_REGEX = r"[A-Z0-9]{31}="            # <<< EDIT when you see a real flag

# ---------------------------------------------------------------------------
# Targets  --  either list IPs explicitly, or use the pattern + id range.
# The game network is usually a /24 per team, e.g. 10.60.<id>.1
# ---------------------------------------------------------------------------
TEAM_IP_PATTERN = "10.60.{id}.1"         # <<< EDIT  use "{id}" where the team id goes
TEAM_IDS = range(1, 11)                  # <<< EDIT  inclusive-exclusive range of team ids
# If you prefer a hand-written list, fill TEAMS and it overrides the pattern:
TEAMS: list[str] = []                    # e.g. ["10.60.1.1", "10.60.2.1"]

# ---------------------------------------------------------------------------
# Farm timing / concurrency
# ---------------------------------------------------------------------------
TICK_SECONDS = 120        # how often each exploit is re-run against every team
EXPLOIT_TIMEOUT = 25      # hard kill an exploit after this many seconds
FARM_THREADS = 32         # parallel (exploit x target) jobs

# ---------------------------------------------------------------------------
# Flag submission
# ---------------------------------------------------------------------------
SUBMIT_PROTO = "http"     # "http" | "tcp" | "dryrun"
DRYRUN = False            # if True, nothing is actually sent (logs only)

# --- HTTP submitter (most modern A-D systems: Forcad / custom) -------------
SUBMIT_URL = "http://10.10.10.10/flags"   # <<< EDIT  scoring endpoint
# How the token is sent: "header" or "json"
SUBMIT_TOKEN_MODE = "header"
SUBMIT_TOKEN_FIELD = "X-Team-Token"       # header name, or json key if json mode
# Body shape: "json_list"  -> POST ["FLAG1","FLAG2"]
#             "json_field" -> POST {"flags": [...]}
#             "text_lines" -> raw body, one flag per line
SUBMIT_BODY_MODE = "json_list"
SUBMIT_FLAGS_FIELD = "flags"              # used only for json_field

# --- TCP submitter (older A-D systems: connect, send flags line by line) ---
SUBMIT_HOST = "10.10.10.10"               # <<< EDIT
SUBMIT_PORT = 31337                       # <<< EDIT
SUBMIT_TCP_GREETING_LINES = 1             # lines to read/skip after connect (banner)
SUBMIT_TCP_SEND_TOKEN_FIRST = True        # send TEAM_TOKEN as first line

# --- Response classification (works for both protocols) -------------------
# The submitter reads the server's per-flag response text and classifies it.
# Match is case-insensitive substring. Edit these to the game's wording.
ACCEPT_WORDS = ["accepted", "ok", "congrat", "valid", "+"]
REJECT_WORDS = ["invalid", "own flag", "nop team", "not found", "too old",
                "expired", "already", "stolen"]
RETRY_WORDS  = ["not yet", "queue", "rate", "try again", "wait", "throttle"]

SUBMIT_BATCH = 50         # max flags per submission request
SUBMIT_PERIOD = 5         # seconds between submission flushes

# ---------------------------------------------------------------------------
# Services we DEFEND  --  used by the sniffer (which ports to watch) and the
# healthcheck (what to probe).  Add one entry per service.
# ---------------------------------------------------------------------------
SERVICES = [
    # name,            port,  kind ("tcp"|"http")
    {"name": "svc1",   "port": 9001, "kind": "tcp"},
    {"name": "webshop","port": 8080, "kind": "http"},
]
OUR_HOST = "127.0.0.1"    # <<< EDIT  our own vulnbox IP (for healthcheck)
CAPTURE_IFACE = None      # None = default iface; or e.g. "eth0" for the sniffer

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLAG_DB = os.path.join(BASE_DIR, "flags.sqlite")
CAPTURE_DIR = os.path.join(BASE_DIR, "steal", "captured")
LOG_DIR = os.path.join(BASE_DIR, "logs")


def iter_targets():
    """Yield every opponent IP, skipping our own team."""
    if TEAMS:
        for ip in TEAMS:
            yield ip
        return
    for tid in TEAM_IDS:
        if tid == OUR_TEAM_ID:
            continue
        yield TEAM_IP_PATTERN.format(id=tid)
