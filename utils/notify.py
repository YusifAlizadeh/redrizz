#!/usr/bin/env python3
"""
Tiny notifier used by the healthcheck on service UP<->DOWN transitions.
Modes (config.NOTIFY): "none" | "bell" | "telegram".
Always safe to call; never raises.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402


def notify(msg):
    mode = getattr(config, "NOTIFY", "bell")
    try:
        print(f"[notify] {msg}", flush=True)
        if mode == "none":
            return
        if mode in ("bell", "telegram"):
            sys.stderr.write("\a")   # terminal bell
            sys.stderr.flush()
        if mode == "telegram" and config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT:
            import requests
            requests.get(
                f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                params={"chat_id": config.TELEGRAM_CHAT, "text": msg},
                timeout=5,
            )
    except Exception:
        pass   # a broken notifier must never take down the checker


if __name__ == "__main__":
    notify(" ".join(sys.argv[1:]) or "test notification")
