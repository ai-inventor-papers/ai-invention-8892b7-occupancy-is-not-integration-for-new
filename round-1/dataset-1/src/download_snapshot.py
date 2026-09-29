#!/usr/bin/env python3
"""Download small OpenAlex snapshot entity folders (parquet) from the free anonymous S3 bucket."""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from loguru import logger

logger.remove(); logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
ROOT = Path(__file__).parent / "snapshot_entities"
ENTS = ["keywords", "concepts", "topics", "subfields", "fields", "domains", "sources"]

@logger.catch(reraise=True)
def main() -> None:
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED, max_pool_connections=32))
    jobs = []
    for ent in ENTS:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket="openalex", Prefix=f"data/parquet/{ent}/"):
            for o in page.get("Contents", []):
                dest = ROOT / o["Key"].removeprefix("data/parquet/")
                if not (dest.exists() and dest.stat().st_size == o["Size"]):
                    jobs.append((o["Key"], dest))
    logger.info(f"{len(jobs)} files to download")
    def dl(j):
        k, d = j; d.parent.mkdir(parents=True, exist_ok=True); s3.download_file("openalex", k, str(d))
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(dl, jobs))
    logger.info("done")

if __name__ == "__main__":
    main()
