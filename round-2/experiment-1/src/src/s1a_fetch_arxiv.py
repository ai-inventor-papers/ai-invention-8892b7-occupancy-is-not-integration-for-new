#!/usr/bin/env python3
"""Rebuild arXiv titles first submitted 1991-2018 (adapted from DS1 fetch_arxiv.py; DS1 arxiv_raw/ was deleted).
Streams only the id/title/versions/categories columns of the HF parquet conversion of
librarian-bots/arxiv-metadata-snapshot -> cache/arxiv_titles_le2018.parquet (title, year, categories)."""
import re
import time
from concurrent.futures import ThreadPoolExecutor

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
from loguru import logger

from common import CACHE, setup_logging

YR = re.compile(r"(\d{4}) \d\d:\d\d")
OUT = CACHE / "arxiv_titles_le2018.parquet"


def first_year(v) -> int:
    if isinstance(v, list):
        v = v[0].get("created", "") if v else ""
    m = YR.search(v or "")
    return int(m.group(1)) if m else -1


def one(path: str) -> pa.Table:
    fs = HfFileSystem()
    for attempt in range(4):
        try:
            with fs.open(path, "rb") as f:
                t = pq.ParquetFile(f).read(columns=["id", "title", "versions", "categories"])
            break
        except (OSError, RuntimeError) as e:
            logger.warning(f"{path}: attempt {attempt} failed: {e!r}"[:300])
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"could not read {path}")
    years = pa.array([first_year(v) for v in t.column("versions").to_pylist()], pa.int16())
    t = t.drop(["versions"]).append_column("year", years)
    t = t.filter(pc.and_(pc.greater_equal(t["year"], 1991), pc.less_equal(t["year"], 2018)))
    logger.info(f"{path.rsplit('/', 1)[-1]}: kept {t.num_rows}")
    return t


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s1a_fetch_arxiv")
    if OUT.exists():
        logger.info(f"{OUT} exists; skipping")
        return
    t0 = time.time()
    fs = HfFileSystem()
    files = sorted(fs.glob("datasets/librarian-bots/arxiv-metadata-snapshot@refs%2Fconvert%2Fparquet/default/train/*.parquet"))
    logger.info(f"{len(files)} parquet files")
    with ThreadPoolExecutor(6) as ex:
        tabs = list(ex.map(one, files))
    t = pa.concat_tables(tabs)
    pq.write_table(t, OUT, compression="zstd")
    logger.info(f"total {t.num_rows} titles in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
