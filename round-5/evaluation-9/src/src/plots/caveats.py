"""tables/inferential_caveats.{csv,tex}: one row per inferential check beside the F2 forest, each with its source."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.plots.common import pfmt
from src.registry import Recorder, Registry

# (check, fold label, [(registry key, format)], template, note)
ROWS = [
    ("CRV1 Wald p, held-out co-primary A_cont", "CONFIRMATORY", [("cav.ho_crv1_p", None)], "{0}", ""),
    ("Holm-adjusted p (A_cont, CT family), held-out", "CONFIRMATORY", [("cav.ho_holm", None)], "{0}", ""),
    ("Wild cluster bootstrap p, held-out", "CONFIRMATORY", [("cav.ho_wild", None)], "{0}", ""),
    ("Nativeness-permutation placebo p (500 draws), held-out", "CONFIRMATORY", [("cav.ho_nat_perm", None)], "{0}",
     ""),
    ("Placebo-calibrated p (screen SD / held-out SD)", "CONFIRMATORY",
     [("cav.ho_plac_cal_screen", None), ("cav.ho_plac_cal_heldout", None)], "{0} / {1}", ""),
    ("Within-concept A-shuffle permutation p (200 draws)", "CONFIRMATORY", [("cav.ho_ashuffle_perm", None)], "{0}",
     "borderline"),
    ("CRV1 null rejection rate at alpha 0.05 (A-shuffle draws)", "CONFIRMATORY", [("cav.ho_crv1_null_rej", ".1%")],
     "{0}", "CRV1 anti-conservative"),
    ("MeSH CRV1 null size at 0.05 / size-calibrated p", "REPLICATION",
     [("cav.mesh_crv1_null_size", ".3f"), ("cav.mesh_size_cal_p", None)], "{0} / {1}", "post hoc"),
    ("MeSH nativeness-permutation placebo p (R2)", "REPLICATION", [("cav.mesh_nat_perm", None)], "{0}", ""),
    ("Screen-vs-held-out heterogeneity p (co-primary / primary)", "CONFIRMATORY",
     [("cav.het_co", ".2f"), ("cav.het_pri", ".2f")], "{0} / {1}", ""),
    ("EST_bin LPM p for A_cont, held-out (co-primary / primary)", "CONFIRMATORY",
     [("cav.estbin_co", ".3f"), ("cav.estbin_pri", ".3f")], "{0} / {1}", "null"),
    ("Out-of-sample deviance, with minus controls-only (main held-out)", "CONFIRMATORY",
     [("cav.oos_main", ".2f"), ("cav.oos_main_lo", ".2f"), ("cav.oos_main_hi", ".2f")], "{0} [{1}, {2}]",
     "negative = improvement; CI includes 0"),
    ("Out-of-fold deviance, method minus baseline (MeSH)", "REPLICATION",
     [("cav.oos_mesh", ".3f"), ("cav.oos_mesh_lo", ".3f"), ("cav.oos_mesh_hi", ".3f")], "{0} [{1}, {2}]",
     "negative = improvement"),
    ("Screen robustness recount: significant / rows with an A term", "SCREEN",
     [("cav.rob_sig", ".0f"), ("cav.rob_n", ".0f")], "{0} / {1}", "incl. base and strata"),
    ("Screen robustness recount excl. base and field strata", "SCREEN",
     [("cav.rob_sig_ex", ".0f"), ("cav.rob_n_ex", ".0f")], "{0} / {1}", ""),
    ("Held-out co-primary spec rows significant (excl. strata)", "CONFIRMATORY",
     [("cav.ho_spec_rows_sig", ".0f"), ("cav.ho_spec_rows_n", ".0f")], "{0} / {1}",
     "derived count: p < 0.05 and CI lower > 1"),
    ("Screen wild p / nativeness-permutation p (co-primary)", "SCREEN",
     [("cav.scr_wild", None), ("cav.scr_nat_perm", None)], "{0} / {1}", ""),
]


def build(reg: Registry, out_root: Path) -> dict:
    rec = Recorder(reg, "caveats")
    out_rows = []
    for check, fold, keys, tmpl, note in ROWS:
        disp, srcs, ok = [], [], True
        for k, fmt in keys:
            v = reg.try_get(k)
            if v is None:
                ok = False
                break
            f = fmt or pfmt(v)
            rec.v(k, panel="table", row=check, field=k, fmt=f)
            disp.append(format(v, f))
            m = reg.meta(k)
            srcs.append(f"{m['artifact_id']}:{m['path']}")
        if not ok:
            continue  # NOT_FOUND rows are logged by the registry and omitted, never typed in
        rec.label(check, fold, panel="table")
        out_rows.append({"check": check, "fold_label": fold, "value": tmpl.format(*disp), "note": note,
                         "source": " ; ".join(dict.fromkeys(srcs))})
    out_root.mkdir(parents=True, exist_ok=True)
    with (out_root / "inferential_caveats.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["check", "fold_label", "value", "note", "source"])
        w.writeheader()
        w.writerows(out_rows)
    esc = lambda s: s.replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")  # noqa: E731
    tex = [r"\begin{table}[t]", r"\centering\footnotesize",
           r"\caption{Inferential caveats beside the D2 forest (F2). Each value is read from the listed "
           r"source file; wild-cluster, permutation and size-calibrated p values qualify the CRV1 Wald p.}",
           r"\label{tab:inferential-caveats}", r"\begin{tabular}{p{6.2cm}lll}", r"\hline",
           r"Check & Fold & Value & Note \\", r"\hline"]
    tex += [f"{esc(r['check'])} & {esc(r['fold_label'])} & {esc(r['value'])} & {esc(r['note'])} \\\\"
            for r in out_rows]
    tex += [r"\hline", r"\end{tabular}", r"\end{table}"]
    (out_root / "inferential_caveats.tex").write_text("\n".join(tex) + "\n")
    rec.dump(out_root / "caveats_values.json")
    (out_root / "caveats_labels.json").write_text(json.dumps(rec.labels, indent=1))
    return {"n_rows": len(out_rows), "n_declared": len(ROWS)}
