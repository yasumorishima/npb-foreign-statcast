"""Layer 2 step 3: combined MLB + translated-AAA measures (§4), the single frozen model (§5), frozen 2026 predictions,
and the reliability-shrunk secondary (Amendment 1 §5). PREREG_layer2.md md5 8a7305c9…; reads no 2026 NPB statistic.

Outputs: l2/feat_train_{bat,pit}.csv, l2/pred26L2_{bat,pit}.csv, l2/coefL2.csv, l2/relk.csv, and their md5s.
Gates: every MLB season with statsapi PA/BF > 0 has a per-player file (training and 2026);
every registered measure used for a role has a δ row for each AAA segment; for every training arrival the MLB part
equals Pillar 1 (n) and, for arrivals without AAA, every registered measure equals Pillar 1 exactly (NaN-aware).
"""
import glob, hashlib, os
import numpy as np, pandas as pd
import ana1
from l2_agg import prep, S
from l2_delta import MEAS

HF = "https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
D = pd.read_csv("l2/delta.csv")
assert set(D.s) == {2023, 2024, 2025}, "delta.csv must cover 2023-2025"
ROLEMEAS = {"bat": [("Y1", "woba", "xwoba"), ("Y2", "k", "whiff"), ("Y3", "bb", "chase"), ("Y4", "hr", "brl")],
            "pit": [("P1", "kbb", "csw"), ("P2", "fipn", "xwoba"), ("P3", "hr", "brl")]}
NEED = {k: {x for _, a, b in v for x in (a, b)} for k, v in ROLEMEAS.items()}
AAA = {(s, role): pd.read_parquet(f"l2/agg_aaa_{s}_{role}.parquet").groupby("player").sum(numeric_only=True)
       for s in (2023, 2024, 2025) for role in ("bat", "pit")}
SEG = {(s, role): pd.read_parquet(f"l2/segments_{s}_{role}.parquet") for s in (2023, 2024, 2025) for role in ("bat", "pit")}
STAT = {"bat": pd.read_parquet(HF + "statsapi_batting.parquet", columns=["player_id", "season", "plateAppearances"])
        .rename(columns={"plateAppearances": "c"}),
        "pit": pd.read_parquet(HF + "statsapi_pitching.parquet", columns=["player_id", "season", "battersFaced"])
        .rename(columns={"battersFaced": "c"})}


def check_files(kind, pid, year):
    m = STAT[kind]
    seasons = m[(m.player_id == pid) & (m.season >= 2015) & (m.season < year) & (m.c > 0)].season.unique()
    miss = [y for y in seasons if not os.path.exists(f"mlb/{kind}_{pid}_{y}.csv")]
    assert not miss, (kind, pid, miss)


def mlb_sums(kind, pid, year):
    check_files(kind, pid, year)
    fs = [f for f in glob.glob(f"mlb/{kind}_{pid}_*.csv") if 2015 <= int(f.split("_")[-1][:4]) < year]
    if not fs:
        return pd.Series(0.0, index=S)
    return prep(pd.concat([pd.read_csv(f, low_memory=False) for f in fs], ignore_index=True))[S].sum().astype(float)


def parts(kind, pid, year):
    """MLB sums and a list of AAA segments (season, sums, δ per measure)."""
    m = mlb_sums(kind, pid, year)
    segs = []
    for s in range(2023, min(year, 2026)):
        if pid not in AAA[(s, kind)].index:
            continue
        a = AAA[(s, kind)].loc[pid]; seg = SEG[(s, kind)].loc[pid]
        r = "bat" if kind == "bat" else seg.r
        dl = {}
        for k in NEED[kind]:
            row = D[(D.m == k) & (D.s == s) & (D.r == r) & (D.g == seg.league)]
            assert len(row) == 1, (k, s, r, seg.league)
            dl[k] = float(row.delta.iloc[0])
        segs.append((s, a, dl))
    return m, segs


def combine(m, segs, kind, shrink=None):
    """(num_MLB + Σ den_seg·v_seg)/den_total with v_seg = translated AAA rate (optionally shrunk toward mu)."""
    out = {}
    one = lambda t: float(t.iloc[0]) if hasattr(t, "iloc") else float(t)
    for k in NEED[kind]:
        f, dcol = MEAS[k]
        num = one(f(m.to_frame().T)); den = float(m[dcol])
        num_a = sum(one(f(a.to_frame().T)) for _, a, _ in segs)
        den_a = sum(float(a[dcol]) for _, a, _ in segs)
        if den_a > 0:
            v = num_a / den_a + sum(float(a[dcol]) * dl[k] for _, a, dl in segs) / den_a
            if shrink is not None:
                mu, kk = shrink[k]
                v = mu + den_a / (den_a + kk) * (v - mu)
            num += den_a * v; den += den_a
        out[k] = num / den if den > 0 else np.nan
    n_aaa = sum(float(a.pa) for _, a, _ in segs)
    out.update(n_mlb=float(m.pa), n_aaa=n_aaa, n_tot=float(m.pa) + n_aaa)
    return out


