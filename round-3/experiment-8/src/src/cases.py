#!/usr/bin/env python3
"""STAGE 9: medoid case studies (selection by rule, never by fame) and all summary figures.

Selection: medoid of each typology cluster (k* in 3..5 -> k* cases; k* == 2 -> each medoid plus the nearest non-medoid
concept of its cluster with a different origin_group -> 4 cases; k* >= 6 -> medoids of the 5 largest clusters).
Per case: ego networks (top-20 association-strength neighbours) at T = [F+1, onset, 2022], alluvial path, subfield x year
matrix, role sequence, channel series, pattern flags and lead-lag category -> cases/<id>.json + figures.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

from common import CASES, D2, DS5, FIG, RES, SNAP_X3, TYP, WORK, X3, C, load_sealed, setup_logging, write_json  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
PALETTE = ["#2E6FBA", "#E07B39", "#3A9E6F", "#B8457E", "#7A6BB5", "#C9A227", "#5B8E9E", "#9C5B3A", "#888888"]


def save(fig, name: str) -> list[str]:
    out = []
    for ext in ("png", "pdf"):
        p = FIG / f"{name}.{ext}"
        fig.savefig(p, dpi=300, bbox_inches="tight")
        out.append(str(p.relative_to(FIG.parent)))
    plt.close(fig)
    return out


def select_cases(asg: pd.DataFrame, medo: dict) -> tuple[list[dict], str]:
    D = np.load(TYP / "D_primary.npy")
    ids = asg.concept_id.tolist()
    pos = {c: i for i, c in enumerate(ids)}
    k = medo["k"]
    meds = medo["medoid_ids"]
    cases = []
    if 3 <= k <= 5:
        cases = [dict(concept_id=m, rule="medoid") for m in meds]
    elif k == 2:
        for m in meds:
            cases.append(dict(concept_id=m, rule="medoid"))
            cl = asg.loc[asg.concept_id == m, "cluster"].iloc[0]
            og = asg.loc[asg.concept_id == m, "origin_group"].iloc[0]
            cand = asg[(asg.cluster == cl) & (asg.concept_id != m) & (asg.origin_group != og) & ~asg.concept_id.isin(meds)]
            best = min(cand.concept_id, key=lambda c: D[pos[m], pos[c]])
            cases.append(dict(concept_id=best, rule=f"nearest non-medoid to {m} with a different origin_group",
                              dtw_to_medoid=float(D[pos[m], pos[best]])))
    else:
        big = asg.cluster.value_counts().index[:5]
        cases = [dict(concept_id=m, rule="medoid of a 5-largest cluster") for m in meds
                 if asg.loc[asg.concept_id == m, "cluster"].iloc[0] in set(big)]
    return cases, f"k*={k}: " + ("medoids" if k != 2 else "2 medoids + nearest different-origin neighbour each")


def case_data(c: str, ctx: dict) -> dict:
    ind, pool, grp, roles, ll, pats, names, subn, pid0, sizes, events = (ctx[k] for k in (
        "ind", "pool", "grp", "roles", "ll", "pats", "names", "subn", "pid0", "sizes", "events"))
    p = pool.set_index("concept_id").loc[c]
    F = int(p.F)
    g = ind[ind.concept_id == c].sort_values("year")
    onset = grp.loc[c, "onset"] if c in grp.index and np.isfinite(grp.loc[c, "onset"]) else None
    llr = ll.set_index("concept_id").loc[c] if c in set(ll.concept_id) else None
    if onset is None and llr is not None and llr.exp_onset == llr.exp_onset and llr.exp_onset is not None:
        onset = llr.exp_onset
    T = [F + 1, int(onset) if onset is not None and np.isfinite(onset) else F + 5, 2022]
    ego = {}
    for t in T:
        nb = pd.read_parquet(WORK / "attach" / f"neigh_y{t}.parquet")
        nb = nb[(nb.concept_id == c) & (nb["rank"] < 20)]
        nodes = nb.node.tolist()
        ed = pd.read_parquet(SNAP_X3 / f"edges_y{t}.parquet")
        ed = ed[ed.i.isin(nodes) & ed.j.isin(nodes)]
        ego[str(t)] = dict(neighbours=[dict(node=int(r.node), name=names.get(int(r.node), str(r.node)), AS=float(r.AS),
                                            x_frame=float(r.x_frame), pid=int(pid0.get((t, int(r.comm)), -1)) if r.comm >= 0 else -1)
                                       for r in nb.itertuples()],
                           edges=[dict(i=int(r.i), j=int(r.j), c_ij=float(r.c_ij), AS=float(r.AS_ij)) for r in ed.itertuples()])
    rr = roles[roles.concept_id == c].sort_values("year")
    doms = rr.dom_s0.dropna().astype(int)
    path = [dict(year=int(y), pid=int(d), size=sizes.get((int(y), int(d))), role=r, robust=bool(b))
            for y, d, r, b in zip(rr.year, rr.dom_s0.fillna(-1), rr.role_modal, rr.robust)]
    ev = events[events.pid.isin(set(doms.tolist()))]
    cp = ctx["cp"][ctx["cp"].concept_id == c]
    kn = cp[cp.subfield >= 0]
    top = kn.subfield.value_counts().index[:12].tolist()
    mat = kn.assign(sf=np.where(kn.subfield.isin(top), kn.subfield, -2)).groupby(["sf", "year"]).size().unstack(fill_value=0)
    mat = mat.reindex(columns=range(2000, 2025), fill_value=0)
    heat = dict(years=list(range(2000, 2025)), rows=[dict(subfield=int(s), name=subn.get(int(s), "other") if s != -2 else "other",
                                                          counts=mat.loc[s].astype(int).tolist()) for s in mat.index])
    series = g[["year", "age", "vol", "H", "H_rar", "RS", "active_subfields_3y", "pct_alt", "P_raw", "wmz", "closure"]].to_dict("records")
    pr = pats[pats.concept_id == c].drop(columns=["concept_id"]).to_dict("records")
    return dict(concept_id=c, phrase=p.phrase, F=F, origin_group=p.origin_group, origin_subfield=p.origin_subfield,
                cluster=ctx["asg"].set_index("concept_id").loc[c, "cluster_name"], E_up_group=grp.loc[c, "group"] if c in grp.index else None,
                E_up_onset=grp.loc[c, "onset"] if c in grp.index else None, time_points=T, ego=ego, alluvial_path=path,
                community_events=ev.to_dict("records"), subfield_year=heat, series=series, patterns=pr[0] if pr else {},
                leadlag=(dict(category=llr.category, exp_onset=llr.exp_onset, diff_onset=llr.diff_onset) if llr is not None else None))


def case_figures(cd: dict) -> list[str]:
    import networkx as nx
    c = cd["concept_id"]
    figs = []
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    allp = sorted({n["pid"] for t in cd["ego"].values() for n in t["neighbours"]})
    col = {p: PALETTE[i % (len(PALETTE) - 1)] if p >= 0 else PALETTE[-1] for i, p in enumerate(allp)}
    for ax, (t, e) in zip(axes, cd["ego"].items()):
        G = nx.Graph()
        G.add_node("FOCAL")
        for n in e["neighbours"]:
            G.add_node(n["node"], name=n["name"], pid=n["pid"])
            G.add_edge("FOCAL", n["node"], w=n["x_frame"])
        for ed in e["edges"]:
            G.add_edge(ed["i"], ed["j"], w=0.3)
        pos = nx.spring_layout(G, seed=7, k=0.6)
        nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25, width=0.6)
        others = [n for n in G.nodes if n != "FOCAL"]
        nx.draw_networkx_nodes(G, pos, nodelist=others, node_color=[col[G.nodes[n]["pid"]] for n in others], node_size=60, ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=["FOCAL"], node_color="black", node_size=160, node_shape="*", ax=ax)
        for n in others[:12]:
            ax.text(pos[n][0], pos[n][1] + 0.04, G.nodes[n]["name"][:18], fontsize=5.5, ha="center")
        npid = len({G.nodes[n]['pid'] for n in others} - {-1})
        ngrey = sum(1 for n in others if G.nodes[n]['pid'] < 0)
        ax.set_title(f"{t}: {len(others)} top-AS neighbours in {npid} persistent communities\n(grey = {ngrey} outside any community of >= 5 kept nodes)", fontsize=7)
        ax.axis("off")
    fig.suptitle(f"{cd['phrase']} ({cd['cluster']}; F={cd['F']}) - ego network (colour = persistent community)", fontsize=9)
    figs += save(fig, f"case_{c}_ego")
    # alluvial strip
    fig, ax = plt.subplots(figsize=(9, 2.6))
    path = [p for p in cd["alluvial_path"] if p["pid"] >= 0]
    uniq = sorted({p["pid"] for p in path})
    ypos = {p: i for i, p in enumerate(uniq)}
    rc = {"BRIDGE": "#B8457E", "STAYER": "#2E6FBA", "MIGRANT": "#E07B39", "CORE_GROWING": "#3A9E6F", "FOUNDER": "#C9A227", "OTHER": "#999999"}
    for p in path:
        ax.scatter(p["year"], ypos[p["pid"]], s=20 + (p["size"] or 0) / 20, color=rc.get(p["role"], "#999"),
                   edgecolor="k" if p["robust"] else "none", linewidth=0.5)
    ax.plot([p["year"] for p in path], [ypos[p["pid"]] for p in path], color="#aaa", lw=0.8, zorder=0)
    ax.set_yticks(range(len(uniq)), [f"pid {u}" for u in uniq], fontsize=6)
    ax.set_xlabel("year")
    for r, cl in rc.items():
        ax.scatter([], [], color=cl, label=r, s=20)
    ax.legend(fontsize=6, ncol=6, loc="upper center", bbox_to_anchor=(0.5, 1.25), frameon=False)
    ax.set_title(f"{cd['phrase']}: dominant community per year (size = community size, colour = role)", fontsize=8, pad=18)
    figs += save(fig, f"case_{c}_alluvial")
    # heatmap
    fig, ax = plt.subplots(figsize=(9, 3.4))
    M = np.array([r["counts"] for r in cd["subfield_year"]["rows"]], dtype=float)
    im = ax.imshow(np.log1p(M), aspect="auto", cmap="Blues")
    ax.set_yticks(range(len(M)), [r["name"][:32] for r in cd["subfield_year"]["rows"]], fontsize=6)
    yrs = cd["subfield_year"]["years"]
    ax.set_xticks(range(0, len(yrs), 3), yrs[::3], fontsize=6)
    fig.colorbar(im, ax=ax, label="log(1 + c-papers)")
    ax.set_title(f"{cd['phrase']}: c-papers by subfield and year", fontsize=8)
    figs += save(fig, f"case_{c}_heatmap")
    return figs


def summary_figures(ctx: dict) -> list[str]:
    figs = []
    typ = json.loads((RES / "typology.json").read_text())
    traj = pd.read_csv(TYP / "cluster_trajectories_by_age.csv")
    names = typ["cluster_names"]
    chs = [("H_rar", "Shannon diversity (rarefied, nats)"), ("RS", "Rao-Stirling diversity"), ("active_subfields_3y", "active subfields (3-yr)")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, (ch, lab) in zip(axes, chs):
        for i, (cl, g) in enumerate(traj.groupby("cluster")):
            g = g[g.n >= 5]
            ax.plot(g.age, g[f"{ch}_0.5"], color=PALETTE[i], label=f"{names[str(cl)]} (n={typ['cluster_sizes'][str(cl)]})")
            ax.fill_between(g.age, g[f"{ch}_0.25"], g[f"{ch}_0.75"], color=PALETTE[i], alpha=0.2)
        ax.set_xlabel("concept age (years since F)")
        ax.set_ylabel(lab)
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Diffusion typology: median trajectory and IQR per cluster (screen MAIN)", fontsize=9)
    figs += save(fig, "typology_trajectories")
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ks = sorted(int(k) for k in typ["by_k"])
    ax.plot(ks, [typ["by_k"][str(k)]["min_jaccard"] for k in ks], "o-", color=PALETTE[0], label="3-channel: min cluster Jaccard")
    ax.plot(ks, [typ["by_k"][str(k)]["silhouette"] for k in ks], "s--", color=PALETTE[1], label="3-channel: silhouette")
    if typ["B1_entropy_only_MAIN"].get("by_k"):
        b = typ["B1_entropy_only_MAIN"]["by_k"]
        ax.plot(ks, [b[str(k)]["min_jaccard"] for k in ks], "^:", color=PALETTE[2], label="B1 entropy-only: min Jaccard")
    ax.axhline(0.75, color="grey", lw=0.8, ls="--")
    ax.axhline(0.6, color="grey", lw=0.6, ls=":")
    ax.set_xlabel("k")
    ax.set_ylabel("value")
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Hennig bootstrap stability (200 resamples)", fontsize=9)
    figs += save(fig, "typology_stability")
    for suffix, tag in (("", "pre-declared rules"), ("_poolrel", "pool-relative variant")):
        ba = pd.read_csv(RES / f"role_shares_by_age{suffix}.csv")
        fig, ax = plt.subplots(figsize=(7, 3.4))
        roles = ["BRIDGE", "OTHER", "STAYER", "MIGRANT", "CORE_GROWING", "FOUNDER"]
        bottom = np.zeros(16)
        for i, r in enumerate(roles):
            s = ba[ba.role == r].set_index("age_c").share.reindex(range(16)).fillna(0).values
            ax.bar(range(16), s, bottom=bottom, color=PALETTE[i], label=r)
            bottom += s
        ax.set_xlabel("concept age (15 = 15+)")
        ax.set_ylabel("share of robust concept-years")
        ax.legend(fontsize=6, ncol=3, frameon=False)
        ax.set_title(f"Community roles by age ({tag}; roles agreeing in >= 3/5 Leiden seeds)", fontsize=8)
        figs += save(fig, f"role_shares_by_age{suffix}")
        Tn = pd.read_csv(RES / f"role_transition_matrix{suffix}.csv", index_col=0)
        Tc = pd.read_csv(RES / f"role_transition_counts{suffix}.csv", index_col=0)
        keep = Tc.sum(axis=1) > 0
        Tn, Tc = Tn.loc[keep, keep.values], Tc.loc[keep, keep.values]
        fig, ax = plt.subplots(figsize=(4.6, 3.8))
        ax.imshow(Tn.fillna(0).values, cmap="Purples", vmin=0, vmax=1)
        for i in range(len(Tn)):
            for j in range(len(Tn.columns)):
                ax.text(j, i, f"{Tn.values[i, j]:.2f}\n({Tc.values[i, j]})", ha="center", va="center", fontsize=6)
        ax.set_xticks(range(len(Tn.columns)), Tn.columns, rotation=45, fontsize=7)
        ax.set_yticks(range(len(Tn)), Tn.index, fontsize=7)
        ax.set_xlabel("role in y")
        ax.set_ylabel("role in y-1")
        ax.set_title(f"Role transitions ({tag}), row-normalised", fontsize=8)
        figs += save(fig, f"role_transition{suffix}")
    ll = json.loads((RES / "leadlag.json").read_text())
    lh = ll["primary"]["lag_hist"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
    axes[0].bar([int(k) for k in lh], list(lh.values()), color=PALETTE[0])
    axes[0].set_xlabel("lag = diffusion onset - expansion onset (years)")
    axes[0].set_ylabel("concepts")
    axes[0].set_title(f"Lead-lag (n = {ll['primary']['n_both_onsets']} with both onsets)", fontsize=8)
    gr = pd.read_csv(RES / "leadlag_grid.csv")
    for i, h in enumerate(sorted(gr.diff_rise.unique())):
        g = gr[gr.diff_rise == h]
        axes[1].errorbar(g.exp_gain + (i - 1) * 0.6, g.share_expansion_first, yerr=[g.share_expansion_first - g.ci_lo, g.ci_hi - g.share_expansion_first],
                         fmt="o", color=PALETTE[i], label=f"diffusion rise {h} nats", capsize=2)
        for x, y, n in zip(g.exp_gain + (i - 1) * 0.6, g.share_expansion_first, g.n_both):
            axes[1].text(x, 1.04, str(n), fontsize=5, ha="center", color=PALETTE[i])
    axes[1].axhline(ll["null"]["null_mean"], color="grey", ls="--", lw=0.8, label="year-shuffle null mean (primary)")
    axes[1].set_xlabel("expansion gain threshold (pct_alt points)")
    axes[1].set_ylabel("share expansion first")
    axes[1].set_ylim(0, 1.1)
    axes[1].legend(fontsize=6, frameon=False)
    axes[1].set_title("Threshold grid (numbers = n with both onsets)", fontsize=8)
    figs += save(fig, "leadlag_hist_grid")
    pc = pd.read_csv(RES / "patterns_contrast.csv")
    pc = pc[pc.threshold_version == "recomputed_hydrated"]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for i, (pop, g) in enumerate(pc.groupby("population")):
        y = np.arange(len(g)) + i * 0.25
        ax.errorbar(g["diff"], y, xerr=[g["diff"] - g.boot_ci_lo, g.boot_ci_hi - g["diff"]], fmt="o", color=PALETTE[i], label=pop, capsize=2)
        if i == 0:
            ax.set_yticks(y + 0.12, g.main_pattern, fontsize=7)
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_xlabel("difference in share (main pool - MeSH), 95% bootstrap CI")
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("RQ1 patterns: hydrated main pool vs MeSH held-out set", fontsize=8)
    figs += save(fig, "patterns_main_vs_mesh")
    return figs


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("cases")
    load_sealed()
    asg = pd.read_csv(TYP / "assignments.csv")
    medo = json.loads((TYP / "medoids.json").read_text())
    cases, rule = select_cases(asg, medo)
    C.assert_not_sealed([x["concept_id"] for x in cases])
    per0 = pd.read_parquet(X3 / "work" / "communities" / "persistent_ids.parquet")
    names = pd.read_parquet(D2 / "data" / "concepts.parquet", columns=["concept_id", "display_name"])
    subn = pd.read_parquet(DS5 / "deps" / "gen_art_dataset_2" / "taxonomy_subfields.parquet")
    ctx = dict(ind=pd.read_parquet(RES / "indicators" / "concept_year_indicators_hyd.parquet"),
               pool=pd.read_parquet(WORK / "pool_active.parquet"), grp=pd.read_csv(RES / "labels" / "groups.csv").set_index("concept_id"),
               roles=pd.read_parquet(RES / "roles.parquet"), ll=pd.read_csv(RES / "leadlag_by_concept.csv"),
               pats=pd.read_csv(RES / "patterns_by_concept.csv"), asg=asg,
               names=dict(zip(names.concept_id.str[1:].astype(np.int64), names.display_name)),
               subn=dict(zip(subn.subfield_id, subn.name)), pid0={(int(y), int(c)): int(p) for y, c, p in zip(per0.year, per0.comm, per0.pid)},
               sizes={(int(y), int(p)): int(z) for y, p, z in zip(per0.year, per0.pid, per0["size"])},
               events=pd.read_parquet(X3 / "work" / "communities" / "alluvial_events.parquet"),
               cp=pd.read_parquet(WORK / "cp_hyd.parquet", columns=["concept_id", "year", "subfield"]))
    figs = []
    for cs in cases:
        cd = case_data(cs["concept_id"], ctx)
        cd["selection"] = cs
        write_json(CASES / f"{cs['concept_id']}.json", cd)
        figs += case_figures(cd)
        logger.info(f"case {cs['concept_id']} ({cd['phrase']}; {cd['cluster']}) done")
    figs += summary_figures(ctx)
    write_json(RES / "cases_selection.json", dict(rule=rule, cases=cases, figures=figs))
    logger.info(f"cases: {[c['concept_id'] for c in cases]}; {len(figs)} figure files")


if __name__ == "__main__":
    main()
