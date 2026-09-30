"""pytest wrapper: every figure check, the literal lint, the production checks and the mutation self-test."""
import subprocess
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parent
FIGS = ["F1", "F2", "F3", "F4", "F5", "F6", "F6b", "F7", "caveats"]


def _run(script: str) -> int:
    return subprocess.run([sys.executable, str(CHECKS / script)], capture_output=True).returncode


@pytest.mark.parametrize("fig", FIGS)
def test_figure_values_match_sources(fig):
    assert _run(f"check_{fig}.py") == 0


def test_no_typed_literals():
    assert _run("lint_no_literals.py") == 0


def test_production():
    assert _run("production.py") == 0


def test_mutation_selftest():
    assert _run("selftest_mutation.py") == 0
