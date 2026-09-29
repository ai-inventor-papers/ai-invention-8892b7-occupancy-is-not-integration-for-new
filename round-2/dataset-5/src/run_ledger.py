#!/usr/bin/env python3
"""Summarise the per-call credit ledger (hyd/credit_ledger.jsonl, one record per credit-priced OpenAlex call with a
'step' field) plus step timings / throughput from the logs into run_ledger.json."""
import re
import sys
from collections import defaultdict
from pathlib import Path

import orjson
from loguru import logger

ROOT = Path(__file__).resolve().parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


def ledger() -> dict:
    by = defaultdict(lambda: {"credits": 0, "calls": 0, "first_utc": None, "last_utc": None,
                              "remaining_keywide_first": None, "remaining_keywide_last": None})
    p = ROOT / "hyd" / "credit_ledger.jsonl"
    if not p.exists():
        return {}
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = orjson.loads(line)
        s = by[r.get("step", "unspecified")]
        s["credits"] += int(r.get("credits", 0))
        s["calls"] += 1
        s["first_utc"] = s["first_utc"] or r["ts"]
        s["last_utc"] = r["ts"]
        if s["remaining_keywide_first"] is None:
            s["remaining_keywide_first"] = r.get("remaining")
        s["remaining_keywide_last"] = r.get("remaining")
    return dict(by)


def hydration_stats() -> dict:
    log = ROOT / "hyd" / "logs" / "hydrate.log"
    if not log.exists():
        return {}
    done = []
    for line in log.read_text(errors="ignore").splitlines():
        m = re.search(r"^(\S+ \S+) .*\[(\d+)\] '(.+?)' route=(\S+) cand=(\d+) links=(\d+) t=([\d.]+)s credits=(\d+) "
                      r"rem=(\S+) store=(\d+)", line)
        if m:
            done.append({"utc": m.group(1), "route": m.group(4), "cand": int(m.group(5)), "links": int(m.group(6)),
                         "seconds": float(m.group(7)), "store": int(m.group(10))})
    new = [d for d in done if d["seconds"] > 0]
    return {"n_log_lines_concepts": len(done), "store_first": done[0]["store"] if done else None,
            "store_last": done[-1]["store"] if done else None, "first_utc": done[0]["utc"] if done else None,
            "last_utc": done[-1]["utc"] if done else None,
            "routes_logged": {r: sum(1 for d in new if d["route"] == r) for r in {d["route"] for d in new}}}


@logger.catch(reraise=True)
def main() -> None:
    out = {"credit_ledger_by_step": ledger(), "hydration_log": hydration_stats()}
    extra = ROOT / "logs" / "run_notes.json"
    if extra.exists():
        out["notes"] = orjson.loads(extra.read_bytes())
    out["total_credits_iter2"] = sum(v["credits"] for v in out["credit_ledger_by_step"].values())
    (ROOT / "run_ledger.json").write_bytes(orjson.dumps(out, option=orjson.OPT_INDENT_2))
    logger.info(orjson.dumps(out).decode()[:2000])


if __name__ == "__main__":
    main()
