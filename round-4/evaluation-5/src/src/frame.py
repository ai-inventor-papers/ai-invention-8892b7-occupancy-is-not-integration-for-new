"""STEP 1: sampling frame (no exposure touched).

Cases   = W2 author-disjoint newcomer adopters of c in d (authors of the W2 d-papers of c counted in Y_strict).
Controls= incidence-density sample from in-corpus authors active in d in the case's adoption year Y, excluding
          Pset(c,e), every c-author 2000-2024 and the entry's cases; exact match on team/activity/first-year bins
          with a fixed relaxation order; 1 control + 2 reserves (productivity-floor rule).
Targets = entry partners P (top 60 by tag weight, G2 classes), frequency-matched negative controls NEG (<=20) and
          placebo partners PLAC (<=20) of another screen MAIN entry into the same d with |e'-e| <= 1.
Mediators (all 1,544 co-primary entries): M2 (corpus pre-exposed host-author pool), M2_share, M2_native, M2_adjacent,
          M1 (exact OpenAlex profile-based partner prevalence in d).
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger
from scipy import sparse

import mech_common as mc
from mech_common import config, io_load  # noqa: F401

import features as F  # vendored
import outcomes as O  # vendored

TEAM_BINS = [(1, 2), (3, 5), (6, 10), (11, 10 ** 9)]
MAX_PER_ENTRY, MAX_PER_CONCEPT, PER_TERCILE, HARD_CAP = 6, 25, 500, 1500
N_P_MAX, N_NEG_MAX, N_PLAC_MAX = 60, 20, 20
NATIVE_T, ADJ_T = 0.3, 0.05


def team_bin(n: int) -> int:
    for i, (a, b) in enumerate(TEAM_BINS):
        if a <= n <= b:
            return i
    return 0


def act_bin(n: int) -> int:
    return 0 if n <= 1 else (1 if n <= 3 else 2)


def prior_bin(n: int) -> int:
    return 0 if n <= 0 else (1 if n == 1 else (2 if n <= 3 else 3))


def fy_bin(fy: int, e: int) -> int:
    return 0 if fy <= e - 10 else (1 if fy <= e - 3 else 2)


class Corpus:
    """Author-level indices over the 463k-work corpus."""

    def __init__(self, G: dict):
        self.G = G
        W = G["W"]
        ptr, idx = G["AU"]
        self.nw = len(ptr) - 1
        self.na = G["n_authors"]
        self.year = W["year"]
        self.sub = W["sub"]
        self.team = np.diff(ptr)
        rows_rep = np.repeat(np.arange(self.nw), self.team)
        M = sparse.csr_matrix((np.ones(len(idx), np.int8), idx, ptr), shape=(self.nw, self.na))
        self.MT = M.T.tocsr()  # authors x works
        self.M = M
        first = np.full(self.na, 9999, np.int32)
        np.minimum.at(first, idx, self.year[rows_rep])
        self.first_year = first
        # authorship table restricted to works with a known subfield (sub >= 0, topic_score >= 0.05 rule)
        m = self.sub[rows_rep] >= 0
        self.AS = pd.DataFrame({"row": rows_rep[m], "au": idx[m], "year": self.year[rows_rep[m]],
                                "sub": self.sub[rows_rep[m]]})
        self.cnt = self.AS.groupby(["au", "sub", "year"]).size()
        raw = mc.author_raw_ids()
        self.raw = raw
        self.bad_author = np.flatnonzero(raw < 0)  # placeholder id -1
        # partner matrix (works x node columns)
        pptr, pidx = G["P"]
        self.nodes, pcol = np.unique(pidx, return_inverse=True)
        self.node_col = {int(n): i for i, n in enumerate(self.nodes)}
        self.Pm = sparse.csr_matrix((np.ones(len(pidx), np.int8), pcol, pptr), shape=(self.nw, len(self.nodes)))
        self.Pc = self.Pm.tocsc()
        self._dy_cache: dict = {}
        self._ad_cache: dict = {}
        self._prior_cache: dict = {}
        logger.info(f"corpus: works {self.nw}, authors {self.na}, authorships(sub>=0) {len(self.AS)}, "
                    f"partner nodes {len(self.nodes)}")

    def prior_count_all(self, e: int) -> np.ndarray:
        """Corpus works published <= e-1 for every author (no c-paper exclusion; used for non-c-authors)."""
        if e not in self._prior_cache:
            self._prior_cache[e] = np.asarray(self.MT @ (self.year <= e - 1).astype(np.int32)).ravel()
        return self._prior_cache[e]

    def author_works(self, a: int) -> np.ndarray:
        return self.MT.indices[self.MT.indptr[a]:self.MT.indptr[a + 1]]

    def activity(self, au: np.ndarray, d: int, Y: int) -> np.ndarray:
        """n corpus d-papers by each author in [Y-2, Y]."""
        out = np.zeros(len(au), int)
        for yy in (Y - 2, Y - 1, Y):
            ix = pd.MultiIndex.from_arrays([au, np.full(len(au), d), np.full(len(au), yy)])
            out += self.cnt.reindex(ix).fillna(0).to_numpy(int)
        return out

    def dy_candidates(self, d: int, years: tuple) -> pd.DataFrame:
        """Authors with >= 1 corpus d-paper in the given years; index paper = their first such paper."""
        key = (d, years)
        if key not in self._dy_cache:
            t = self.AS[(self.AS["sub"] == d) & self.AS.year.isin(years)].sort_values(["au", "year", "row"])
            t = t.drop_duplicates("au", keep="first")
            t = t.assign(team=self.team[t.row.to_numpy()])
            self._dy_cache[key] = t.reset_index(drop=True)
        return self._dy_cache[key]

    def host_authors_mask(self, d: int, e: int) -> np.ndarray:
        """Authors with a corpus d-paper in [e-3, e-1]."""
        key = (d, e)
        if key not in self._ad_cache:
            t = self.AS[(self.AS["sub"] == d) & (self.AS.year >= e - 3) & (self.AS.year <= e - 1)]
            m = np.zeros(self.na, bool)
            m[t.au.to_numpy()] = True
            m[self.bad_author] = False
            self._ad_cache[key] = m
        return self._ad_cache[key]

    def prior_rows(self, a: int, e: int, c_rows: set) -> np.ndarray:
        w = self.author_works(a)
        w = w[self.year[w] <= e - 1]
        if c_rows:
            w = np.array([x for x in w if int(x) not in c_rows], np.int64)
        return w

    def exposed_authors(self, cols: list[int], e: int, c_rowmask: np.ndarray) -> np.ndarray:
        """Boolean author mask: >= 1 corpus work published <= e-1 (not a c-paper) carrying >= 1 node in cols."""
        if not cols:
            return np.zeros(self.na, bool)
        sub = self.Pc[:, cols]
        rows = np.unique(sub.indices)
        rows = rows[(self.year[rows] <= e - 1) & ~c_rowmask[rows]]
        v = np.zeros(self.nw, np.int8)
        v[rows] = 1
        return (self.MT @ v) > 0


def entry_targets(G: dict, C: Corpus, row: pd.Series, nat: F.Nativeness, prof_pool: dict, rng: np.random.Generator,
                  plac_nodes: list[int], own) -> dict:
    cid, d, e = row.concept_id, int(row.d), int(row.e)
    blk = F.block_of(e)
    r, y = G["links"][cid]
    sub = G["W"]["sub"][r]
    o = int(row.o) if pd.notna(row.o) else -999
    er, pos, nodes = F.event_tags(G, cid, d, e, own)
    cnt = Counter(int(x) for x in nodes)
    tot = sum(cnt.values())
    all_w = {k: v / tot for k, v in cnt.items()} if tot else {}
    top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:N_P_MAX]
    comp = F.partner_set(G, r[(sub == o) & (y >= e - 5) & (y <= e - 1)], own)
    P = []
    for node, k in top:
        s = nat.share(node, blk, d)
        cls = "UNPROFILED" if s is None else ("NATIVE" if s >= NATIVE_T else ("ADJACENT" if s >= ADJ_T else "FOREIGN"))
        P.append({"node": node, "w": k / tot, "share": s, "cls": cls, "companion": node in comp})
    pset = {p["node"] for p in P}
    plac = [n for n in plac_nodes if n not in pset][:N_PLAC_MAX]
    # negative controls: frequency-matched profiled nodes (decile of n_p[d,blk], decile of total_p[blk], level)
    pool = prof_pool[(d, blk)]
    excl = pset | set(comp) | set(plac) | ({own} if own is not None else set())
    prof_partners = [p for p in P if p["share"] is not None]
    if len(prof_partners) > N_NEG_MAX:
        pick = rng.choice(len(prof_partners), N_NEG_MAX, replace=False)
        prof_partners = [prof_partners[i] for i in sorted(pick)]
    neg, n_relax = [], 0
    lvl = G["level"]
    for p in prof_partners:
        i = pool["pos"][p["node"]]
        dn, dt, lv = pool["dec_n"][i], pool["dec_t"][i], lvl.get(p["node"], -1)
        chosen = None
        for stage in range(4):
            if stage == 0:
                m = (pool["dec_n"] == dn) & (pool["dec_t"] == dt) & (pool["level"] == lv)
            elif stage == 1:
                m = (pool["dec_n"] == dn) & (pool["dec_t"] == dt)
            elif stage == 2:
                m = (pool["dec_n"] == dn) & (np.abs(pool["dec_t"] - dt) <= 1)
            else:
                m = (np.abs(pool["dec_n"] - dn) <= 1) & (np.abs(pool["dec_t"] - dt) <= 1)
            cand = [int(x) for x in pool["node"][m] if int(x) not in excl]
            if cand:
                chosen = int(rng.choice(cand))
                n_relax += stage > 0
                break
        if chosen is not None:
            neg.append(chosen)
            excl.add(chosen)
    return {"P": P, "NEG": neg, "PLAC": plac, "companions_n": len(comp), "all_w": all_w, "blk": blk,
            "neg_relaxed": n_relax, "comp": comp}


def build_prof_pool(G: dict, pairs: set) -> dict:
    """Per (d, block): profiled nodes with within-pool deciles of n_p[d, block] and total_p[block]."""
    prof = G["prof"]
    by_blk = defaultdict(list)
    for (node, blk), (tot, counts, _) in prof.items():
        by_blk[blk].append((node, tot, counts))
    out = {}
    for d, blk in pairs:
        L = by_blk[blk]
        node = np.array([x[0] for x in L], np.int64)
        tot = np.array([x[1] for x in L], float)
        nd = np.array([x[2].get(d, 0) for x in L], float)

        def dec(v):
            srt = np.sort(v)
            return np.minimum((np.searchsorted(srt, v, side="left") / len(v) * 10).astype(int), 9)
        out[(d, blk)] = {"node": node, "dec_n": dec(nd), "dec_t": dec(tot),
                         "level": np.array([G["level"].get(int(n), -1) for n in node]),
                         "pos": {int(n): i for i, n in enumerate(node)}}
    return out


def build(G: dict, measurable_only: bool = True, concept_cap: int = MAX_PER_CONCEPT, per_tercile: int = PER_TERCILE,
          hard_cap: int = HARD_CAP, with_mediators: bool = True, C: Corpus | None = None) -> dict:
    rng = np.random.default_rng(mc.SEED)
    config.load_sealed_ids()
    s, _ = mc.coprimary_sample()
    ent = s[s.retained].reset_index(drop=True).copy()
    config.assert_not_sealed(ent.concept_id.unique())
    ent["entry_id"] = ent.concept_id + "|" + ent.d.astype(str) + "|" + ent.e.astype(str)
    q = ent.A_cont.quantile([1 / 3, 2 / 3]).to_numpy()
    ent["A_tercile"] = np.where(ent.A_cont <= q[0], 1, np.where(ent.A_cont <= q[1], 2, 3))
    con = G["concepts"].set_index("concept_id")
    C = C or Corpus(G)
    cai = O.CoauthorIndex(G)
    AUp, AUi = G["AU"]
    W = G["W"]
    bad = set(C.bad_author.tolist())

    # ---------- 1a cases ----------
    cases, entry_info = [], {}
    n_ymismatch = 0
    for cid, g in ent.groupby("concept_id", sort=True):
        r, y = G["links"][cid]
        sub = W["sub"][r]
        c_auth = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r] or [np.zeros(0, np.int64)]))
        for ev in g.itertuples():
            d, e = int(ev.d), int(ev.e)
            seeds = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r[(y >= e - 5) & (y <= e)]]
                                             or [np.zeros(0, np.int64)]))
            ps = cai.prior_set(seeds, e)
            w2 = (sub == d) & (y >= e + 1) & (y <= e + 5)
            adopt = {}
            n_strict = 0
            for k, yy in zip(r[w2], y[w2]):  # r is sorted by (year, work_id)
                a = AUi[AUp[k]:AUp[k + 1]]
                if len(a) == 0 or ps[a].any():
                    continue
                n_strict += 1
                for au in a.tolist():
                    if au not in adopt:
                        adopt[au] = (int(yy), int(k))
            if n_strict != int(ev.Y_strict):
                n_ymismatch += 1
            entry_info[ev.entry_id] = {"ps": ps, "c_auth": c_auth, "n_adopters": len(adopt)}
            for au, (Y, k) in adopt.items():
                if au in bad:
                    continue
                cases.append({"entry_id": ev.entry_id, "concept_id": cid, "d": d, "e": e, "au": au, "Y": Y,
                              "index_row": k, "team": int(C.team[k]), "A_tercile": int(ev.A_tercile),
                              "A_cont": float(ev.A_cont), "single_paper_entry": bool(ev.n_entry_papers == 1),
                              "field_group": ev.field_group, "Y_strict": int(ev.Y_strict)})
    if n_ymismatch:
        raise RuntimeError(f"recomputed Y_strict differs from exp_7 for {n_ymismatch} entries")
    allc = pd.DataFrame(cases)
    logger.info(f"adopters: {len(allc)} (author, entry) pairs over {allc.entry_id.nunique()} entries")
    adopt_summary = {
        "n_adopter_pairs_total": int(len(allc)), "n_distinct_adopter_authors": int(allc.au.nunique()),
        "n_entries": int(len(ent)), "n_entries_with_adopter": int(allc.entry_id.nunique()),
        "share_entries_with_adopter": float(allc.entry_id.nunique() / len(ent)),
        "adopters_per_entry_mean_given_ge1": float(allc.groupby("entry_id").size().mean()),
        "adopters_per_entry_median_given_ge1": float(allc.groupby("entry_id").size().median()),
        "Y_strict_recomputed_match": True}

    crow_sets = {cid: set(G["links"][cid][0].tolist()) for cid in allc.concept_id.unique()}

    def n_prior(au: int, e: int, cid: str) -> int:
        return int(len(C.prior_rows(au, e, crow_sets[cid])))

    allc["n_prior_corpus"] = [n_prior(a, e, c) for a, e, c in zip(allc.au, allc.e, allc.concept_id)]
    adopt_summary["share_adopter_pairs_career_new_corpus"] = float((allc.n_prior_corpus == 0).mean())
    adopt_summary["n_adopter_pairs_measurable_corpus"] = int((allc.n_prior_corpus > 0).sum())
    adopt_summary["n_entries_with_measurable_adopter"] = int(allc[allc.n_prior_corpus > 0].entry_id.nunique())
    allc_full = allc
    if measurable_only:
        allc = allc[allc.n_prior_corpus > 0].copy()
    # ---------- 1c caps (before controls: controls drawn only for sampled cases) ----------
    allc["u"] = rng.random(len(allc))
    allc = allc.sort_values(["entry_id", "u"])
    allc["k_entry"] = allc.groupby("entry_id").cumcount()
    capped = allc[allc.k_entry < MAX_PER_ENTRY].copy()
    capped["u2"] = rng.random(len(capped))
    capped = capped.sort_values(["concept_id", "u2"])
    capped["k_conc"] = capped.groupby("concept_id").cumcount()
    capped = capped[capped.k_conc < concept_cap].copy()
    avail = capped.groupby("A_tercile").size().reindex([1, 2, 3]).fillna(0).astype(int).to_dict()
    target = {t: min(per_tercile, avail[t]) for t in (1, 2, 3)}
    short = min(hard_cap, sum(avail.values())) - sum(target.values())
    redistribution = []
    while short > 0:
        room = {t: avail[t] - target[t] for t in (1, 2, 3) if avail[t] > target[t]}
        if not room:
            break
        for t in sorted(room):
            add = min(room[t], int(np.ceil(short / len(room))))
            target[t] += add
            short -= add
            redistribution.append({"tercile": t, "added": add})
            if short <= 0:
                break
    capped["u3"] = rng.random(len(capped))
    samp = pd.concat([g.sort_values("u3").head(target[t]) for t, g in capped.groupby("A_tercile")])
    samp = samp.drop(columns=["u", "u2", "u3"]).sort_values(["entry_id", "au"]).reset_index(drop=True)
    cap_summary = {"after_entry_cap": int((allc.k_entry < MAX_PER_ENTRY).sum()), "after_concept_cap": int(len(capped)),
                   "available_by_tercile": avail, "target_by_tercile": target, "redistribution": redistribution,
                   "n_cases": int(len(samp)), "n_entries": int(samp.entry_id.nunique()),
                   "n_concepts": int(samp.concept_id.nunique())}
    logger.info(f"caps: {cap_summary}")

    # ---------- 1b controls ----------
    first_year = C.first_year
    samp["act"] = [int(C.activity(np.array([a]), d, Y)[0]) for a, d, Y in zip(samp.au, samp.d, samp.Y)]
    samp["first_year"] = first_year[samp.au.to_numpy()]
    controls, reserve_rows, bal_pre = [], [], []
    case_by_entry = samp.groupby("entry_id").au.apply(set).to_dict()
    all_case_auth = defaultdict(set)
    for eid, a in zip(allc_full.entry_id, allc_full.au):
        all_case_auth[eid].add(a)
    for i, cs in samp.iterrows():
        info = entry_info[cs.entry_id]
        widened = False
        cand = C.dy_candidates(cs.d, (cs.Y,))

        def filt(cd):
            au = cd.au.to_numpy()
            m = ~info["ps"][au] & ~np.isin(au, info["c_auth"]) & ~np.isin(au, list(all_case_auth[cs.entry_id]))
            m &= ~np.isin(au, C.bad_author)
            if measurable_only:
                m &= C.prior_count_all(int(cs.e))[au] > 0
            return cd[m]
        cand = filt(cand)
        if len(cand) < 5:
            cand = filt(C.dy_candidates(cs.d, (cs.Y - 1, cs.Y, cs.Y + 1)))
            widened = True
        if len(cand) == 0:
            controls.append({"case_i": i, "ctrl_au": -1, "relax": -1, "widened": widened, "n_risk": 0})
            continue
        au = cand.au.to_numpy()
        tb = np.array([team_bin(t) for t in cand.team.to_numpy()])
        ab = np.array([act_bin(x) for x in C.activity(au, cs.d, cs.Y)])
        fb = np.array([fy_bin(int(f), cs.e) for f in first_year[au]])
        pb = np.array([prior_bin(int(x)) for x in C.prior_count_all(int(cs.e))[au]])
        ctb, cab, cfb = team_bin(cs.team), act_bin(cs.act), fy_bin(int(cs.first_year), cs.e)
        cpb = prior_bin(int(cs.n_prior_corpus))
        bal_pre.append({"case_i": i, "risk_team_bin_mean": float(tb.mean()), "risk_act_bin_mean": float(ab.mean()),
                        "risk_prior_bin_mean": float(pb.mean()), "risk_log1p_prior_mean": float(np.log1p(C.prior_count_all(int(cs.e))[au]).mean()),
                        "risk_fy_bin_mean": float(fb.mean()), "n_risk": int(len(au))})
        # relaxation order: first-year bin, then activity, then team size, then (corpus primary) prior-works bin
        for relax in range(5):
            m = np.ones(len(au), bool)
            if measurable_only and relax <= 3:
                m &= pb == cpb
            if relax <= 2:
                m &= tb == ctb
            if relax <= 1:
                m &= ab == cab
            if relax == 0:
                m &= fb == cfb
            if m.sum() >= 1:
                break
        pool = au[m]
        k = min(3, len(pool))
        draw = rng.choice(pool, k, replace=False)
        chosen, floor_applied = int(draw[0]), False
        if cs.n_prior_corpus > 0 and n_prior(chosen, cs.e, cs.concept_id) == 0:
            for rsv in draw[1:]:
                if n_prior(int(rsv), cs.e, cs.concept_id) > 0:
                    chosen, floor_applied = int(rsv), True
                    break
        rest = [int(x) for x in draw if int(x) != chosen]
        controls.append({"case_i": i, "ctrl_au": chosen, "relax": relax, "widened": widened, "n_risk": int(len(au)),
                         "n_stratum": int(m.sum()), "floor_applied": floor_applied, "reserves": rest})
    ct = pd.DataFrame(controls).set_index("case_i")
    samp = samp.join(ct)
    n_noctrl = int((samp.ctrl_au < 0).sum())
    samp = samp[samp.ctrl_au >= 0].reset_index(drop=True)
    samp["stratum"] = np.arange(len(samp))
    # long table: one row per (stratum, member)
    rows = []
    for cs in samp.itertuples():
        base = {"stratum": cs.stratum, "entry_id": cs.entry_id, "concept_id": cs.concept_id, "d": cs.d, "e": cs.e,
                "Y": cs.Y, "A_tercile": cs.A_tercile, "A_cont": cs.A_cont, "field_group": cs.field_group,
                "single_paper_entry": cs.single_paper_entry, "relax": cs.relax, "widened": cs.widened}
        rows.append({**base, "au": cs.au, "case": 1, "role": "case"})
        rows.append({**base, "au": cs.ctrl_au, "case": 0, "role": "control"})
        for j, rv in enumerate(cs.reserves or []):
            rows.append({**base, "au": rv, "case": 0, "role": f"reserve{j + 1}"})
    L = pd.DataFrame(rows)
    # member covariates (pre-exposure only)
    L["n_prior_corpus"] = [n_prior(int(a), int(e), c) for a, e, c in zip(L.au, L.e, L.concept_id)]
    L["first_year"] = first_year[L.au.to_numpy()]
    L["act"] = [int(C.activity(np.array([int(a)]), int(d), int(Y))[0]) for a, d, Y in zip(L.au, L.d, L.Y)]
    L["team_index"] = 0
    idx_team = {}
    for (d, Y) in set(zip(L.d, L.Y)):
        t = C.dy_candidates(int(d), (int(Y),))
        idx_team[(d, Y)] = dict(zip(t.au, t.team))
    L["team_index"] = [idx_team.get((d, Y), {}).get(int(a), np.nan) for a, d, Y in zip(L.au, L.d, L.Y)]
    L.loc[L.role == "case", "team_index"] = L[L.role == "case"].stratum.map(samp.set_index("stratum").team)
    L["raw_author_id"] = C.raw[L.au.to_numpy()]
    L["team_bin"] = [team_bin(int(t)) if pd.notna(t) else -1 for t in L.team_index]
    L["act_bin"] = [act_bin(int(a)) for a in L.act]
    L["fy_bin"] = [fy_bin(int(f), int(e)) for f, e in zip(L.first_year, L.e)]
    L["prior_bin"] = [prior_bin(int(n)) for n in L.n_prior_corpus]

    # ---------- 1d target sets ----------
    nat = F.Nativeness(G["prof"])
    screen_all = mc.load_screen()
    screen_all = screen_all[(screen_all.arm == "main") & (screen_all.fold == "screen") & screen_all.MAIN & screen_all.kw5]
    pairs = {(int(d), F.block_of(int(e))) for d, e in zip(ent.d, ent.e)}
    prof_pool = build_prof_pool(G, pairs)
    tag_cache = {}

    def entry_nodes(cid, d, e):
        k = (cid, d, e)
        if k not in tag_cache:
            own = con.loc[cid].own_node
            own = int(own) if pd.notna(own) else None
            _, _, nodes = F.event_tags(G, cid, d, e, own)
            cnt = Counter(int(x) for x in nodes)
            tag_cache[k] = [n for n, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]
        return tag_cache[k]

    tgt_rows, targets = [], {}
    for ev in ent.itertuples():
        cid, d, e = ev.concept_id, int(ev.d), int(ev.e)
        own = con.loc[cid].own_node
        own = int(own) if pd.notna(own) else None
        others = screen_all[(screen_all.d == d) & (screen_all.concept_id != cid) & ((screen_all.e - e).abs() <= 1)]
        plac_nodes, plac_entry = [], None
        if len(others):
            o = others.iloc[int(rng.integers(len(others)))]
            plac_entry = f"{o.concept_id}|{int(o.d)}|{int(o.e)}"
            plac_nodes = entry_nodes(o.concept_id, int(o.d), int(o.e))
        row = pd.Series({"concept_id": cid, "d": d, "e": e, "o": ev.o})
        t = entry_targets(G, C, row, nat, prof_pool, rng, plac_nodes, own)
        t["plac_entry"] = plac_entry
        t["plac_full"] = plac_nodes[:N_P_MAX]
        targets[ev.entry_id] = t
        cls = Counter(p["cls"] for p in t["P"])
        tgt_rows.append({"entry_id": ev.entry_id, "n_P": len(t["P"]), "n_NEG": len(t["NEG"]), "n_PLAC": len(t["PLAC"]),
                         "plac_entry": plac_entry, "neg_relaxed": t["neg_relaxed"],
                         "n_native": cls.get("NATIVE", 0), "n_adjacent": cls.get("ADJACENT", 0),
                         "n_foreign": cls.get("FOREIGN", 0), "n_unprofiled": cls.get("UNPROFILED", 0),
                         "n_companion": sum(p["companion"] for p in t["P"]),
                         "P_nodes": [p["node"] for p in t["P"]], "P_w": [p["w"] for p in t["P"]],
                         "P_share": [np.nan if p["share"] is None else p["share"] for p in t["P"]],
                         "P_cls": [p["cls"] for p in t["P"]], "P_comp": [bool(p["companion"]) for p in t["P"]],
                         "NEG_nodes": t["NEG"], "PLAC_nodes": t["PLAC"], "PLAC_full_nodes": t["plac_full"]})
    T = pd.DataFrame(tgt_rows)

    # ---------- 1e entry-level mediators (all co-primary entries) ----------
    med = []
    totals = G["totals"]
    blk_years = {"2000-2004": range(2000, 2005), "2005-2009": range(2005, 2010), "2010-2014": range(2010, 2015)}
    for ev in (ent.itertuples() if with_mediators else []):
        cid, d, e = ev.concept_id, int(ev.d), int(ev.e)
        t = targets[ev.entry_id]
        crm = np.zeros(C.nw, bool)
        crm[G["links"][cid][0]] = True
        hm = C.host_authors_mask(d, e)
        n_host = int(hm.sum())
        allnodes = list(t["all_w"].keys())
        cols = [C.node_col[n] for n in allnodes if n in C.node_col]
        ex = C.exposed_authors(cols, e, crm) & hm
        nat_cols = [C.node_col[p["node"]] for p in t["P"] if p["cls"] == "NATIVE" and p["node"] in C.node_col]
        adj_cols = [C.node_col[p["node"]] for p in t["P"] if p["cls"] == "ADJACENT" and p["node"] in C.node_col]
        exn = C.exposed_authors(nat_cols, e, crm) & hm
        exa = C.exposed_authors(adj_cols, e, crm) & hm
        blk = t["blk"]
        Nd = sum(totals.get((d, yy), 0) for yy in blk_years[blk])
        m1, unprof_w = 0.0, 0.0
        for node, w in t["all_w"].items():
            p = G["prof"].get((node, blk))
            if p is None:
                unprof_w += w
                continue
            m1 += w * p[1].get(d, 0) / Nd * 1e4 if Nd > 0 else 0.0
        med.append({"entry_id": ev.entry_id, "n_host_authors_pre": n_host, "M2_count": int(ex.sum()),
                    "M2": float(np.log1p(ex.sum())), "M2_share": float(ex.sum() / n_host) if n_host else 0.0,
                    "M2_native_count": int(exn.sum()), "M2_native": float(np.log1p(exn.sum())),
                    "M2_adjacent_count": int(exa.sum()), "M2_adjacent": float(np.log1p(exa.sum())),
                    "M1_raw": m1, "M1": float(np.log1p(m1)), "M1_unprofiled_w": unprof_w, "N_d_block": int(Nd)})
    Med = pd.DataFrame(med)
    if with_mediators:
        ent = ent.merge(Med, on="entry_id", how="left")
    summary = {"adopters": adopt_summary, "caps": cap_summary, "n_cases_without_control": n_noctrl,
               "n_strata": int(len(samp)),
               "relax_counts": samp.relax.value_counts().sort_index().to_dict(),
               "widened": int(samp.widened.sum()), "floor_applied": int(samp.floor_applied.sum()),
               "career_new_cases_corpus": int((samp.n_prior_corpus == 0).sum()),
               "targets": {"mean_n_P": float(T.n_P.mean()), "mean_n_NEG": float(T.n_NEG.mean()),
                           "mean_n_PLAC": float(T.n_PLAC.mean()), "entries_without_placebo": int((T.n_PLAC == 0).sum()),
                           "neg_relaxed_total": int(T.neg_relaxed.sum())},
               "mediators": ({"M2_count_mean": float(Med.M2_count.mean()), "M2_share_mean": float(Med.M2_share.mean()),
                              "M1_unprofiled_w_mean": float(Med.M1_unprofiled_w.mean())} if with_mediators else None),
               "A_cont_tercile_cuts": q.tolist()}
    summary["measurable_only"] = measurable_only
    return {"entries": ent, "cases_all": allc_full, "long": L, "targets": T, "summary": summary, "bal_pre": pd.DataFrame(bal_pre),
            "C": C}
