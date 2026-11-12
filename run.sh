#!/usr/bin/env bash
# Launch the whole toolkit in one tmux session with a pane per component.
# Attach:  tmux attach -t redrizz    |    detach: Ctrl-b then d
set -e
cd "$(dirname "$0")"
SESSION=redrizz

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux not installed. Run manually in separate terminals:"
    echo "  python farm/server.py"
    echo "  python checker/healthcheck.py --watch"
    echo "  python dashboard.py"
    exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[*] session '$SESSION' already exists, attaching."
    exec tmux attach -t "$SESSION"
fi

# window 0: the farm (runs every exploit vs every team, auto-submits)
tmux new-session -d -s "$SESSION" -n farm "python farm/server.py; bash"
# split: SLA healthcheck
tmux split-window -v -t "$SESSION:farm" "python checker/healthcheck.py --watch; bash"
# window 1: live dashboard
tmux new-window -t "$SESSION" -n dash "python dashboard.py; bash"
# window 2: a spare shell for writing exploits / running the sniffer (needs sudo)
tmux new-window -t "$SESSION" -n work "echo 'sniffer: sudo python steal/sniffer.py'; bash"

tmux select-window -t "$SESSION:farm"
echo "[+] started. attaching... (detach with Ctrl-b d)"
exec tmux attach -t "$SESSION"
