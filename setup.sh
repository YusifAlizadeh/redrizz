#!/usr/bin/env bash
# One-shot environment setup for the redrizz A-D toolkit.
set -e
echo "[*] Installing Python deps..."
pip install --upgrade pip
pip install -r requirements.txt
echo "[*] Installing tcpdump (sniffer fallback)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y tcpdump
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm tcpdump
else
    echo "[!] Install tcpdump manually for your distro."
fi
echo "[+] Done. Edit config.py, then: python farm/server.py"
