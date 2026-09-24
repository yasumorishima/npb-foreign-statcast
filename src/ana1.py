"""Pillar 1 analysis exactly as frozen in PREREG_pillar1.md (md5 77977d43ac5c315da48710ef6218a7c5).

Builds MLB A/B measures from mlb/<kind>_<mlbam>_<season>.csv, NPB first-season outcomes from the season
CSVs (summed by key_npb), runs leave-one-arrival-year-out CV and the centred player bootstrap.
Writes feat_bat.csv / feat_pit.csv and prints every registered number.
"""
import glob, hashlib, sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

assert hashlib.md5(open("PREREG_pillar1.md", "rb").read()).hexdigest() == "77977d43ac5c315da48710ef6218a7c5"
SEED, NBOOT = 20260924, 2000

# completeness: every (kind, player, season) the fetcher planned must exist, and the fetch must have finished
import os
assert open("fetch_mlb.log").read().strip().splitlines()[-1] == "done", "fetch not finished"
_HF = "https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
_L = pd.read_csv("links.csv", usecols=["kind", "key_mlbam", "year"])
_missing = []
for _k, _t, _c in [("bat", "statsapi_batting", "plateAppearances"), ("pit", "statsapi_pitching", "battersFaced")]:
    _m = pd.read_parquet(_HF + _t + ".parquet", columns=["player_id", "season", _c])
    for _r in _L[_L.kind == _k].itertuples():
        _s = _m[(_m.player_id == _r.key_mlbam) & (_m.season >= 2015) & (_m.season < _r.year) & (_m[_c] > 0)]
        if _s[_c].sum() >= 100:
            _missing += [f"mlb/{_k}_{_r.key_mlbam}_{y}.csv" for y in _s.season.unique()
                         if not os.path.exists(f"mlb/{_k}_{_r.key_mlbam}_{y}.csv")]
assert not _missing, ("missing files", _missing[:10], len(_missing))

PA_EVENTS = {"single", "double", "triple", "home_run", "walk", "hit_by_pitch", "strikeout", "strikeout_double_play",
             "field_out", "force_out", "grounded_into_double_play", "double_play", "triple_play", "fielders_choice",
             "fielders_choice_out", "field_error", "sac_fly", "sac_fly_double_play", "other_out"}
EXCL_EVENTS = {"intent_walk", "sac_bunt", "sac_bunt_double_play", "catcher_interf", "truncated_pa"}
SWSTR = {"swinging_strike", "swinging_strike_blocked", "foul_tip", "missed_bunt", "bunt_foul_tip", "swinging_pitchout"}
SWING_EXTRA = {"foul", "foul_bunt", "foul_pitchout"}
PITCH_EXCL = {"intent_ball", "pitchout", "automatic_ball", "automatic_strike"}
DEFAULTS = {(82.9, -21.0), (80.0, 69.0), (90.3, -17.0), (89.2, 39.0)}


def ip_outs(x):
    w, f = str(x).split(".") if "." in str(x) else (str(x), "0")
    assert f in ("0", "1", "2"), x
    return int(w) * 3 + int(f)


