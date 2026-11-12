#!/usr/bin/env python3
"""
Pre-match sanity check. Run this BEFORE the farm so you don't discover a typo in
the token / URL / flag regex while the clock is burning.

    python preflight.py                 # check everything
    python preflight.py --flag ABC123=  # also verify a real flag matches the regex

Exit code is non-zero if anything FAILs. WARNs are fine to launch with.
"""
import sys
import os
import re
import glob
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

G, Y, R, N = "\033[32m", "\033[33m", "\033[31m", "\033[0m"
_fails = 0
_warns = 0


def ok(msg):
    print(f"[{G}OK{N}]   {msg}")


def warn(msg):
    global _warns
    _warns += 1
    print(f"[{Y}WARN{N}] {msg}")


def fail(msg):
    global _fails
    _fails += 1
    print(f"[{R}FAIL{N}] {msg}")


def check_identity():
    if config.TEAM_TOKEN and config.TEAM_TOKEN != "CHANGEME_TEAM_TOKEN":
        ok(f"team token set ({config.TEAM_TOKEN[:4]}…)")
    else:
        fail("TEAM_TOKEN is still the placeholder — set it in config.py")
    ok(f"our team id = {config.OUR_TEAM_ID}")


def check_regex(sample):
    try:
        rx = re.compile(config.FLAG_REGEX)
        ok(f"FLAG_REGEX compiles: {config.FLAG_REGEX}")
    except re.error as e:
        fail(f"FLAG_REGEX does not compile: {e}")
        return
    if sample:
        if rx.search(sample):
            ok(f"sample flag matches regex: {sample}")
        else:
            fail(f"sample flag does NOT match regex: {sample}")


def check_targets():
    targets = list(config.iter_targets())
    if targets:
        ok(f"{len(targets)} targets (first: {targets[0]}, last: {targets[-1]})")
    else:
        fail("no targets — check TEAMS / TEAM_IP_PATTERN / TEAM_IDS")


def check_exploits():
    exps = [p for p in glob.glob(os.path.join(config.BASE_DIR, "exploits", "*.py"))
            if not os.path.basename(p).startswith(("template_", "_"))]
    if exps:
        ok(f"{len(exps)} exploit(s): " + ", ".join(os.path.basename(e) for e in exps))
    else:
        warn("no exploits yet (only templates) — nothing will be farmed until you add one")


def check_deps():
    for mod, needed_for in [("requests", "http submit / web exploits"),
                            ("pwn", "pwn & crypto exploits"),
                            ("scapy", "steal sniffer"),
                            ("rich", "dashboard")]:
        try:
            __import__(mod)
            ok(f"dependency '{mod}' present ({needed_for})")
        except ImportError:
            warn(f"dependency '{mod}' missing ({needed_for}) — run: bash setup.sh")


def check_submit_endpoint():
    if config.DRYRUN or config.SUBMIT_PROTO == "dryrun":
        warn("SUBMIT in DRYRUN mode — flags will NOT be sent (fine for testing)")
        return
    if config.SUBMIT_PROTO == "http":
        try:
            import requests
            # non-destructive: OPTIONS, never submits a flag
            r = requests.options(config.SUBMIT_URL, timeout=6)
            ok(f"submit endpoint reachable: {config.SUBMIT_URL} (HTTP {r.status_code})")
        except Exception as e:
            fail(f"submit endpoint unreachable: {config.SUBMIT_URL} — {e}")
    elif config.SUBMIT_PROTO == "tcp":
        try:
            s = socket.create_connection((config.SUBMIT_HOST, config.SUBMIT_PORT), timeout=6)
            s.settimeout(3)
            try:
                banner = s.recv(128).decode(errors="replace").strip()
            except socket.timeout:
                banner = "(no banner)"
            s.close()
            ok(f"submit server reachable: {config.SUBMIT_HOST}:{config.SUBMIT_PORT} [{banner}]")
        except Exception as e:
            fail(f"submit server unreachable: {config.SUBMIT_HOST}:{config.SUBMIT_PORT} — {e}")
    else:
        fail(f"unknown SUBMIT_PROTO: {config.SUBMIT_PROTO!r}")


def main():
    sample = None
    if "--flag" in sys.argv:
        sample = sys.argv[sys.argv.index("--flag") + 1]
    print("=== redrizz preflight ===")
    check_identity()
    check_regex(sample)
    check_targets()
    check_exploits()
    check_deps()
    check_submit_endpoint()
    print(f"\nsummary: {_fails} FAIL, {_warns} WARN")
    if _fails:
        print(f"{R}NOT ready — fix the FAILs above.{N}")
        sys.exit(1)
    print(f"{G}ready to launch.{N}")


if __name__ == "__main__":
    main()
