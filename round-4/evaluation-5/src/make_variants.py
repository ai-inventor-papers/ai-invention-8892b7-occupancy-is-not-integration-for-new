#!/usr/bin/env python3
"""Write mini_eval_out.json (first 3 examples per dataset) and preview_eval_out.json (mini + strings cut to 200 chars)."""
import json
from pathlib import Path

WS = Path(__file__).resolve().parent


def trunc(o):
    if isinstance(o, str):
        return o[:200]
    if isinstance(o, list):
        return [trunc(x) for x in o]
    if isinstance(o, dict):
        return {k: trunc(v) for k, v in o.items()}
    return o


def main() -> None:
    full = json.loads((WS / "eval_out.json").read_text())
    mini = dict(full)
    mini["datasets"] = [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in full["datasets"]]
    (WS / "mini_eval_out.json").write_text(json.dumps(mini, indent=1))
    (WS / "preview_eval_out.json").write_text(json.dumps(trunc(mini), indent=1))
    print("wrote mini_eval_out.json, preview_eval_out.json")


if __name__ == "__main__":
    main()