# ---------------- MLB features ----------------
def mlb_features(kind, pid, npb_year, min_season=2015):
    files = [f for f in glob.glob(f"mlb/{kind}_{pid}_*.csv")
             if min_season <= int(f.split("_")[-1][:4]) < npb_year]
    if not files:
        return None
    ds = []
    for f in files:
        d = pd.read_csv(f, low_memory=False)
        role = "batter" if kind == "bat" else "pitcher"
        season = int(f.split("_")[-1][:4])
        assert (d[role] == pid).all() and (d.game_year == season).all() and (d.game_type == "R").all(), f
        ds.append(d)
    d = pd.concat(ds, ignore_index=True)
    ev = d.events.dropna()
    unknown = set(ev) - PA_EVENTS - EXCL_EVENTS
    assert not unknown, (pid, unknown)
    pa = d[d.events.isin(PA_EVENTS)].copy()
    n = len(pa)
    if n == 0:
        return None
    ls, la = pa.launch_speed, pa.launch_angle
    pair_default = np.array([(a, b) in DEFAULTS for a, b in zip(ls.round(1), la.round(1))])
    valid = ls.notna() & la.notna() & ~pair_default
    bbe = pa.type == "X"
    use_x = bbe & valid & pa.estimated_woba_using_speedangle.notna()
    wv = pa.woba_value.astype(float)
    assert wv.notna().all()
    xw = np.where(use_x, pa.estimated_woba_using_speedangle, wv)
    K = pa.events.isin({"strikeout", "strikeout_double_play"}).sum()
    BB = (pa.events == "walk").sum()
    HBP = (pa.events == "hit_by_pitch").sum()
    HR = (pa.events == "home_run").sum()
    barrels = (bbe & valid & (pa.launch_speed_angle == 6)).sum()
    p = d[~d.description.isin(PITCH_EXCL)]
    desc = p.description
    swstr = desc.isin(SWSTR)
    swing = swstr | desc.isin(SWING_EXTRA) | desc.str.startswith("hit_into_play")
    ooz = p.zone.isin([11, 12, 13, 14])
    out = dict(n=n, woba=wv.mean(), xwoba=float(np.mean(xw)), fallback=float((bbe & ~use_x).sum() / max(bbe.sum(), 1)),
               k=K / n, bb=BB / n, hr=HR / n, brl=barrels / n, kbb=(K - BB) / n,
               fipn=(13 * HR + 3 * (BB + HBP) - 2 * K) / n,
               whiff=swstr.sum() / swing.sum(), chase=(swing & ooz).sum() / ooz.sum(),
               csw=(swstr | (desc == "called_strike")).sum() / len(p))
    if kind == "pit":
        g = d.sort_values(["game_pk", "at_bat_number", "pitch_number"]).groupby("game_pk").head(1)
        started = ((g.inning == 1) & (g.outs_when_up == 0) & g.on_1b.isna() & g.on_2b.isna() & g.on_3b.isna()
                   & (g.pitch_number == 1))
        out["start_share"] = started.mean()
    return out


# ---------------- NPB outcomes ----------------
L = pd.read_csv("links.csv")[["player", "team", "year", "kind", "key_npb", "key_mlbam"]]
H = pd.read_csv("npb_hitters_2015_2025.csv")
P = pd.read_csv("npb_pitchers_2015_2025.csv")
H["TB"] = H.SLG * H.AB
P["OUTS"] = P.IP.map(ip_outs)
lg = H.groupby("year").apply(lambda g: pd.Series(dict(
    obp=(g.H + g.BB + g.HBP).sum() / (g.PA - g.SH).sum(), slg=g.TB.sum() / g.AB.sum())), include_groups=False)
lg["ops"] = lg.obp + lg.slg
lgera = P.groupby("year").apply(lambda g: 27 * g.ER.sum() / g.OUTS.sum(), include_groups=False)

assert not H.duplicated(["player", "team", "year"]).any() and not P.duplicated(["player", "team", "year"]).any()
bat = L[L.kind == "bat"].merge(H, on=["player", "team", "year"], how="inner")
pit = L[L.kind == "pit"].merge(P, on=["player", "team", "year"], how="inner")
assert len(bat) == (L.kind == "bat").sum() and len(pit) == (L.kind == "pit").sum()
bat = bat.groupby(["key_npb", "year"]).agg(key_mlbam=("key_mlbam", "first"), PA=("PA", "sum"), AB=("AB", "sum"),
      H=("H", "sum"), BB=("BB", "sum"), HBP=("HBP", "sum"), SO=("SO", "sum"), SH=("SH", "sum"), HR=("HR", "sum"),
      TB=("TB", "sum")).reset_index()
pit = pit.groupby(["key_npb", "year"]).agg(key_mlbam=("key_mlbam", "first"), BF=("BF", "sum"), OUTS=("OUTS", "sum"),
      ER=("ER", "sum"), BB=("BB", "sum"), SO=("SO", "sum"), HRA=("HRA", "sum")).reset_index()
obp = (bat.H + bat.BB + bat.HBP) / (bat.PA - bat.SH)
bat["Y1"] = (obp + bat.TB / bat.AB) / bat.year.map(lg.ops)
bat["Y2"], bat["Y3"], bat["Y4"] = bat.SO / bat.PA, bat.BB / bat.PA, bat.HR / bat.PA
bat["ok100"], bat["ok50"] = bat.PA >= 100, bat.PA >= 50
pit["P1"] = (pit.SO - pit.BB) / pit.BF
pit["P2"] = 27 * pit.ER / pit.OUTS - pit.year.map(lgera)
pit["P3"] = pit.HRA / pit.BF
pit["ok100"], pit["ok50"] = pit.OUTS >= 90, pit.OUTS >= 45


