"""
Flag submitter. Runs as a background thread inside the farm (or standalone).
Pulls QUEUED/RETRY flags from the FlagDB, submits them via the configured
protocol, and classifies each per-flag response as ACCEPTED / REJECTED / RETRY.

Supports three protocols via config.SUBMIT_PROTO:
    "http"   POST to a scoring API (json list / json field / text lines)
    "tcp"    connect, optional banner + token, send flags line by line
    "dryrun" log only, never touch the network
"""
import sys
import os
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from farm import flagdb  # noqa: E402


def _classify(response_text):
    low = (response_text or "").lower()
    for w in config.ACCEPT_WORDS:
        if w.lower() in low:
            return flagdb.ACCEPTED
    for w in config.RETRY_WORDS:
        if w.lower() in low:
            return flagdb.RETRY
    for w in config.REJECT_WORDS:
        if w.lower() in low:
            return flagdb.REJECTED
    # Unknown wording -> be conservative, retry rather than drop a live flag.
    return flagdb.RETRY


# --------------------------------------------------------------------------- #
# Protocol back-ends: each returns {flag: response_text}
# --------------------------------------------------------------------------- #
def _submit_http(flags):
    import requests
    headers = {}
    payload = None
    data = None
    if config.SUBMIT_TOKEN_MODE == "header":
        headers[config.SUBMIT_TOKEN_FIELD] = config.TEAM_TOKEN

    if config.SUBMIT_BODY_MODE == "json_list":
        payload = flags
    elif config.SUBMIT_BODY_MODE == "json_field":
        payload = {config.SUBMIT_FLAGS_FIELD: flags}
        if config.SUBMIT_TOKEN_MODE == "json":
            payload[config.SUBMIT_TOKEN_FIELD] = config.TEAM_TOKEN
    elif config.SUBMIT_BODY_MODE == "text_lines":
        data = "\n".join(flags)

    try:
        if data is not None:
            r = requests.put(config.SUBMIT_URL, data=data, headers=headers, timeout=10)
        else:
            r = requests.put(config.SUBMIT_URL, json=payload, headers=headers, timeout=10)
    except Exception:
        # network blip: retry everything
        return {f: "retry network error" for f in flags}

    # Ideal case: server returns JSON [{"flag":..,"msg":..}, ...]
    try:
        body = r.json()
        if isinstance(body, list) and body and isinstance(body[0], dict):
            out = {}
            for item in body:
                fl = item.get("flag") or item.get("Flag")
                msg = str(item.get("msg") or item.get("status") or item)
                if fl:
                    out[fl] = msg
            if out:
                return out
    except Exception:
        pass
    # Fallback: apply the whole-response text to every flag in the batch.
    return {f: r.text for f in flags}


def _submit_tcp(flags):
    out = {}
    try:
        s = socket.create_connection((config.SUBMIT_HOST, config.SUBMIT_PORT), timeout=10)
        s.settimeout(5)
        f = s.makefile("rwb", buffering=0)
        for _ in range(config.SUBMIT_TCP_GREETING_LINES):
            f.readline()
        if config.SUBMIT_TCP_SEND_TOKEN_FIRST:
            f.write((config.TEAM_TOKEN + "\n").encode())
        for fl in flags:
            f.write((fl + "\n").encode())
            try:
                resp = f.readline().decode(errors="replace").strip()
            except socket.timeout:
                resp = "retry timeout"
            out[fl] = resp
        s.close()
    except Exception as e:  # noqa: BLE001
        return {fl: f"retry conn error {e}" for fl in flags}
    return out


def _submit_dryrun(flags):
    return {f: "accepted (dryrun)" for f in flags}


def submit_batch(flags):
    if not flags:
        return {}
    if config.DRYRUN or config.SUBMIT_PROTO == "dryrun":
        return _submit_dryrun(flags)
    if config.SUBMIT_PROTO == "http":
        return _submit_http(flags)
    if config.SUBMIT_PROTO == "tcp":
        return _submit_tcp(flags)
    raise ValueError(f"unknown SUBMIT_PROTO {config.SUBMIT_PROTO!r}")


def run_once(db):
    """One flush: retire dead flags, take a batch, submit, record. Returns #accepted."""
    db.reap(getattr(config, "FLAG_LIFETIME", 0), getattr(config, "FLAG_MAX_TRIES", 15))
    flags = db.take_submittable(config.SUBMIT_BATCH)
    if not flags:
        return 0
    results = submit_batch(flags)
    accepted = 0
    for fl in flags:
        resp = results.get(fl, "")
        status = _classify(resp)
        db.mark(fl, status, resp)
        if status == flagdb.ACCEPTED:
            accepted += 1
    return accepted


def loop(db, stop_event=None):
    """Background submission loop."""
    while stop_event is None or not stop_event.is_set():
        try:
            n = run_once(db)
            if n:
                print(f"[submitter] +{n} accepted  {db.counts()}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[submitter] error: {e}", flush=True)
        time.sleep(config.SUBMIT_PERIOD)


if __name__ == "__main__":
    # Standalone: keep flushing whatever the farm queues into the DB.
    database = flagdb.FlagDB(config.FLAG_DB)
    print(f"[submitter] standalone, proto={config.SUBMIT_PROTO} dryrun={config.DRYRUN}")
    loop(database)
