#!/usr/bin/env python3
"""One-off: split the monolithic work_store.sqlite into work_store/ shards (< 100 MB each)."""
import sqlite3
from pathlib import Path
from hydrate_lib import Store, N_SHARDS
ROOT = Path(__file__).resolve().parent
old = sqlite3.connect(ROOT / "work_store.sqlite")
st = Store()
for t in ("works", "missing"):
    cols = "id, rec" if t == "works" else "id"
    buf = {k: [] for k in range(N_SHARDS)}
    for row in old.execute(f"SELECT {cols} FROM {t}"):
        buf[row[0] % N_SHARDS].append(row)
    for k, rows in buf.items():
        st.shards[k].executemany(f"INSERT OR REPLACE INTO {t} VALUES ({','.join('?' * len(rows[0]))})" if rows else "SELECT 1", rows) if rows else None
        st.shards[k].commit()
st.con.executemany("INSERT OR REPLACE INTO s2map VALUES (?,?,?)", old.execute("SELECT corpus_id, wid, how FROM s2map"))
st.con.commit()
print("works", st.count(), "old", old.execute("SELECT COUNT(*) FROM works").fetchone()[0])
