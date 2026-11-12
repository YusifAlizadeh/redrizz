#!/usr/bin/env python3
"""
Traffic-steal sniffer. Watches the ports of OUR defended services. When a flag
leaves one of our services, it dumps the FULL inbound request that caused the
leak -- i.e. an opponent's exploit -- to steal/captured/<svc>/. Feed those to
steal/replay.py to fire the same exploit back at every team.

Needs root (raw sockets). scapy required.

Usage:
    sudo python steal/sniffer.py              # live capture on CAPTURE_IFACE
    python steal/sniffer.py --pcap dump.pcap  # offline: mine an existing pcap
"""
import sys
import os
import re
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

FLAG_RE = re.compile(config.FLAG_REGEX)
PORT2SVC = {s["port"]: s for s in config.SERVICES}
SERVICE_PORTS = set(PORT2SVC)

# per-connection buffers: key -> {"in": b"", "out": b"", "saved": bool}
streams = {}


def _key(ip_a, pa, ip_b, pb):
    # canonical per-connection key independent of direction
    return tuple(sorted([(ip_a, pa), (ip_b, pb)]))


def save_attack(svc, peer_ip, inbound):
    d = os.path.join(config.CAPTURE_DIR, svc["name"])
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, f"{int(time.time())}_{peer_ip.replace(':', '_')}.json")
    rec = {
        "service": svc["name"],
        "port": svc["port"],
        "kind": svc.get("kind", "tcp"),
        "peer": peer_ip,
        "ts": time.time(),
        "payload_hex": inbound.hex(),
    }
    with open(fn, "w") as f:
        json.dump(rec, f, indent=2)
    print(f"[sniffer] STOLE attack on {svc['name']} from {peer_ip} -> {fn} "
          f"({len(inbound)} bytes)", flush=True)


def on_packet(pkt):
    from scapy.all import IP, TCP, Raw
    if IP not in pkt or TCP not in pkt:
        return
    ip = pkt[IP]
    tcp = pkt[TCP]
    payload = bytes(pkt[Raw].load) if Raw in pkt else b""
    if not payload:
        return

    sport, dport = tcp.sport, tcp.dport
    if dport in SERVICE_PORTS:          # client -> our service (the attack)
        svc_port, direction, peer = dport, "in", (ip.src, sport)
    elif sport in SERVICE_PORTS:        # our service -> client (maybe a flag)
        svc_port, direction, peer = sport, "out", (ip.dst, dport)
    else:
        return

    k = _key(ip.src, sport, ip.dst, dport)
    st = streams.setdefault(k, {"in": b"", "out": b"", "saved": False, "peer": peer[0]})
    st[direction] += payload

    if direction == "out" and not st["saved"] and FLAG_RE.search(st["out"].decode("latin1")):
        # a flag just left our service on this connection -> steal the request
        if st["in"]:
            save_attack(PORT2SVC[svc_port], st["peer"], st["in"])
            st["saved"] = True


def main():
    try:
        from scapy.all import sniff, rdpcap
    except ImportError:
        sys.exit("scapy not installed -- run: pip install scapy")

    os.makedirs(config.CAPTURE_DIR, exist_ok=True)
    bpf = " or ".join(f"tcp port {p}" for p in SERVICE_PORTS) or "tcp"

    if "--pcap" in sys.argv:
        path = sys.argv[sys.argv.index("--pcap") + 1]
        print(f"[sniffer] offline mining {path} (ports {sorted(SERVICE_PORTS)})")
        for pkt in rdpcap(path):
            on_packet(pkt)
        print("[sniffer] done.")
        return

    print(f"[sniffer] live capture iface={config.CAPTURE_IFACE or 'default'} "
          f"filter='{bpf}'  (needs root)")
    sniff(filter=bpf, prn=on_packet, store=False, iface=config.CAPTURE_IFACE)


if __name__ == "__main__":
    main()
