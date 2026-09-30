#!/usr/bin/env python3
"""Block until a condition holds or max seconds pass, then print a hydration progress line.
Usage: waitfor.py <max_s> [--until-utc HH:MM] [--pid-exit PID] [--file-exists PATH]"""
import argparse, os, time, datetime as dt, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
a = argparse.ArgumentParser(); a.add_argument("max_s", type=float); a.add_argument("--until-utc"); a.add_argument("--pid-exit", type=int)
a.add_argument("--file-exists"); x = a.parse_args()
t0 = time.time()
def cond():
    now = dt.datetime.now(dt.timezone.utc)
    if x.until_utc and now.strftime("%H:%M") >= x.until_utc and now.hour < 12 <= int(x.until_utc[:2]) + 12: return "time"
    if x.until_utc and now.strftime("%H:%M") >= x.until_utc and now.hour >= 12 and int(x.until_utc[:2]) >= 12: return "time"
    if x.pid_exit:
        try: os.kill(x.pid_exit, 0)
        except OSError: return "pid_exit"
    if x.file_exists and Path(x.file_exists).exists(): return "file"
    return None
r = None
while time.time() - t0 < x.max_s and not (r := cond()):
    time.sleep(15)
lines = [l for l in (ROOT / "hyd/logs/hydrate.log").read_text(errors="ignore").splitlines() if "worker:" in l or "[keywide]" in l]
w = [l for l in lines if "worker:" in l]
print(dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "reason:", r or "timeout")
print("last concept:", w[-1][:24], re.sub(r".*worker:\d+ - ", "", w[-1])[:200] if w else "")
print("last keywide:", lines[-1][:19], lines[-1][-150:] if lines else "")
