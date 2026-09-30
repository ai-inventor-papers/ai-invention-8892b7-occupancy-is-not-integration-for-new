"""STAGE 15: figures (PDF + PNG). F1/F2 binned within-FE response, F3 partition by establishment, F4 robustness
forest, F5 placebo, F6 power curve."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import models  # noqa: E402
import ppml  # noqa: E402
from config import FIGS, RESULTS, SEED  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "savefig.dpi": 200})
C_A, C_CT, C_GREY = "#1b6ca8", "#c2571a", "#7f7f7f"


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png")
    plt.close(fig)


def binned(s: pd.DataFrame, var: str, rng, nb: int = 10) -> pd.DataFrame:
    """Deciles of var vs mean y/mu0 (mu0 = controls + secondary FE fit), concept-bootstrap 95% band."""
    s = s.copy()
    s["bin"] = pd.qcut(s[var].rank(method="first"), nb, labels=False)
    s["ratio"] = s.Y_strict / s.mu0
    agg = s.groupby("bin").agg(x=(var, "mean"), r=("ratio", "mean"), ysum=("Y_strict", "sum"), msum=("mu0", "sum"))
    agg["r"] = agg.ysum / agg.msum
    cids = s.concept_id.unique()
    g = {c: x for c, x in s.groupby("concept_id")}
    bs = []
    for _ in range(500):
        b = pd.concat([g[c] for c in rng.choice(cids, len(cids))])
        a = b.groupby("bin").agg(ysum=("Y_strict", "sum"), msum=("mu0", "sum"))
        bs.append((a.ysum / a.msum).reindex(range(nb)).to_numpy())
    bs = np.array(bs)
    agg["lo"], agg["hi"] = np.nanquantile(bs, .025, axis=0), np.nanquantile(bs, .975, axis=0)
    return agg


def run() -> None:
    rng = np.random.default_rng(SEED)
    df = pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet")
    s = models.primary_sample(df)
    xs = models.EVENT_CONTROLS + models.SECONDARY_EXTRA
    r0 = ppml.fit(s.Y_strict.to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    k = s[r0["keep"]].copy()
    k["mu0"] = r0["mu"]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for a, var, col, lab in ((ax[0], "A_cont", C_A, "Anchoring A (mean host share of partners)"),
                             (ax[1], "CT", C_CT, "Co-transfer CT (share of origin companions)")):
        b = binned(k, var, rng)
        a.fill_between(b.x, b.lo, b.hi, color=col, alpha=.2, lw=0)
        a.plot(b.x, b.r, "o-", color=col, ms=4)
        a.axhline(1, color=C_GREY, lw=.8, ls="--")
        a.set_xlabel(lab)
    ax[0].set_ylabel("Newcomer host papers in W2\n(observed / expected, within FE)")
    fig.suptitle("Establishment of host entries by decile (screen, MAIN; controls + concept, year, host FE)", fontsize=9)
    save(fig, "F1_F2_binned_A_CT")
    # F3 partition by establishment
    lab = pd.read_parquet(RESULTS / "graft_labels_screen.parquet")
    m = df[df.MAIN & df.kw5].join(lab[["anchored"]], how="inner")
    parts = ["graft_t03", "native_companion_t03", "package_t03", "third_party_t03"]
    names = ["graft (native, new)", "native companion", "package (non-native companion)", "third party"]
    tab = m.groupby("EST_bin")[parts].mean().mul(1 - m.groupby("EST_bin").unknown_share.mean(), axis=0)
    tab["unknown"] = m.groupby("EST_bin").unknown_share.mean()
    fig, a = plt.subplots(figsize=(4.8, 2.6))
    left = np.zeros(len(tab))
    cols = [C_A, "#6aa6d6", C_CT, "#d9b38c", "#d0d0d0"]
    for c, n, colr in zip(parts + ["unknown"], names + ["unprofiled"], cols):
        a.barh(["not established", "established"], tab[c].to_numpy(), left=left, color=colr, label=n)
        left += tab[c].to_numpy()
    a.set_xlabel("share of entry-year partner tags (native >= 0.3)")
    a.legend(fontsize=7, ncol=2, loc="upper center", bbox_to_anchor=(.5, -.35), frameon=False)
    save(fig, "F3_partition_by_establishment")
    # F4 forest
    rb = pd.read_csv(RESULTS / "d2_robustness.csv")
    rb = rb[rb.irr_sd_A.notna() & ~rb.spec.str.startswith("stratum") & ~rb.spec.str.contains("bound A_cont_hi")]
    specs = list(dict.fromkeys(rb.spec))
    fig, a = plt.subplots(figsize=(6.4, 0.24 * len(specs) + 1.0))
    for off, fe, col in ((-.18, "primary", C_GREY), (.18, "secondary", C_A)):
        r = rb[rb.fe == fe].set_index("spec").reindex(specs)
        y = np.arange(len(specs)) + off
        a.errorbar(r.irr_sd_A, y, xerr=[r.irr_sd_A - r.irr_sd_A_lo, r.irr_sd_A_hi - r.irr_sd_A], fmt="o", ms=3,
                   color=col, lw=.8, label={"primary": "concept x year + host x year FE",
                                             "secondary": "concept + year + host FE (co-primary)"}[fe])
    a.axvline(1, color="k", lw=.7)
    a.set_yticks(range(len(specs)))
    a.set_yticklabels(specs, fontsize=7)
    a.invert_yaxis()
    a.set_xscale("log")
    a.set_xlabel("IRR per SD of the anchoring measure (95% CI)")
    a.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.3, -0.06 * 22 / len(specs)), ncol=1, frameon=False)
    save(fig, "F4_robustness_forest")
    # F5 placebo
    pl = pd.read_csv(RESULTS / "placebo_draws.csv")
    ps = json.loads((RESULTS / "placebo_summary.json").read_text())
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for a, spec, t in ((ax[0], "primary", "concept x year + host x year FE"),
                       (ax[1], "secondary", "concept + year + host FE")):
        a.hist(pl[f"z_A_{spec}"].dropna(), bins=40, color=C_GREY, alpha=.8)
        a.axvline(ps[spec]["z_A_obs"], color=C_A, lw=2)
        a.set_title(f"{t}\nperm. p = {ps[spec]['perm_p_two_sided_z (primary placebo p)']:.3f}", fontsize=8)
        a.set_xlabel("z of b_A under permuted nativeness")
    save(fig, "F5_placebo")
    # F6 power
    pw = json.loads((RESULTS / "power_heldout.json").read_text())
    fig, a = plt.subplots(figsize=(4.2, 2.8))
    for spec, col in (("primary", C_GREY), ("secondary", C_A)):
        c = {float(k): v for k, v in pw["power_curve"][spec].items()}
        xs_ = sorted(c)
        a.plot(xs_, [c[x] for x in xs_], "o-", color=col, ms=3, label=spec)
        a.axvline(pw["screen_irr_per_sd"][spec], color=col, ls=":", lw=1)
    a.axhline(.8, color="k", lw=.6, ls="--")
    a.set_xlabel("true IRR per SD of A")
    a.set_ylabel("power (held-out design)")
    a.legend(fontsize=7)
    save(fig, "F6_power_heldout")
