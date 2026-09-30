"""STEP 6: figures F1-F6 (PNG 300 dpi + PDF, Okabe-Ito colourblind-safe palette)."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from base import E8, FIG, HO, RES, wilson  # noqa: E402

OI = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#999999", "#000000"]
POPC = {"screen": "#0072B2", "heldout": "#E69F00", "mesh": "#009E73", "pooled_main": "#CC79A7"}
TYPC = {"BROAD": "#D55E00", "LOCALISED": "#56B4E9"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


def save(fig, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def f1_cases() -> None:
    cases = json.loads((RES / "cases_rooting.json").read_text())
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
    for ax, (cid, c) in zip(axs.ravel(), cases.items()):
        cj = json.loads((E8 / "cases" / f"{cid}.json").read_text())
        sy = cj["subfield_year"]
        yrs = np.array(sy["years"])
        M = pd.DataFrame({r["name"]: pd.Series(r["counts"], index=yrs).rolling(3, min_periods=1).sum() for r in sy["rows"]})
        M = M.loc[yrs >= c["F"] - 1]
        top = M.sum().sort_values(ascending=False).index[:6]
        S = pd.concat([M[top], M.drop(columns=top).sum(axis=1).rename("remaining subfields")], axis=1)
        S = S.div(S.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
        ax.stackplot(S.index, S.T.values, labels=[t[:32] for t in S.columns], colors=OI[:len(S.columns) - 1] + ["#DDDDDD"], alpha=0.85)
        ent = pd.DataFrame(c["entries"])
        if len(ent):
            ax2 = ax.twinx()
            sc = ax2.scatter(ent.e + np.random.default_rng(0).uniform(-0.15, 0.15, len(ent)), ent.A_cont, c=ent.A_cont, cmap="viridis",
                             s=12 + 6 * np.sqrt(ent.Y_strict.clip(0)), edgecolor=np.where(ent.EST_bin == 1, "k", "none"), linewidth=0.8, zorder=5)
            ax2.set_ylabel("host entry A_cont (marker); size ~ Y_strict; black edge = rooted", fontsize=7)
            ax2.set_ylim(0, max(0.2, float(ent.A_cont.max()) * 1.15))
        ll = c["leadlag"]
        for k, ls in (("exp_onset", "--"), ("diff_onset", ":")):
            if ll.get(k):
                ax.axvline(ll[k], color="k", ls=ls, lw=1)
        ax.set_title(f"{c['phrase']} ({'BROAD' if c['cluster'].startswith('broad') else 'LOCALISED'}; F={c['F']}; {ll['category']})", fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_ylabel("subfield share (3-yr window)")
        ax.legend(fontsize=6, loc="lower left", framealpha=0.7)
    fig.suptitle("F1. Case subfield shares over time with D2 host entries (dashed = expansion onset, dotted = diffusion onset)", fontsize=10)
    fig.tight_layout()
    save(fig, "F1_cases_subfield_shares")


def f2_type_hostshare() -> None:
    s = pd.read_parquet(RES / "rooting_screen_sample.parquet")
    hp = RES / "rooting_heldout_sample_W1.parquet"
    h = pd.read_parquet(hp) if hp.exists() else None
    rt = json.loads((RES / "rooting.json").read_text())
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    ax = axs[0]
    pos = 0
    ticks, labs = [], []
    for pop, d in (("screen", s), ("held-out", h)):
        if d is None:
            continue
        for t in ("BROAD", "LOCALISED"):
            v = d[d.type == t].A_cont.dropna().values
            vp = ax.violinplot(v, positions=[pos], widths=0.8, showmedians=True)
            for b in vp["bodies"]:
                b.set_facecolor(TYPC[t]); b.set_alpha(0.5)
            cm = d[d.type == t].groupby("concept_id").A_cont.mean().values
            ax.scatter(np.full(len(cm), pos) + np.random.default_rng(1).uniform(-0.2, 0.2, len(cm)), cm, s=5, color="k", alpha=0.5)
            ticks.append(pos); labs.append(f"{pop}\n{t}")
            pos += 1
        pos += 0.5
    ax.set_xticks(ticks, labs, fontsize=7)
    ax.set_ylabel("A_cont (partners' pre-entry host share)")
    si = rt["screen"]["model_i_Acont"]
    ax.set_title(f"a. A_cont by type (dots = concept means)\nadj. BROAD coef screen {si['coef']:+.4f} [{si['ci'][0]:+.4f},{si['ci'][1]:+.4f}]", fontsize=8)
    ax = axs[1]
    tab = rt["screen"]["EST_by_Aq_type"]
    for t in ("BROAD", "LOCALISED"):
        qs = [q for q in range(1, 6) if f"{t}_q{q}" in tab]
        ax.plot(qs, [tab[f"{t}_q{q}"]["EST_rate"] for q in qs], "o-", color=TYPC[t], label=t)
    ax.set_xlabel("A_cont quintile (screen co-primary sample)"); ax.set_ylabel("EST_bin rate (rooted)")
    ax.set_title("b. Establishment vs host share by type (screen)", fontsize=8); ax.legend(fontsize=7)
    ax = axs[2]
    x = np.arange(2)
    for i, (pop, key) in enumerate((("screen", "screen"), ("held-out", "heldout"))):
        if key not in rt:
            continue
        occ = rt[key]["descriptives"]["occupancy"]
        ax.bar(x + i * 0.38, [occ[t]["all_main_entries_per_concept"] for t in ("BROAD", "LOCALISED")], width=0.36,
               color=[TYPC["BROAD"], TYPC["LOCALISED"]], alpha=1 if i == 0 else 0.55, edgecolor="k", label=pop)
    ax.set_xticks(x + 0.19, ["BROAD", "LOCALISED"]); ax.set_ylabel("host entries per concept (MAIN)")
    ax.set_title("c. Occupancy: entries per concept (solid = screen, light = held-out)", fontsize=8)
    fig.suptitle("F2. Typology x host share, rooting and occupancy", fontsize=10)
    fig.tight_layout()
    save(fig, "F2_type_hostshare")


def f3_leadlag() -> None:
    t = pd.read_csv(RES / "leadlag_denominator_table.csv")
    cats = ["neither", "diffusion_only", "expansion_only", "expansion_first", "same_year", "diffusion_first"]
    col = ["#DDDDDD", "#56B4E9", "#E69F00", "#D55E00", "#F0E442", "#0072B2"]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    left = np.zeros(len(t))
    for c, cc in zip(cats, col):
        v = t[f"n_{c}"].values / t.n.values
        ax.barh(t.population, v, left=left, color=cc, label=c, edgecolor="w")
        for i, (l, w, n) in enumerate(zip(left, v, t[f"n_{c}"].values)):
            if w > 0.04:
                ax.text(l + w / 2, i, str(n), ha="center", va="center", fontsize=7)
        left += v
    for i, r in t.iterrows():
        ax.text(1.01, i, f"{r.n_expansion_first}/{r.n_both} exp-first", va="center", fontsize=7)
    ax.set_xlim(0, 1.2); ax.set_xlabel("share of concepts")
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.set_title("F3. Lead-lag full category table (from-start onsets excluded)", fontsize=10)
    save(fig, "F3_leadlag_categories")


def role_ga(pop: str) -> tuple[dict, dict, int]:
    if pop == "mesh":
        m = json.loads((RES / "mesh_results.json").read_text())["roles"]
        rs = {k: (v["share"], v["wilson_ci"]) for k, v in m["role_shares"].items()}
        ga = {k: (v["share"], v["wilson_ci"]) for k, v in m["GA_classes"].items()}
        return rs, ga, m["n_concept_years"]
    base = E8 / "results" if pop == "screen" else HO / "results"
    r = pd.read_parquet(base / "roles.parquet")
    r = r[r.MAIN] if "MAIN" in r.columns else r
    rb = r[r.robust]
    n = len(rb)
    rs = {k: (float((rb.role_modal == k).mean()), wilson(int((rb.role_modal == k).sum()), n))
          for k in ["FOUNDER", "CORE_GROWING", "BRIDGE", "MIGRANT", "STAYER", "OTHER"]}
    ga = {k: (float((r.GA_class == k).mean()), wilson(int((r.GA_class == k).sum()), len(r))) for k in sorted(r.GA_class.unique())}
    return rs, ga, n


def f4_roles() -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
    pops = ["screen", "heldout", "mesh"] if (HO / "results/roles.parquet").exists() else ["screen", "mesh"]
    data = {p: role_ga(p) for p in pops}
    for ax, idx, title in ((axs[0], 0, "a. robust primary role shares"), (axs[1], 1, "b. Guimera-Amaral classes")):
        keys = sorted(set().union(*[data[p][idx].keys() for p in pops]))
        x = np.arange(len(keys))
        for i, p in enumerate(pops):
            v = [data[p][idx].get(k, (0, [0, 0]))[0] for k in keys]
            lo = [v_ - (data[p][idx].get(k, (0, [0, 0]))[1][0] or 0) for k, v_ in zip(keys, v)]
            hi = [(data[p][idx].get(k, (0, [0, 0]))[1][1] or 0) - v_ for k, v_ in zip(keys, v)]
            ax.bar(x + i * 0.27, v, width=0.26, color=POPC[p], label=f"{p} (n={data[p][2]})", yerr=[lo, hi], capsize=2)
        ax.set_xticks(x + 0.27, [k.replace("_", "\n") for k in keys], fontsize=7)
        ax.set_ylabel("share of concept-years"); ax.set_title(title, fontsize=9); ax.legend(fontsize=7)
    fig.suptitle("F4. Community roles (Wilson CIs on concept-years; clustering ignored) - MeSH roles from a different substrate", fontsize=9)
    fig.tight_layout()
    save(fig, "F4_roles_GA")


def f5_patterns() -> None:
    p = json.loads((RES / "mesh_results.json").read_text())["patterns"]["frequencies"]
    pats = ["EARLY_BRIDGING", "INCUBATION_THEN_EXPANSION", "GRADUAL_CENTRALISATION"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for j, pat in enumerate(pats):
        for i, pop in enumerate([k for k in ("screen", "heldout", "mesh") if k in p]):
            v = p[pop].get(pat)
            if not v:
                continue
            y = j + i * 0.22
            ax.errorbar(v["freq"], y, xerr=[[v["freq"] - v["wilson_ci"][0]], [v["wilson_ci"][1] - v["freq"]]], fmt="o", color=POPC[pop],
                        label=pop if j == 0 else None, capsize=3)
    ax.set_yticks(np.arange(len(pats)) + 0.22, [s.replace("_", " ").lower() for s in pats])
    ax.set_xlabel("pattern frequency (Wilson 95% CI)"); ax.legend(fontsize=7)
    ax.set_title("F5. Emergence patterns across populations", fontsize=10)
    save(fig, "F5_patterns_forest")


def f6_margin() -> None:
    d = pd.read_csv(RES / "typology_distances.csv")
    mp = RES / "mesh/mesh_assignments.csv"
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    bins = np.linspace(0, 1, 26)
    for pop in ("screen", "heldout"):
        v = d[d.population == pop].margin
        axs[0].hist(v, bins=bins, density=True, alpha=0.5, color=POPC[pop], label=f"{pop} (n={len(v)})")
    if mp.exists():
        m = pd.read_csv(mp)
        axs[0].hist(m.margin, bins=bins, density=True, histtype="step", color=POPC["mesh"], lw=1.5, label=f"MeSH (n={len(m)})")
    axs[0].axvline(0.05, color="k", ls=":", lw=1)
    axs[0].set_xlabel("assignment margin (d2-d1)/(d2+d1)"); axs[0].set_ylabel("density"); axs[0].legend(fontsize=7)
    axs[0].set_title("a. margin (dotted = 0.05 ambiguity cut)", fontsize=9)
    p95 = json.loads((RES / "typology_extras.json").read_text())["screen"]["d1_p95"]
    b2 = np.linspace(0, max(3.5, d.d1.max()), 30)
    for pop in ("screen", "heldout"):
        axs[1].hist(d[d.population == pop].d1, bins=b2, density=True, alpha=0.5, color=POPC[pop], label=pop)
    if mp.exists():
        axs[1].hist(m.d1, bins=b2, density=True, histtype="step", color=POPC["mesh"], lw=1.5, label="MeSH")
    axs[1].axvline(p95, color="k", ls="--", lw=1)
    axs[1].set_xlabel("DTW distance to assigned medoid d1"); axs[1].legend(fontsize=7)
    axs[1].set_title("b. d1 (dashed = screen 95th pct = support edge)", fontsize=9)
    fig.suptitle("F6. Do new concepts fall inside the typology's support?", fontsize=10)
    fig.tight_layout()
    save(fig, "F6_assignment_margin")


def run() -> dict:
    done = []
    for f in (f1_cases, f2_type_hostshare, f3_leadlag, f4_roles, f5_patterns, f6_margin):
        f()
        done.append(f.__name__)
    return dict(figures=done)
