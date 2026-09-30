#!/usr/bin/env python3
"""Stream title + first-version date + categories + doi from the HF arXiv metadata snapshot
(librarian-bots/arxiv-metadata-snapshot, parquet conversion); keep papers first submitted <= 2018 only."""
import re
from concurrent.futures import ThreadPoolExecutor
import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc
from huggingface_hub import HfFileSystem
from loguru import logger
from common import ROOT, setup_logging

YR = re.compile(r"(\d{4}) \d\d:\d\d")

def first_year(v) -> int:
    if isinstance(v, list):
        v = v[0].get("created", "") if v else ""
    m = YR.search(v or "")
    return int(m.group(1)) if m else -1

def one(path: str) -> pa.Table:
    fs = HfFileSystem()
    with fs.open(path, "rb") as f:
        t = pq.ParquetFile(f).read(columns=["id", "title", "versions", "categories", "doi"])
    years = pa.array([first_year(v) for v in t.column("versions").to_pylist()], pa.int16())
    t = t.drop(["versions"]).append_column("year", years)
    t = t.filter(pc.and_(pc.greater_equal(t["year"], 1991), pc.less_equal(t["year"], 2018)))
    logger.info(f"{path.rsplit('/',1)[-1]}: kept {t.num_rows}")
    return t

@logger.catch(reraise=True)
def main() -> None:
    setup_logging("fetch_arxiv")
    fs = HfFileSystem()
    files = sorted(fs.glob("datasets/librarian-bots/arxiv-metadata-snapshot@refs%2Fconvert%2Fparquet/default/train/*.parquet"))
    with ThreadPoolExecutor(6) as ex:
        tabs = list(ex.map(one, files))
    t = pa.concat_tables(tabs)
    (ROOT / "arxiv_raw").mkdir(exist_ok=True)
    pq.write_table(t, ROOT / "arxiv_raw" / "arxiv_titles_le2018.parquet", compression="zstd")
    logger.info(f"total {t.num_rows}")

if __name__ == "__main__":
    main()
