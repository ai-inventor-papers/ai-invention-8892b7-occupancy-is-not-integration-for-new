#!/usr/bin/env python3
"""Re-reads every value plotted in F6 from its source file (independently of src/registry.py) and asserts equality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from independent import main_for  # noqa: E402

if __name__ == "__main__":
    sys.exit(main_for("F6"))
