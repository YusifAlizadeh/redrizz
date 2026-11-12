# redrizz — Attack-Defense Red-Team Toolkit

Infrastructure for an A/D CTF. You don't pre-build exploits (you get the services
at kickoff) — you pre-build the machine that **runs one exploit against every team
and auto-submits the flags**. Write the exploit once, score everywhere.

```
config.py        <- the ONLY file you edit on match day
farm/            <- runs every exploit x every team each tick, submits flags
exploits/        <- your exploits (+ templates to copy); farm auto-loads new ones
steal/           <- sniff opponents' attacks on your box, replay them back
checker/         <- SLA health of your own services
utils/           <- target list + a local test service for offline practice
```

## 0. Setup (do this tonight)

```bash
bash setup.sh                 # pwntools, requests, scapy, tcpdump
```

## 1. Match-day config (fill config.py)

Edit the lines marked `<<< EDIT`:
- `TEAM_TOKEN`, `OUR_TEAM_ID`
- `FLAG_REGEX` — paste the real regex the second you see a flag
- `TEAM_IP_PATTERN` + `TEAM_IDS` (or hand-fill `TEAMS`)
- Submission block: set `SUBMIT_PROTO` (`http`/`tcp`), the URL/host, how the token
  is sent, and the `ACCEPT_WORDS/REJECT_WORDS/RETRY_WORDS` to the game's wording
- `SERVICES` — one entry per service you defend (name, port, kind)

Sanity check your target list:
```bash
python utils/targets.py
```

## 2. Launch the farm

```bash
python farm/server.py            # loops forever, one tick per TICK_SECONDS
python farm/server.py --once     # single tick (testing)
```
The submitter runs inside it as a background thread. Watch the per-exploit flag
counts to see which exploit is earning.

## 3. Add an exploit in 60 seconds

1. Copy a template: `cp exploits/template_web.py exploits/webshop.py`
2. Fill the `# TODO` with the bug. **Rule: print flags to stdout, one per line.**
3. Test it alone: `python exploits/webshop.py 10.60.2.1`
4. Drop it in `exploits/` — the farm picks it up on the next tick. No restart.

## 4. Steal opponents' exploits (big points)

```bash
sudo python steal/sniffer.py              # watch your service ports
python steal/replay.py --list             # what you've captured
python steal/replay.py --latest webshop   # fire newest stolen attack at all teams
```
To farm a stolen attack continuously, wrap it as an exploit:
```bash
cat > exploits/stolen_webshop.py <<'PY'
import os
os.execvp("python", ["python", "steal/replay.py", "--latest", "webshop", "--target", __import__("sys").argv[1]])
PY
```

## 5. Defend your SLA

```bash
python checker/healthcheck.py --watch     # alerts if a patch broke a service
```

## Offline dry-run (practice before kickoff)

```bash
# terminal 1 — fake vulnerable service
python utils/testservice.py 9001

# edit config.py: TEAMS=["127.0.0.1"], SUBMIT_PROTO="dryrun"
python farm/server.py --once              # should capture + "submit" a flag
```

## Troubleshooting
- **No flags:** test the exploit standalone; check `FLAG_REGEX` matches a real flag.
- **Flags rejected:** tune `ACCEPT/REJECT/RETRY_WORDS` to the server's exact replies.
- **Farm slow:** raise `FARM_THREADS`, lower `EXPLOIT_TIMEOUT`.
- **Sniffer empty:** run as root; confirm `SERVICES` ports and `CAPTURE_IFACE`.

*Scope: everything here targets only the team IPs in `config.py` — the competition
network. Standard A/D-CTF infrastructure.*