def rel_k(kind):
    """Amendment 1 §5: split-half reliability → k per measure (AAA 2023–2025 only)."""
    key = "batter" if kind == "bat" else "pitcher"
    res = {}
    sl = pd.concat([pd.read_parquet(f"l2/slim_aaa_{s}.parquet").assign(season=s) for s in (2023, 2024, 2025)])
    sl = sl.astype({c: "int64" for c in S if c not in ("wv", "xwv")})  # no int16 overflow in sums
    for k in sorted(NEED[kind]):
        f, dcol = MEAS[k]
        x = sl[sl.pa > 0] if dcol == "pa" else sl[sl.np > 0]  # Amendment 1 §5: odd/even PA, or odd/even pitches
        order = ["season", key, "game_date", "game_pk", "at_bat_number"] + ([] if dcol == "pa" else ["pitch_number"])
        x = x.sort_values(order)
        x = x.assign(half=x.groupby(["season", key]).cumcount() % 2)
        g = x.groupby(["season", key, "half"])[S].sum()
        num = f(g); den = g[dcol]
        t = pd.DataFrame({"num": num, "den": den}).unstack("half")
        full = t["den"].sum(axis=1)
        t = t[full >= 100]
        r0 = t["num"][0] / t["den"][0]; r1 = t["num"][1] / t["den"][1]
        ok = np.isfinite(r0) & np.isfinite(r1)
        r = np.corrcoef(r0[ok], r1[ok])[0, 1]; assert 0 < r < 1, (kind, k, r); rho = 2 * r / (1 + r); nbar = float(full[full >= 100].mean())
        res[k] = (nbar * (1 - rho) / rho, r, rho, nbar, len(t))
    return res


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


if __name__ == "__main__":
    coef, rk = [], []
    r26 = pd.read_csv("r26_links.csv", dtype={"key_npb": str}).dropna(subset=["key_mlbam"])
    for kind, fr in (("bat", ana1.bat), ("pit", ana1.pit)):
        tr = fr.copy()
        P = {r.Index: parts(kind, int(r.key_mlbam), int(r.year)) for r in tr.itertuples()}
        tr = tr.join(pd.DataFrame([combine(*P[i], kind) for i in tr.index], index=tr.index))
        p1 = pd.read_csv(f"feat_{kind}.csv").set_index(["key_npb", "year"])
        t2 = tr.set_index(["key_npb", "year"])
        has = p1.n.notna()
        assert np.array_equal(t2.loc[p1.index[has], "n_mlb"].values, p1.n[has].values.astype(float)), "n_mlb != Pillar 1 n"
        no_aaa = t2.index[(t2.n_aaa == 0)].intersection(p1.index[has])
        for c in NEED[kind]:
            a, b = t2.loc[no_aaa, c].values, p1.loc[no_aaa, c].values
            assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=0, atol=1e-12), c
        print(kind, "gates ok: n_mlb == Pillar 1 for", int(has.sum()), "| measures == Pillar 1 for", len(no_aaa), "no-AAA arrivals", flush=True)
        tr.to_csv(f"l2/feat_train_{kind}.csv", index=False)
        T = tr[(tr.n_tot >= 150) & tr.ok100]
        print(kind, "training n", len(T), "| of which AAA-only", int((T.n_mlb < 150).sum()), flush=True)
        new = r26[r26.kind == kind].copy()
        Pn = {x.Index: parts(kind, int(x.key_mlbam), 2026) for x in new.itertuples()}
        new = new.join(pd.DataFrame([combine(*Pn[i], kind) for i in new.index], index=new.index))
        RK = rel_k(kind)
        shrink = {k: (float(T[k].mean()), RK[k][0]) for k in NEED[kind]}
        for k, v in RK.items():
            rk.append((kind, k, *v, shrink[k][0]))
        sh = pd.DataFrame([combine(*Pn[i], kind, shrink=shrink) for i in new.index], index=new.index)
        new = new.join(sh[list(NEED[kind])].add_suffix("_shr"))
        new = new[new.n_tot >= 150].copy()
        new["aaa_only"] = new.n_mlb < 150
        for y, a, b in ROLEMEAS[kind]:
            new[f"{y}_C"] = T[y].mean(); coef.append((kind, y, "C", T[y].mean(), np.nan))
            for nm, x in (("A", a), ("B", b)):
                b1, b0 = np.polyfit(T[x].values, T[y].values, 1)
                new[f"{y}_{nm}"] = b0 + b1 * new[x]
                new[f"{y}_{nm}_shr"] = b0 + b1 * new[x + "_shr"]
                coef.append((kind, y, nm, b0, b1))
        keep = ["team", "key_npb", "name", "npb_en", "key_mlbam", "pos", "n_mlb", "n_aaa", "n_tot", "aaa_only"] + \
               sorted(NEED[kind]) + [c for c in new.columns if c[:2] in ("Y1", "Y2", "Y3", "Y4", "P1", "P2", "P3") and "_" in c]
        new[keep].to_csv(f"l2/pred26L2_{kind}.csv", index=False)
        print(new[["npb_en", "n_mlb", "n_aaa", "aaa_only"] + [c for c in new.columns if c.startswith(("Y1_", "P1_"))]]
              .round(4).to_string(), flush=True)
    pd.DataFrame(coef, columns=["kind", "outcome", "model", "b0", "b1"]).to_csv("l2/coefL2.csv", index=False)
    pd.DataFrame(rk, columns=["kind", "measure", "k", "r_half", "rho_full", "nbar", "n_playerseasons", "mu"]).to_csv("l2/relk.csv", index=False)
    for p in ["l2/pred26L2_bat.csv", "l2/pred26L2_pit.csv", "l2/coefL2.csv", "l2/relk.csv", "l2/delta.csv", "l2_pred26.py", "l2_agg.py", "l2_delta.py"]:
        print(md5(p), p)
    print("written")
