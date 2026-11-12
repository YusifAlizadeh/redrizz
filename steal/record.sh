#!/usr/bin/env bash
# Continuously record traffic on our service ports into rotating pcaps, so the
# sniffer can mine them offline (sudo python steal/sniffer.py --pcap <file>).
# Needs root. Rotates a new file every 60s. Ctrl-C to stop.
set -e
cd "$(dirname "$0")/.."
mkdir -p steal/pcaps

# Build a BPF filter from the SERVICES ports in config.py
PORTS=$(python - <<'PY'
import config
print(" or ".join(f"tcp port {s['port']}" for s in config.SERVICES))
PY
)
echo "[*] recording: $PORTS  -> steal/pcaps/  (new file every 60s)"
exec sudo tcpdump -i "${1:-any}" -G 60 -w "steal/pcaps/%Y%m%d-%H%M%S.pcap" -s 0 $PORTS