def attach(df, kind, min_season=2015):
    rows = [mlb_features(kind, int(r.key_mlbam), int(r.year), min_season) for r in df.itertuples()]
    f = pd.DataFrame([r if r else {} for r in rows], index=df.index)
    return df.join(f)


# ---------------- models ----------------
def ols_oof(df, y, xs):
    pred = np.full(len(df), np.nan)
    yrs = df.year.values
    for fy in np.unique(yrs):
        tr, te = yrs != fy, yrs == fy
        if tr.sum() < len(xs) + 2:
            continue
        if not xs:
            pred[te] = df[y].values[tr].mean(); continue
        X = np.column_stack([np.ones(tr.sum())] + [df[x].values[tr] for x in xs])
        b = np.linalg.lstsq(X, df[y].values[tr], rcond=None)[0]
        Xt = np.column_stack([np.ones(te.sum())] + [df[x].values[te] for x in xs])
        pred[te] = Xt @ b
    return pred


def logit_oof(df, y, xs):
    pred = np.full(len(df), np.nan)
    yrs = df.year.values
    for fy in np.unique(yrs):
        tr, te = yrs != fy, yrs == fy
        yt = df[y].values[tr]
        if len(set(yt)) < 2:
            return None
        m = LogisticRegression(penalty=None, max_iter=1000).fit(df[xs].values[tr], yt)
        pred[te] = m.predict_proba(df[xs].values[te])[:, 1]
    return pred


def mae(df, y, xs, w=None):
    pr = ols_oof(df, y, xs)
    assert np.isfinite(pr).all(), "fold without prediction"
    e = np.abs(df[y].values - pr)
    return np.average(e, weights=w) if w is not None else e.mean()


def compare(df, y, a, b, wcol=None, boot=True):
    w = df[wcol].values if wcol else None
    mc, ma, mb = mae(df, y, [], w), mae(df, y, [a], w), mae(df, y, [b], w)
    mab = mae(df, y, [a, b], w)
    res = dict(n=len(df), C=mc, A=ma, B=mb, AB=mab, dBA=ma - mb, dBC=mc - mb)
    if boot:
        rng = np.random.default_rng(SEED)
        dA, dC = [], []
        for _ in range(NBOOT):
            s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
            ws = s[wcol].values if wcol else None
            m_b = mae(s, y, [b], ws)
            dA.append(mae(s, y, [a], ws) - m_b); dC.append(mae(s, y, [], ws) - m_b)
        dA, dC = np.array(dA), np.array(dC)
        res["p_BA"] = float(np.mean((dA - res["dBA"]) >= res["dBA"]))
        res["p_BC"] = float(np.mean((dC - res["dBC"]) >= res["dBC"]))
        # sign-flip (secondary)
        eA = np.abs(df[y].values - ols_oof(df, y, [a])); eB = np.abs(df[y].values - ols_oof(df, y, [b]))
        d = eA - eB; r2 = np.random.default_rng(SEED)
        flips = r2.choice([-1, 1], size=(20000, len(d))) @ d / len(d)
        res["p_signflip"] = float(np.mean(flips >= d.mean()))
    return res


def s1(df, a, b):
    pa, pb = logit_oof(df, "ok100", [a]), logit_oof(df, "ok100", [b])
    auc = lambda p: roc_auc_score(df.ok100, p)
    obs = auc(pb) - auc(pa)
    rng = np.random.default_rng(SEED); ds, dropped = [], 0
    for _ in range(NBOOT):
        s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        qa, qb = logit_oof(s, "ok100", [a]), logit_oof(s, "ok100", [b])
        if qa is None or qb is None or s.ok100.nunique() < 2:
            dropped += 1; continue
        ds.append(roc_auc_score(s.ok100, qb) - roc_auc_score(s.ok100, qa))
    ds = np.array(ds)
    return dict(n=len(df), AUC_A=auc(pa), AUC_B=auc(pb), dAUC=obs, p=float(np.mean((ds - obs) >= obs)), dropped=dropped)


