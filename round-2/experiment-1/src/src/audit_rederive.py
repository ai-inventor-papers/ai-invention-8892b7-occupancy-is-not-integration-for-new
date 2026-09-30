#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from RAW per-item files, through code that shares nothing with
clfdata/s3/s4/s8/s9 (hand-written F1, rank-based AUC, own bootstrap RNG, own population rules), plus placebo checks:
the same statistics on permuted labels must fail. Writes results/audit_rederive.json."""
import json
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

R = Path(__file__).resolve().parent.parent
RES = R / "results"
rng = np.random.default_rng(777)


def f1(y, h):
    tp = int(((y == 1) & (h == 1)).sum()); fp = int(((y == 0) & (h == 1)).sum()); fn = int(((y == 1) & (h == 0)).sum())
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def auc(y, s):  # Mann-Whitney U with average ranks
    order = np.argsort(s, kind="mergesort"); ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
    for v in np.unique(s):
        m = s == v; ranks[m] = ranks[m].mean()
    n1 = y.sum(); n0 = len(y) - n1
    return (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def boot(fn, n, reps=2000):
    vals = [fn(rng.integers(0, n, n)) for _ in range(reps)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


out = {}
# 1. classifier on D2 test (raw per-item predictions)
d = json.loads((RES / "d2_test_predictions.json").read_text())
thr = json.loads((R / "models" / "thresholds.json").read_text())
y = np.array([r["silver"] == "CONCEPT" for r in d], int)
p = np.array([r["p"] for r in d])
h = (p >= thr["t_F1"]).astype(int)
assert (h == np.array([r["accept_tF1"] for r in d])).all()
A = np.array([r["label_A"] == "CONCEPT" for r in d], int)
maj = np.ones(len(y), int)
out["classifier_test"] = {"n": len(y), "f1": f1(y, h), "f1_ci": boot(lambda b: f1(y[b], h[b]), len(y)), "auc": auc(y, p),
                          "f1_majority": f1(y, maj), "f1_llmA": f1(y, A),
                          "dF1_vs_majority_ci": boot(lambda b: f1(y[b], h[b]) - f1(y[b], maj[b]), len(y)),
                          "dF1_vs_llmA_ci": boot(lambda b: f1(y[b], h[b]) - f1(y[b], A[b]), len(y))}
# placebo: permuted silver labels -> AUC ~0.5 and the majority-beating margin must vanish
yp = rng.permutation(y)
out["classifier_placebo_permuted_labels"] = {"auc": auc(yp, p), "dF1_vs_majority_ci": boot(lambda b: f1(yp[b], h[b]) - f1(yp[b], maj[b]), len(yp))}

# 2. merger test sets (raw per-pair predictions)
mp = json.loads((RES / "merger_test_predictions.json").read_text())
mt = json.loads((R / "models" / "merger_thresholds.json").read_text())
for k, rows in mp.items():
    yy = np.array([r["y"] for r in rows]); pp = np.array([r["p"] for r in rows])
    out[f"merger_{k}"] = {"n": len(rows), "f1": f1(yy, (pp >= mt["p_merge"]).astype(int)), "auc": auc(yy, pp),
                          "f1_cos_baseline": f1(yy, np.array([r["cos_ge_t"] for r in rows]))}

# 3. frozen population recomputed from per-concept raw fields
tp = json.loads((RES / "test_population.json").read_text())
cs = tp["concepts"]
main = [c["concept_id"] for c in cs if c["arm"] == "main" and c["p_concept"] >= thr["t_F1"] and c["sense_final"] is not None
        and c["sense_final"] >= 0.70 and c["merged_into"] is None]
strict = [c["concept_id"] for c in cs if c["arm"] == "main" and c["p_concept"] >= thr["t_P90"] and c["sense_final"] is not None
          and c["sense_final"] >= 0.70 and c["merged_into_strict"] is None]
ref = [c["concept_id"] for c in cs if c["arm"] == "reference" and c["p_concept"] >= thr["t_F1"] and c["merged_into"] is None]
out["population"] = {"MAIN": len(main), "MAIN_equals_list": sorted(main) == sorted(tp["lists"]["MAIN"]),
                     "STRICT": len(strict), "REFERENCE_ACCEPTED": len(ref), "accepted_primary_all": sum(c["p_concept"] >= thr["t_F1"] for c in cs),
                     "accepted_primary_main": sum(c["p_concept"] >= thr["t_F1"] and c["arm"] == "main" for c in cs),
                     "unlinked_main": sum(c["link_status"] == "UNLINKED" and c["arm"] == "main" for c in cs)}
import hashlib
out["population"]["sha256_recomputed"] = hashlib.sha256((RES / "test_population.json").read_bytes()).hexdigest()

# 4. rejection x DS1 sense_check_fail (hydrated main) + placebo with permuted flags
hy = [c for c in cs if c["hydrated"] and c["arm"] == "main"]
rej = np.array([c["p_concept"] < thr["t_F1"] for c in hy]); fl = np.array([c["sense_check_fail_flag"] for c in hy])
tab = [[int((rej & fl).sum()), int((rej & ~fl).sum())], [int((~rej & fl).sum()), int((~rej & ~fl).sum())]]
out["rejection_vs_sense_fail"] = {"table": tab, "fisher_p": float(fisher_exact(tab)[1])}
pl = []
for _ in range(1000):
    f2 = rng.permutation(fl)
    t2 = [[int((rej & f2).sum()), int((rej & ~f2).sum())], [int((~rej & f2).sum()), int((~rej & ~f2).sum())]]
    pl.append(fisher_exact(t2)[1])
out["rejection_vs_sense_fail"]["placebo_share_p_lt_0.05"] = float(np.mean(np.array(pl) < 0.05))

# 5. in-domain silver audit from raw LLM labels
au = json.loads((RES / "frame_llm_audit.json").read_text())
pre = {r["concept_id"]: r for r in json.loads((RES / "frame_predictions_prelabel.json").read_text())["predictions"]}
ids = sorted(au["labels_A"])
hc = np.array([pre[i]["p_concept"] >= thr["t_F1"] for i in ids], int)
ya = np.array([au["labels_A"][i]["label"] == "CONCEPT" for i in ids], int)
ys = np.array([ya[k] if ya[k] == hc[k] else int(au["labels_adj"].get(i, au["labels_A"][i])["label"] == "CONCEPT") for k, i in enumerate(ids)])
out["frame_silver"] = {"n": len(ids), "f1_vs_adjudicated": f1(ys, hc), "n_disagree": int((ya != hc).sum()),
                       "f1_placebo_permuted": f1(rng.permutation(ys), hc)}
# 6. sense proxy validation
oa = {json.loads(l)["concept_id"]: json.loads(l)["dominant_share"] for l in (R / "data" / "sense_check.jsonl").read_text().splitlines()}
both = [c for c in oa if c in au["sense_proxy"] and oa[c] is not None]
x = np.array([oa[c] < 0.7 for c in both]); z = np.array([au["sense_proxy"][c] < 0.7 for c in both])
out["sense_proxy"] = {"n_overlap": len(both), "oa_fail": int(x.sum()), "proxy_fail": int(z.sum())}
# 7. link calibration pick from the raw curve
lc = json.loads((RES / "link_calibration.json").read_text())
cur = lc["encoders"]["minilm"]["curves"]["gated"]
tp_, wr, fl_ = (np.array([c[k] for c in cur]) for k in ("tp_rate", "wrong_rate", "falselink_rate"))
prec = 0.1 * tp_ / (0.1 * (tp_ + wr) + 0.9 * fl_ + 1e-12)
ok = [c["tau"] for c, pv in zip(cur, prec) if pv >= 0.90]
out["linker_minilm"] = {"tau": ok[0] if ok else None, "recall_at_tau": float(tp_[[c["tau"] for c in cur].index(ok[0])]) if ok else None}
# 8. LLM spend
out["llm_spend_usd"] = sum(json.loads(l)["cost"] for l in (R / "logs" / "llm_spend.jsonl").read_text().splitlines() if l.strip())
(RES / "audit_rederive.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
