#!/usr/bin/env python3
"""OpenRouter helpers with a running cost total and a hard stop on the AI Inventor budget 403."""
import asyncio
import os
import re

import orjson
from loguru import logger
from openai import AsyncOpenAI, APIStatusError

MODEL = "google/gemini-3.1-flash-lite"
COST_CAP_USD = 1.0  # this artifact's OpenRouter ceiling (plan: <= $1)


class BudgetStop(RuntimeError):
    pass


class LLM:
    def __init__(self, cost_path) -> None:
        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
        self.cost_path = cost_path
        self.cost = float(orjson.loads(cost_path.read_bytes())["usd"]) if cost_path.exists() else 0.0
        self.stopped = False
        self.sem = asyncio.Semaphore(8)

    def _save(self) -> None:
        self.cost_path.write_bytes(orjson.dumps({"usd": round(self.cost, 6), "model": MODEL}))

    async def json_call(self, system: str, user: str, max_tokens: int = 6000) -> list | dict | None:
        if self.stopped or self.cost >= COST_CAP_USD:
            raise BudgetStop("stopped")
        async with self.sem:
            if self.stopped or self.cost >= COST_CAP_USD:
                raise BudgetStop("stopped")
            for attempt in range(3):
                try:
                    r = await self.client.chat.completions.create(
                        model=MODEL, temperature=0, max_tokens=max_tokens,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                        extra_body={"usage": {"include": True}})
                except APIStatusError as e:
                    if e.status_code == 403 and "AI Inventor per-run OpenRouter budget" in str(e):
                        self.stopped = True
                        raise BudgetStop(str(e)) from e
                    logger.warning(f"LLM error {e.status_code}: {str(e)[:200]}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                u = getattr(r, "usage", None)
                c = getattr(u, "cost", None) if u else None
                if c is None and u is not None:
                    c = (u.prompt_tokens * 0.25 + u.completion_tokens * 1.5) / 1e6
                self.cost += float(c or 0)
                self._save()
                txt = r.choices[0].message.content or ""
                logger.debug(f"LLM in={user[:200]!r} out={txt[:300]!r} cost_total={self.cost:.4f}")
                m = re.search(r"(\[.*\]|\{.*\})", txt, re.S)
                if not m:
                    continue
                try:
                    return orjson.loads(m.group(1))
                except orjson.JSONDecodeError:
                    continue
            return None
