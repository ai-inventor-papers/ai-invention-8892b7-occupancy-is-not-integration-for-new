#!/usr/bin/env python3
"""Re-shard work_store/ from 8 to 16 SQLite shards (work_id % 16) so every shard stays < 100 MB.

Copies the `works` and `missing` tables row by row into work_store_16/, checks per-table row counts, then swaps:
work_store/ -> work_store_old8/ (removed after the check) and work_store_16/ -> work_store/. s2map.sqlite is copied
unchanged. Usage: python reshard_store.py"""
import shutil
import sqlite3
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
OLD, NEW = ROOT / "work_store", ROOT / "work_store_16"
OLD_N, NEW_N = 8, 16

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


@logger.catch(reraise=True)
def main() -> None:
    NEW.mkdir(exist_ok=True)
    dst = []
    for i in range(NEW_N):
        c = sqlite3.connect(NEW / f"works_{i:02d}.sqlite")
        c.execute("CREATE TABLE IF NOT EXISTS works (id INTEGER PRIMARY KEY, rec BLOB)")
        c.execute("CREATE TABLE IF NOT EXISTS missing (id INTEGER PRIMARY KEY)")
        dst.append(c)
    n_old = {"works": 0, "missing": 0}
    for k in range(OLD_N):
        src = sqlite3.connect(OLD / f"works_{k:02d}.sqlite")
        for table, cols in (("works", "id, rec"), ("missing", "id")):
            n_old[table] += src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            cur = src.execute(f"SELECT {cols} FROM {table}")
            while rows := cur.fetchmany(20_000):
                by: dict[int, list] = {}
                for r in rows:
                    by.setdefault(r[0] % NEW_N, []).append(r)
                ph = ",".join("?" * len(rows[0]))
                for s, rs in by.items():
                    dst[s].executemany(f"INSERT OR REPLACE INTO {table} VALUES ({ph})", rs)
        for c in dst:
            c.commit()
        src.close()
        logger.info(f"old shard {k} copied")
    n_new = {t: sum(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for c in dst) for t in n_old}
    for c in dst:
        c.close()
    logger.info(f"rows old {n_old} new {n_new}")
    assert n_old == n_new, "row counts differ; keeping the old store"
    shutil.copy2(OLD / "s2map.sqlite", NEW / "s2map.sqlite")
    OLD.rename(ROOT / "work_store_old8")
    NEW.rename(OLD)
    shutil.rmtree(ROOT / "work_store_old8")
    big = [p.name for p in OLD.glob("*.sqlite") if p.stat().st_size >= 100e6]
    logger.info(f"swapped; shards >= 100 MB: {big}")
    assert not big


if __name__ == "__main__":
    main()
