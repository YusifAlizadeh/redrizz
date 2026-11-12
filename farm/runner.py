"""
Runs ONE exploit script against ONE target as an isolated subprocess, with a
hard timeout so a hanging or crashing exploit never stalls the farm.

Exploit contract (DestructiveFarm-style):
    the script is invoked as   python <exploit.py> <HOST>
    and prints captured flags to stdout, one per line, then exits.
"""
import subprocess
import sys


def run_exploit(exploit_path, host, timeout):
    """
    Execute one exploit against one host.
    Returns (stdout, stderr, returncode). On timeout returncode is -1.
    """
    try:
        proc = subprocess.run(
            [sys.executable, exploit_path, host],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        return (e.stdout or "") if isinstance(e.stdout, str) else "", "TIMEOUT", -1
    except Exception as e:  # noqa: BLE001 - never let a bad exploit kill the loop
        return "", f"RUNNER-ERROR: {e}", -2
