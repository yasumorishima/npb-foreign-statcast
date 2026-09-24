"""Layer 2 step 2: AAA->MLB additive offsets δ(m, s, r, g) exactly as PREREG_layer2.md §3 (md5 8a7305c9…).

Reads l2/agg_*, l2/start_*, l2/firstbat_* (from l2_agg.py) and the statsapi AAA team->league map.
Writes l2/delta.csv (one row per registered cell, with the pooling level actually used) and
l2/segments_<season>.parquet (per player: AAA league and role per season, used for pooling in step 3).
No NPB data is read.
"""
import json, sys, urllib.request
import numpy as np, pandas as pd

SEASONS = [int(x) for x in sys.argv[1:]] or [2023, 2024, 2025]
SEED, NBOOT, MINPAIR, MINPA = 20260924, 2000, 20, 50
MEAS = {  # measure: (numerator(t), denominator column)
    "woba": (lambda t: t.wv, "pa"), "xwoba": (lambda t: t.xwv, "pa"), "k": (lambda t: t.k, "pa"),
    "bb": (lambda t: t.bb, "pa"), "hr": (lambda t: t.hr, "pa"), "brl": (lambda t: t.brl, "pa"),
    "kbb": (lambda t: t.k - t.bb, "pa"), "fipn": (lambda t: 13 * t.hr + 3 * (t.bb + t.hbp) - 2 * t.k, "pa"),
    "whiff": (lambda t: t.swstr, "swings"), "chase": (lambda t: t.oozsw, "ooz"), "csw": (lambda t: t.csw, "np")}


def league_map(season):
    u = f"https://statsapi.mlb.com/api/v1/teams?sportId=11&season={season}"
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "python-requests/2.32"}), timeout=30))
    m = {t["abbreviation"]: t["league"]["name"] for t in j["teams"]}
    names = set(m.values())
    assert names == {"International League", "Pacific Coast League"}, names
    return {k: ("IL" if v.startswith("International") else "PCL") for k, v in m.items()}


def player_table(level, season, role, lg=None):
    a = pd.read_parquet(f"l2/agg_{level}_{season}_{role}.parquet")
    tot = a.groupby("player").sum(numeric_only=True)
    if lg is not None:
        unk = set(a.team) - set(lg)
        assert not unk, ("AAA teams missing from league map", unk)
        main = a.sort_values(["pa", "team"], ascending=[False, True], kind="mergesort").drop_duplicates("player").set_index("player").team
        tot["league"] = main.map(lg)
    if role == "pit":
        st = pd.read_parquet(f"l2/start_{level}_{season}.parquet")
        tot = tot.join(st[["games", "starts"]])
        tot["r"] = np.where(tot.starts / tot.games >= 0.5, "SP", "RP")
    else:
        tot["r"] = "bat"
    first = pd.read_parquet(f"l2/start_{level}_{season}.parquet")["first"] if role == "pit" \
        else pd.read_parquet(f"l2/firstbat_{level}_{season}.parquet")["first"]
    tot["first"] = first
    return tot


def nfinite(p, m):
    f, den = MEAS[m]
    return int(((p[den + "_m"] > 0) & (p[den + "_a"] > 0)).sum())


def delta(p, m, rng=None):
    f, den = MEAS[m]
    x_m = f(p.filter(like="_m").rename(columns=lambda c: c[:-2])) / p[den + "_m"]
    x_a = f(p.filter(like="_a").rename(columns=lambda c: c[:-2])) / p[den + "_a"]
    w = 2 / (1 / p[den + "_m"] + 1 / p[den + "_a"])
    ok = np.isfinite(x_m) & np.isfinite(x_a) & (w > 0)
    ids = np.asarray(p.index)[ok.values]
    x_m, x_a, w = x_m[ok].values, x_a[ok].values, w[ok].values
    d = np.sum(w * (x_m - x_a)) / np.sum(w)
    se = np.nan
    if rng is not None and len(w) > 1:  # player bootstrap: resample unique players (Amendment 1 §4)
        uid = np.unique(ids); rows = {u: np.flatnonzero(ids == u) for u in uid}
        bs = []
        for _ in range(NBOOT):
            i = np.concatenate([rows[u] for u in rng.choice(uid, len(uid))])
            bs.append(np.sum(w[i] * (x_m[i] - x_a[i])) / np.sum(w[i]))
        se = float(np.std(bs, ddof=1))
    slope = np.polyfit(x_a, x_m, 1, w=np.sqrt(w))[0] if len(w) > 2 else np.nan
    return d, se, int(len(w)), slope


if __name__ == "__main__":
    pairs = []
    for s in SEASONS:
        lg = league_map(s)
        for role in ("bat", "pit"):
            A = player_table("aaa", s, role, lg); M = player_table("mlb", s, role)
            A[["league", "r"]].assign(season=s, role=role).to_parquet(f"l2/segments_{s}_{role}.parquet")
            j = A.join(M, lsuffix="_a", rsuffix="_m", how="inner")
            j = j[(j.pa_a >= MINPA) & (j.pa_m >= MINPA) & (j.r_a == j.r_m)].copy()
            j["season"], j["g"], j["r"], j["role"] = s, j.league, j.r_a, role
            j["order"] = np.select([j.first_m < j.first_a, j.first_m > j.first_a], ["demotion_first", "callup_first"], "same_day")
            pairs.append(j)
            print(s, role, "pairs", len(j), j.groupby(["r", "g"]).size().to_dict(), flush=True)
    P = pd.concat(pairs)
    rng = np.random.default_rng(SEED)
    out = []
    for m in MEAS:
        roles = ["bat"] if m in ("woba", "xwoba", "bb", "k", "hr", "brl", "whiff", "chase") else []
        roles += ["SP", "RP"] if m in ("kbb", "csw", "fipn", "xwoba", "hr", "brl") else []
        for r in roles:
            base = P[P.role == ("bat" if r == "bat" else "pit")]
            for s in SEASONS:
                for g in ("IL", "PCL"):
                    for lvl, sel in [("s,r,g", (base.season == s) & (base.r == r) & (base.g == g)),
                                     ("s,r", (base.season == s) & (base.r == r)),
                                     ("s,pit" if r != "bat" else "s,r", base.season == s),
                                     ("all seasons", base.index == base.index)]:
                        if nfinite(base[sel], m) >= MINPAIR:
                            break
                    thin = nfinite(base[sel], m) < MINPAIR
                    d, se, n, slope = delta(base[sel], m, rng)
                    sub = {o: delta(base[sel & (base.order == o)], m)[0] if (sel & (base.order == o)).sum() > 1 else np.nan
                           for o in ("callup_first", "demotion_first", "same_day")}
                    out.append(dict(m=m, s=s, r=r, g=g, level=lvl, thin=thin, delta=d, se=se, n=n, slope=slope, **sub))
    D = pd.DataFrame(out)
    D.to_csv("l2/delta.csv", index=False)
    print(D.round(4).to_string())
