"""Budget-guarded async OpenRouter labelling client (codebook-based batch labelling)."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from openai import AsyncOpenAI, APIStatusError

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "logs" / "llm_spend.jsonl"
CACHE = ROOT / "cache" / "llm"
CACHE.mkdir(parents=True, exist_ok=True)

MODEL_A = "google/gemini-2.5-flash-lite"
MODEL_B = "openai/gpt-4.1-nano"
MODEL_ADJ = "anthropic/claude-haiku-4.5"
HARD_CAP_USD = 1.40  # plan: hard cap $1.50, stop everything at $1.40

LABELS = ["CONCEPT", "NOT_CONCEPT", "TOO_GENERIC", "VARIANT_OF"]


class BudgetStop(RuntimeError):
    pass


def spent_so_far() -> float:
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(l).get("cost", 0.0) for l in LEDGER.open() if l.strip())


class LLM:
    def __init__(self, concurrency: int = 12) -> None:
        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
        self.sem = asyncio.Semaphore(concurrency)
        self.spent = spent_so_far()
        self.stopped = False
        self._lock = asyncio.Lock()

    async def call_json(self, *, model: str, system: str, user: str, tag: str, max_tokens: int = 4000) -> dict:
        import hashlib
        h = hashlib.sha1(f"{model}\n{system}\n{user}".encode()).hexdigest()
        cp = CACHE / f"{h}.json"
        if cp.exists():
            return json.loads(cp.read_text())
        async with self.sem:
            # check AFTER acquiring the slot, per budget rules
            if self.stopped:
                raise BudgetStop("stopped")
            if self.spent >= HARD_CAP_USD:
                self.stopped = True
                raise BudgetStop(f"artifact LLM cap reached: ${self.spent:.4f}")
            extra: dict = {"usage": {"include": True}}
            if model.startswith("google/"):
                extra["reasoning"] = {"max_tokens": 0}
            last_err = None
            for attempt in range(3):
                try:
                    resp = await self.client.chat.completions.create(
                        model=model, temperature=0, max_tokens=max_tokens,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                        response_format={"type": "json_object"}, extra_body=extra, timeout=180)
                except APIStatusError as e:
                    msg = str(e)
                    if e.status_code == 403 and "AI Inventor per-run OpenRouter budget" in msg:
                        self.stopped = True
                        raise BudgetStop(msg[:200])
                    last_err = e
                    logger.warning(f"{model} {tag} HTTP {e.status_code} attempt {attempt}: {msg[:150]}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                except Exception as e:  # network / timeout
                    last_err = e
                    logger.warning(f"{model} {tag} error attempt {attempt}: {e!r}"[:200])
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                u = resp.usage
                cost = float(getattr(u, "cost", None) or (u.model_extra or {}).get("cost", 0.0) or 0.0) if u else 0.0
                async with self._lock:
                    self.spent += cost
                    with LEDGER.open("a") as f:
                        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "model": model, "tag": tag,
                                            "in": u.prompt_tokens if u else None, "out": u.completion_tokens if u else None,
                                            "cost": cost}) + "\n")
                txt = resp.choices[0].message.content or ""
                logger.debug(f"{model} {tag} -> {txt[:300]}")
                data = parse_json(txt)
                if data is None:
                    last_err = ValueError(f"unparseable JSON: {txt[:200]}")
                    continue
                data["_model"] = resp.model or model
                data["_cost"] = cost
                data["_date"] = datetime.now(timezone.utc).date().isoformat()
                cp.write_text(json.dumps(data))
                return data
            raise RuntimeError(f"{model} {tag} failed: {last_err!r}"[:300])


def parse_json(txt: str) -> dict | None:
    txt = txt.strip()
    txt = re.sub(r"^```(json)?|```$", "", txt).strip()
    try:
        d = json.loads(txt)
        return d if isinstance(d, dict) else {"items": d}
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


CODEBOOK = (ROOT / "labelling" / "codebook.md")


def system_prompt() -> str:
    return CODEBOOK.read_text() + """

OUTPUT FORMAT: return ONLY a JSON object {"items": [{"id": "<item id>", "label": "CONCEPT|NOT_CONCEPT|TOO_GENERIC|VARIANT_OF",
"variant_of": "<id of the other item in THIS batch, or null>", "rationale": "<=15 words", "confidence": 1|2|3}, ...]}
with exactly one entry per input item, in the same order. VARIANT_OF may only point to another item id in the same batch."""


def pair_system_prompt() -> str:
    return """You judge whether two scientific phrases name the SAME concept (surface variants: plural, hyphenation,
acronym vs long form, spelling, word order, synonym listed in a thesaurus) or DIFFERENT concepts (a broader/narrower term,
a term with an added modifier that changes meaning, a different expansion of the same acronym, related-but-distinct notions).
Judge only from the phrases and the short contexts; do not use knowledge of how popular a term later became.
Return ONLY JSON {"items": [{"id": "<pair id>", "label": "SAME|DIFFERENT", "confidence": 1|2|3}, ...]} with one entry per pair."""
