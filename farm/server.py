"""
Farm orchestrator -- the heart of the red-team toolkit.

Every TICK_SECONDS it runs each exploit in exploits/ (anything not named
template_*) against EVERY opponent target, in parallel. It scrapes flags from
each exploit's stdout with FLAG_REGEX, dedupes them into the FlagDB, and a
background submitter thread ships them to the scoring server.

Add an exploit mid-match by dropping a new file in exploits/ -- it is picked up
automatically on the next tick. No restart needed.

Usage:
    python farm/server.py            # run forever, one tick per TICK_SECONDS
    python farm/server.py --once     # run a single tick and exit (for testing)
"""
import sys
import os
import re
import glob
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from farm import flagdb, runner, submitter  # noqa: E402

FLAG_RE = re.compile(config.FLAG_REGEX)
EXPLOIT_DIR = os.path.join(config.BASE_DIR, "exploits")


def discover_exploits():
    """Every .py in exploits/ except templates and dunder files."""
    out = []
    for path in sorted(glob.glob(os.path.join(EXPLOIT_DIR, "*.py"))):
        name = os.path.basename(path)
        if name.startswith("template_") or name.startswith("_"):
            continue
        out.append(path)
    return out


def one_job(db, exploit_path, target):
    name = os.path.basename(exploit_path)
    stdout, stderr, rc = runner.run_exploit(exploit_path, target, config.EXPLOIT_TIMEOUT)
    flags = set(FLAG_RE.findall(stdout))
    new = 0
    for fl in flags:
        if db.add(fl, name, target):
            new += 1
    if rc not in (0, -1) and not flags:
        # surface genuine errors but keep them short
        err = (stderr or "").strip().splitlines()[-1:] or [""]
        print(f"  [!] {name} vs {target} rc={rc} {err[0][:120]}", flush=True)
    return name, target, len(flags), new


def tick(db):
    exploits = discover_exploits()
    targets = list(config.iter_targets())
    if not exploits:
        print("[farm] no exploits in exploits/ yet -- drop one in from a template.", flush=True)
        return
    print(f"[farm] tick: {len(exploits)} exploit(s) x {len(targets)} target(s)", flush=True)
    jobs = [(e, t) for e in exploits for t in targets]
    total_flags = total_new = 0
    per_exploit = {}
    with ThreadPoolExecutor(max_workers=config.FARM_THREADS) as pool:
        futs = [pool.submit(one_job, db, e, t) for e, t in jobs]
        for fut in as_completed(futs):
            name, target, got, new = fut.result()
            total_flags += got
            total_new += new
            per_exploit[name] = per_exploit.get(name, 0) + new
    hot = ", ".join(f"{os.path.basename(k)}:{v}" for k, v in per_exploit.items() if v)
    print(f"[farm] tick done: {total_flags} flags seen, {total_new} new "
          f"[{hot}]  db={db.counts()}", flush=True)


def main():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    db = flagdb.FlagDB(config.FLAG_DB)

    # background submitter
    stop = threading.Event()
    t = threading.Thread(target=submitter.loop, args=(db, stop), daemon=True)
    t.start()

    once = "--once" in sys.argv
    print(f"[farm] start  proto={config.SUBMIT_PROTO} dryrun={config.DRYRUN} "
          f"tick={config.TICK_SECONDS}s targets={len(list(config.iter_targets()))}")
    try:
        while True:
            start = time.time()
            tick(db)
            if once:
                # give the submitter a moment to flush, then report
                time.sleep(config.SUBMIT_PERIOD + 1)
                submitter.run_once(db)
                print(f"[farm] --once complete  db={db.counts()}")
                break
            elapsed = time.time() - start
            time.sleep(max(1, config.TICK_SECONDS - elapsed))
    except KeyboardInterrupt:
        print("\n[farm] stopping...")
    finally:
        stop.set()


if __name__ == "__main__":
    main()
