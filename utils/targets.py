#!/usr/bin/env python3
"""
Target helper. Prints the list of opponent IPs the farm will attack, so you can
eyeball it before launching. Driven entirely by config.py.

Usage:  python utils/targets.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

if __name__ == "__main__":
    targets = list(config.iter_targets())
    print(f"# {len(targets)} targets (our team id {config.OUR_TEAM_ID} excluded)")
    for ip in targets:
        print(ip)
