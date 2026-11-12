#!/usr/bin/env python3
"""
Tiny vulnerable TCP service for OFFLINE testing of the whole toolkit.

It mimics an A-D service: it stores a rotating flag and leaks it to anyone who
sends the "vulnerable" command. Use it to prove the farm -> submitter path and
the sniffer -> replay path work before match day. NOT for the real competition.

Protocol (line based):
    PING              -> PONG                 (used by the healthcheck)
    GET /note/1       -> the current flag     (the "IDOR" vuln the example abuses)
    anything else     -> "?"

Run:  python utils/testservice.py [port]
"""
import socket
import socketserver
import random
import string
import threading
import sys
import time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
_flag = {"v": ""}


def _rotate():
    while True:
        _flag["v"] = "".join(random.choices(string.ascii_uppercase + string.digits, k=31)) + "="
        time.sleep(30)  # flags rotate, like a real A-D round


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"welcome to vulnservice\n")
        for raw in self.rfile:
            cmd = raw.decode(errors="replace").strip()
            if cmd == "PING":
                self.wfile.write(b"PONG\n")
            elif cmd == "GET /note/1":
                # the vulnerability: no auth check -> flag leaks
                self.wfile.write((_flag["v"] + "\n").encode())
            elif not cmd:
                continue
            else:
                self.wfile.write(b"?\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    threading.Thread(target=_rotate, daemon=True).start()
    while not _flag["v"]:
        time.sleep(0.05)
    print(f"[testservice] listening on 127.0.0.1:{PORT}  (flag rotates every 30s)")
    Server(("0.0.0.0", PORT), Handler).serve_forever()
