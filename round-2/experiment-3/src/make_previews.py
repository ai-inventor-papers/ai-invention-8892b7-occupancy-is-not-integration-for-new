#!/usr/bin/env python3
"""Write mini_method_out.json (first 3 examples) and preview_method_out.json (same, strings truncated to 200 chars)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def trunc(o, n: int = 200):
    if isinstance(o, str):
        return o if len(o) <= n else o[:n] + "..."
    if isinstance(o, list):
        return [trunc(x, n) for x in o]
    if isinstance(o, dict):
        return {k: trunc(v, n) for k, v in o.items()}
    return o


def main() -> None:
    d = json.loads((ROOT / "method_out.json").read_text())
    mini = dict(metadata=d.get("metadata", {}), datasets=[dict(dataset=ds["dataset"], examples=ds["examples"][:3]) for ds in d["datasets"]])
    (ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=1))
    (ROOT / "preview_method_out.json").write_text(json.dumps(trunc(mini), indent=1))
    print("wrote mini_method_out.json and preview_method_out.json")


if __name__ == "__main__":
    main()