def fmt(d):
    return " ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in d.items())


if __name__ == "__main__":
    bat, pit = attach(bat, "bat"), attach(pit, "pit")
    bat.to_csv("feat_bat.csv", index=False); pit.to_csv("feat_pit.csv", index=False)
    eb, ep = bat[bat.n >= 150].copy(), pit[pit.n >= 150].copy()
    print("entrants bat", len(eb), "pit", len(ep))
    for nm, e in [("bat", eb), ("pit", ep)]:
        print(nm, "MLB PA/BF by arrival year:", e.groupby("year").n.agg(["size", "median"]).to_dict("index"))
        print(nm, "xwOBA fallback share by arrival year:", e.groupby("year").fallback.mean().round(3).to_dict())
    B1, P1 = eb[eb.ok100].reset_index(drop=True), ep[ep.ok100].reset_index(drop=True)
    print("\n== PRIMARY ==")
    h1 = compare(B1, "Y1", "woba", "xwoba"); print("H1 Y1 OPS_rel  ", fmt(h1))
    h2 = compare(P1, "P1", "kbb", "csw"); print("H2 P1 K-BB%    ", fmt(h2))
    ps = sorted([("H1", h1["p_BA"]), ("H2", h2["p_BA"])], key=lambda t: t[1])
    holm = {ps[0][0]: ps[0][1] <= 0.025, ps[1][0]: ps[0][1] <= 0.025 and ps[1][1] <= 0.05}
    print("Holm reject (B<A):", holm, "| floor B<C at .05:", {"H1": h1["p_BC"] <= 0.05, "H2": h2["p_BC"] <= 0.05})
    print("VERDICT (Holm-reject AND beats floor):", {"H1": holm["H1"] and h1["p_BC"] <= 0.05, "H2": holm["H2"] and h2["p_BC"] <= 0.05})
    print("note: every bootstrap reuses seed", SEED, "(Holm is valid under any dependence)")
    print("\n== SECONDARY ==")
    for y, a, b in [("Y2", "k", "whiff"), ("Y3", "bb", "chase"), ("Y4", "hr", "brl")]:
        print(y, fmt(compare(B1, y, a, b)))
    for y, a, b in [("P2", "fipn", "xwoba"), ("P3", "hr", "brl")]:
        print(y, fmt(compare(P1, y, a, b)))
    print("H1 weighted", fmt(compare(B1, "Y1", "woba", "xwoba", wcol="PA")))
    print("H2 weighted", fmt(compare(P1, "P1", "kbb", "csw", wcol="BF")))
    B50, P50 = eb[eb.ok50].reset_index(drop=True), ep[ep.ok50].reset_index(drop=True)
    print("H1 >=50PA", fmt(compare(B50, "Y1", "woba", "xwoba")))
    print("H2 >=15IP", fmt(compare(P50, "P1", "kbb", "csw")))
    P1["start_share"] = P1.start_share.astype(float)
    print("H2 +start: A", round(mae(P1, "P1", ["kbb", "start_share"]), 4), "B", round(mae(P1, "P1", ["csw", "start_share"]), 4))
    print("S1 bat", fmt(s1(eb.reset_index(drop=True), "woba", "xwoba")))
    print("S1 pit", fmt(s1(ep.reset_index(drop=True), "kbb", "csw")))
    # 2020+ window
    b20 = attach(bat[["key_npb", "year", "key_mlbam", "Y1", "ok100", "PA"]].copy(), "bat", 2020)
    p20 = attach(pit[["key_npb", "year", "key_mlbam", "P1", "ok100", "BF"]].copy(), "pit", 2020)
    b20 = b20[(b20.n >= 150) & b20.ok100].reset_index(drop=True); p20 = p20[(p20.n >= 150) & p20.ok100].reset_index(drop=True)
    print(f"2020+ window: bat n={len(b20)} (drops {len(B1)-len(b20)}), pit n={len(p20)} (drops {len(P1)-len(p20)})")
    if b20.year.nunique() > 2:
        print("H1 2020+", fmt(compare(b20, "Y1", "woba", "xwoba")))
    if p20.year.nunique() > 2:
        print("H2 2020+", fmt(compare(p20, "P1", "kbb", "csw")))
