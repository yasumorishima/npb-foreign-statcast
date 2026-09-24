"""Pillar 1 S1 replacement exactly as frozen in PREREG_pillar1_S1v2.md (md5 f9754643bbd42af806af25b125c3c58c).

Reads feat_bat.csv / feat_pit.csv written by ana1.py (same working directory) and prints the within-year AUC
of the leave-one-arrival-year-out logistic predictions, its centred player bootstrap, and the sensitivities.
"""
import hashlib, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning

assert hashlib.md5(open("PREREG_pillar1_S1v2.md", "rb").read()).hexdigest() == "f9754643bbd42af806af25b125c3c58c"
SEED, NBOOT = 20260924, 2000
S1 = {"bat": ("woba", "xwoba"), "pit": ("kbb", "csw")}
EXPECT_N = {"bat": 64, "pit": 96}


# copied verbatim from ana1.py
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


def fe_oof(df, y, x):
    """Sens-b: ok ~ x + arrival-year dummies on the training fold; held-out year scored by slope * x."""
    score = np.full(len(df), np.nan)
    yrs = df.year.values
    nwarn = 0
    for fy in np.unique(yrs):
        tr, te = yrs != fy, yrs == fy
        d = pd.get_dummies(df.year[tr], drop_first=True, dtype=float)
        X = np.column_stack([df[x].values[tr], d.values])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", ConvergenceWarning)
            m = LogisticRegression(penalty=None, max_iter=1000).fit(X, df[y].values[tr])
        nwarn += sum(issubclass(i.category, ConvergenceWarning) for i in w)
        score[te] = m.coef_[0][0] * df[x].values[te]
    return score, nwarn


def auc_w(df, y, p):
    """Within-year AUC (PREREG §2): concordant pairs within arrival year / within-year pairs; ties count 1/2."""
    num = den = 0.0
    years, per_year = 0, []
    for _, g in pd.DataFrame({"yr": df.year.values, "y": df[y].values.astype(bool), "p": p}).groupby("yr"):
        pos, neg = g.p[g.y].values, g.p[~g.y].values
        if len(pos) == 0 or len(neg) == 0:
            continue
        c = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
        num += c; den += len(pos) * len(neg); years += 1; per_year.append(c / (len(pos) * len(neg)))
    if den == 0:
        return None
    return dict(auc=num / den, years=years, pairs=int(den), mean_year=float(np.mean(per_year)))


def run(df, a, b, y="ok100", boot=True):
    pa, pb = logit_oof(df, y, [a]), logit_oof(df, y, [b])
    assert pa is not None and pb is not None and np.isfinite(pa).all() and np.isfinite(pb).all()
    ra, rb = auc_w(df, y, pa), auc_w(df, y, pb)
    res = dict(n=len(df), n_reached=int(df[y].sum()), years=rb["years"], pairs=rb["pairs"],
               AUCw_A=ra["auc"], AUCw_B=rb["auc"], dAUCw=rb["auc"] - ra["auc"],
               meanyr_A=ra["mean_year"], meanyr_B=rb["mean_year"])
    if not boot:
        return res
    rng = np.random.default_rng(SEED)
    d_, fa, fb, dropped = [], [], [], 0
    for _ in range(NBOOT):
        s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        qa, qb = logit_oof(s, y, [a]), logit_oof(s, y, [b])
        if qa is None or qb is None:
            dropped += 1; continue
        sa, sb = auc_w(s, y, qa), auc_w(s, y, qb)
        if sa is None or sb is None:
            dropped += 1; continue
        d_.append(sb["auc"] - sa["auc"]); fa.append(sa["auc"] - 0.5); fb.append(sb["auc"] - 0.5)
    d_, fa, fb = map(np.array, (d_, fa, fb))
    oa, ob = res["AUCw_A"] - 0.5, res["AUCw_B"] - 0.5
    res["p_BA"] = float(np.mean((d_ - res["dAUCw"]) >= res["dAUCw"]))
    res["p_A_floor"] = float(np.mean((fa - oa) >= oa))
    res["p_B_floor"] = float(np.mean((fb - ob) >= ob))
    res["dropped"] = dropped
    res["B_better (p_BA<=.05 and p_B_floor<=.05)"] = res["p_BA"] <= 0.05 and res["p_B_floor"] <= 0.05
    return res


def fmt(d):
    return " ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in d.items())


if __name__ == "__main__":
    for kind in ["bat", "pit"]:
        f = pd.read_csv(f"feat_{kind}.csv")
        e = f[f.n >= 150].reset_index(drop=True)
        assert len(e) == EXPECT_N[kind], (kind, len(e))
        for c in ["ok100", "ok50"]:
            assert e[c].dtype == bool, (c, e[c].dtype)
        a, b = S1[kind]
        assert e[[a, b]].notna().all().all()
        print(f"== S1v2 {kind} (secondary) ==")
        print("primary  ", fmt(run(e, a, b)))
        # Sens-a is meanyr_A / meanyr_B above
        sa, wa = fe_oof(e, "ok100", a); sb, wb = fe_oof(e, "ok100", b)
        print(f"Sens-b FE AUCw_A={auc_w(e, 'ok100', sa)['auc']:.4f} AUCw_B={auc_w(e, 'ok100', sb)['auc']:.4f}"
              f" convergence_warnings A={wa} B={wb}")
        print("Sens-c ok50", fmt(run(e, a, b, y="ok50", boot=False)))
        # sanity: intercept-only must be exactly 0.5 by construction
        const = np.array([e.ok100[e.year != yr].mean() for yr in e.year])
        print("check intercept-only AUCw =", auc_w(e, "ok100", const)["auc"])
