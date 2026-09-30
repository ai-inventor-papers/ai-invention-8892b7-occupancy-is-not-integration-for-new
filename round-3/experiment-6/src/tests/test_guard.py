"""Every outcome function refuses held-out concept ids and sealed focal years (2016-2018)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import common as K  # noqa: E402
import outcomes as OC  # noqa: E402

OUTCOME_FNS = [OC.w2_counts, OC.breadth_outcomes, OC.newcomer_outcome, OC.mediator]


def test_all_outcome_functions_are_guarded():
    for f in OUTCOME_FNS:
        assert getattr(f, "__outcome_fn__", False), f.__name__


def test_heldout_id_raises():
    K.C.SEALED_IDS.add("c_sealed_test")
    try:
        for f in OUTCOME_FNS:
            with pytest.raises(RuntimeError, match="SEALED concept"):
                f("c_sealed_test", 2010, None, None, None)
    finally:
        K.C.SEALED_IDS.discard("c_sealed_test")


@pytest.mark.parametrize("t", [2016, 2017, 2018])
def test_sealed_years_raise(t):
    for f in OUTCOME_FNS:
        with pytest.raises(RuntimeError, match="SEALED focal years"):
            f("c_open", t, None, None, None)


def test_real_sealed_ids_refused_if_population_built():
    ids = K.load_sealed_ids()
    if not ids:
        pytest.skip("population stage not run yet")
    cid = sorted(ids)[0]
    g = pd.DataFrame(dict(year=[2010], subfield=[1]))
    with pytest.raises(RuntimeError):
        OC.w2_counts(cid, 2010, g)
