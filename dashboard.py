#!/usr/bin/env python3
"""
Live match dashboard. Read-only view of flags.sqlite + SLA of our services.

    python dashboard.py            # live, refresh every 2s (rich)
    python dashboard.py --once     # render a single frame and exit (testing / non-tty)

Shows: flag status counts, accept-rate, flags accepted in the last 60s, a
per-exploit breakdown (spot which exploit got patched / stopped earning), and
UP/DOWN for each service you defend.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from farm import flagdb  # noqa: E402
from checker import healthcheck  # noqa: E402

START = time.time()


def gather():
    db = flagdb.FlagDB(config.FLAG_DB)
    st = db.stats()
    # SLA (silent: no notify from the dashboard)
    sla = []
    for svc in config.SERVICES:
        if svc.get("kind") == "http":
            up, info = healthcheck.check_http(config.OUR_HOST, svc["port"])
        else:
            up, info = healthcheck.check_tcp(config.OUR_HOST, svc["port"])
        sla.append((svc["name"], svc["port"], up, info))
    return st, sla


def _accept_rate(by_status):
    acc = by_status.get("ACCEPTED", 0)
    rej = by_status.get("REJECTED", 0) + by_status.get("SKIPPED", 0)
    done = acc + rej
    return (100.0 * acc / done) if done else 0.0


# --------------------------------------------------------------------------- #
# rich renderer
# --------------------------------------------------------------------------- #
def render_rich(st, sla):
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns

    bs = st["by_status"]
    up_m = int(time.time() - START) // 60
    header = (f"proto=[b]{config.SUBMIT_PROTO}[/] dryrun={config.DRYRUN}  "
              f"tick={config.TICK_SECONDS}s  targets={len(list(config.iter_targets()))}  "
              f"uptime={up_m}m   accept-rate=[b]{_accept_rate(bs):.0f}%[/]  "
              f"accepted/60s=[b green]{st['accepted_last_60']}[/]")

    status_tbl = Table(title="flags", expand=True)
    status_tbl.add_column("status")
    status_tbl.add_column("count", justify="right")
    for s in ("QUEUED", "RETRY", "ACCEPTED", "REJECTED", "SKIPPED"):
        color = {"ACCEPTED": "green", "REJECTED": "red", "SKIPPED": "yellow"}.get(s, "")
        status_tbl.add_row(f"[{color}]{s}[/]" if color else s, str(bs.get(s, 0)))

    exp_tbl = Table(title="per exploit", expand=True)
    for c in ("exploit", "flags", "acc", "rej"):
        exp_tbl.add_column(c, justify="right" if c != "exploit" else "left")
    for name, row in sorted(st["per_exploit"].items(),
                            key=lambda kv: kv[1]["acc"], reverse=True):
        exp_tbl.add_row(name, str(row["total"]),
                        f"[green]{row['acc']}[/]", f"[red]{row['rej']}[/]")

    sla_tbl = Table(title="our services (SLA)", expand=True)
    for c in ("service", "port", "state"):
        sla_tbl.add_column(c)
    for name, port, up, info in sla:
        sla_tbl.add_row(name, str(port),
                        "[green]UP[/]" if up else f"[red]DOWN[/] {info[:30]}")

    return Panel(Columns([status_tbl, exp_tbl, sla_tbl]),
                 title="[b]redrizz dashboard[/]", subtitle=header)


def render_plain(st, sla):
    bs = st["by_status"]
    lines = ["=== redrizz dashboard (plain) ===",
             f"proto={config.SUBMIT_PROTO} dryrun={config.DRYRUN} "
             f"accept-rate={_accept_rate(bs):.0f}% accepted/60s={st['accepted_last_60']}",
             "flags: " + "  ".join(f"{k}={v}" for k, v in bs.items()),
             "per exploit:"]
    for name, row in sorted(st["per_exploit"].items(),
                            key=lambda kv: kv[1]["acc"], reverse=True):
        lines.append(f"  {name:<22} flags={row['total']} acc={row['acc']} rej={row['rej']}")
    lines.append("services:")
    for name, port, up, info in sla:
        lines.append(f"  [{'UP' if up else 'DOWN'}] {name}:{port} {'' if up else info[:40]}")
    return "\n".join(lines)


def main():
    once = "--once" in sys.argv
    try:
        from rich.console import Console
        from rich.live import Live
        have_rich = True
    except ImportError:
        have_rich = False

    if not have_rich:
        st, sla = gather()
        print(render_plain(st, sla))
        if once:
            return
        while True:
            time.sleep(2)
            st, sla = gather()
            print("\n" + render_plain(st, sla))
        return

    console = Console()
    if once:
        st, sla = gather()
        console.print(render_rich(st, sla))
        return
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            st, sla = gather()
            live.update(render_rich(st, sla))
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
