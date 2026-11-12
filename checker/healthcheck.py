#!/usr/bin/env python3
"""
SLA health checker for OUR OWN services. A patch that breaks functionality
costs SLA points -- run this after every change so you catch it immediately.

Usage:
    python checker/healthcheck.py           # check once
    python checker/healthcheck.py --watch    # re-check every 15s
"""
import sys
import os
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402


def check_tcp(host, port):
    try:
        s = socket.create_connection((host, port), timeout=4)
        s.settimeout(3)
        try:
            s.recv(256)              # grab banner if any
            s.sendall(b"PING\n")
            s.recv(256)
        except socket.timeout:
            pass
        s.close()
        return True, "tcp ok"
    except Exception as e:
        return False, str(e)


def check_http(host, port):
    try:
        import requests
        r = requests.get(f"http://{host}:{port}/", timeout=4)
        return (r.status_code < 500), f"http {r.status_code}"
    except Exception as e:
        return False, str(e)


def run_once():
    host = config.OUR_HOST
    allok = True
    for svc in config.SERVICES:
        kind = svc.get("kind", "tcp")
        if kind == "http":
            ok, info = check_http(host, svc["port"])
        else:
            ok, info = check_tcp(host, svc["port"])
        allok &= ok
        mark = "UP  " if ok else "DOWN"
        print(f"[{mark}] {svc['name']:<10} {host}:{svc['port']:<6} {info}")
    return allok


if __name__ == "__main__":
    if "--watch" in sys.argv:
        while True:
            print(f"--- {time.strftime('%H:%M:%S')} ---")
            run_once()
            time.sleep(15)
    else:
        sys.exit(0 if run_once() else 1)
