"""Put vendor/ (the unchanged exp_7 modules) and src/ on sys.path so the vendored exp_7 tests run unchanged."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
