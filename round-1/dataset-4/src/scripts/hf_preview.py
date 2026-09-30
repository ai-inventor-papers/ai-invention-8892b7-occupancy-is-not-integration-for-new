#!/usr/bin/env python3
"""Preview HF datasets via the datasets-server API (metadata + first rows)."""
import sys, json, asyncio, aiohttp, os
IDS = sys.argv[1:]
H = {"Authorization": f"Bearer {os.environ.get('HF_TOKEN','')}"}
async def one(s, ds):
    out = {"id": ds}
    try:
        async with s.get(f"https://huggingface.co/api/datasets/{ds}", headers=H) as r:
            j = await r.json()
            out["downloads"] = j.get("downloads"); out["likes"] = j.get("likes")
            out["license"] = [t for t in j.get("tags", []) if t.startswith("license:")]
            out["files"] = [x["rfilename"] for x in j.get("siblings", [])][:15]
        async with s.get(f"https://datasets-server.huggingface.co/splits?dataset={ds}", headers=H) as r:
            sp = await r.json()
        splits = sp.get("splits", [])
        out["splits"] = [(x["config"], x["split"]) for x in splits][:12]
        if splits:
            c, spl = splits[0]["config"], splits[0]["split"]
            async with s.get(f"https://datasets-server.huggingface.co/first-rows?dataset={ds}&config={c}&split={spl}", headers=H) as r:
                fr = await r.json()
            rows = fr.get("rows", [])[:1]
            out["row"] = json.dumps(rows[0]["row"] if rows else fr, ensure_ascii=False)[:700]
        else:
            out["err"] = str(sp)[:200]
    except Exception as e:
        out["err"] = repr(e)[:200]
    return out
async def main():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
        res = await asyncio.gather(*[one(s, d) for d in IDS])
    for r in res:
        print(json.dumps(r, ensure_ascii=False)); print()
asyncio.run(main())
