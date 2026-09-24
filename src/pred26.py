"""PREREG_pillar1.md §7: fit every model on the 2016–2025 primary sample and freeze predictions for 2026 arrivals.

Reads no 2026 NPB statistic. 2026 arrivals = npb.jp roster players whose first NPB season on their
npb.jp page is 2026 (r26_links.csv, role from the roster position section), linked to MLBAM via Chadwick
(surname checked against the npb.jp English page for all 37). Entry: >=150 pitch-level MLB PA/BF (2015–2025).
Writes pred26_bat.csv, pred26_pit.csv, pred26_coef.csv; their md5s are recorded before any 2026 stat is read.
"""
import os
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
import ana1  # runs the frozen-file md5 check and the 2016–2025 completeness gate

assert open("fetch_mlb26b.log").read().strip().splitlines()[-1] == "done", "2026 fetch not finished"
HF = "https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
r = pd.read_csv("r26_links.csv", dtype={"key_npb": str}).dropna(subset=["key_mlbam"])
r["key_mlbam"] = r.key_mlbam.astype(int)
miss = []
for k, t, c in [("bat", "statsapi_batting", "plateAppearances"), ("pit", "statsapi_pitching", "battersFaced")]:
    m = pd.read_parquet(HF + t + ".parquet", columns=["player_id", "season", c])
    for x in r[r.kind == k].itertuples():
        s = m[(m.player_id == x.key_mlbam) & (m.season >= 2015) & (m.season < 2026) & (m[c] > 0)]
        if s[c].sum() >= 100:
            miss += [y for y in s.season.unique() if not os.path.exists(f"mlb/{k}_{x.key_mlbam}_{y}.csv")]
assert not miss, miss

fb, fp = pd.read_csv("feat_bat.csv"), pd.read_csv("feat_pit.csv")
TR = {"bat": fb[(fb.n >= 150) & fb.ok100], "pit": fp[(fp.n >= 150) & fp.ok100]}
ENT = {"bat": fb[fb.n >= 150], "pit": fp[fp.n >= 150]}
assert len(TR["bat"]) == 49 and len(TR["pit"]) == 63
SPEC = {"bat": [("Y1", "woba", "xwoba"), ("Y2", "k", "whiff"), ("Y3", "bb", "chase"), ("Y4", "hr", "brl")],
        "pit": [("P1", "kbb", "csw"), ("P2", "fipn", "xwoba"), ("P3", "hr", "brl")]}
S1 = {"bat": ("woba", "xwoba"), "pit": ("kbb", "csw")}

coef = []
for kind in ("bat", "pit"):
    new = r[r.kind == kind].copy()
    feats = [ana1.mlb_features(kind, int(x.key_mlbam), 2026) for x in new.itertuples()]
    new = new.join(pd.DataFrame([f if f else {} for f in feats], index=new.index))
    print(kind, "2026 arrivals", len(new), "| below 150 MLB PA/BF (not entrants):",
          new[~(new.n >= 150)].npb_en.str.split("（").str[0].tolist())
    new = new[new.n >= 150].copy()
    tr = TR[kind]
    for y, a, b in SPEC[kind]:
        new[f"{y}_C"] = tr[y].mean(); coef.append((kind, y, "C", tr[y].mean(), np.nan, np.nan))
        for nm, xs in [("A", [a]), ("B", [b]), ("AB", [a, b])]:
            X = np.column_stack([np.ones(len(tr))] + [tr[x].values for x in xs])
            beta = np.linalg.lstsq(X, tr[y].values, rcond=None)[0]
            new[f"{y}_{nm}"] = np.column_stack([np.ones(len(new))] + [new[x].values for x in xs]) @ beta
            coef.append((kind, y, nm, *beta, *([np.nan] * (3 - len(beta)))))
    ent = ENT[kind]
    for nm, x in zip(("A", "B"), S1[kind]):
        lr = LogisticRegression(C=np.inf, max_iter=1000).fit(ent[[x]].values, ent.ok100.values)
        new[f"S1_{nm}"] = lr.predict_proba(new[[x]].values)[:, 1]
        coef.append((kind, "S1", nm, lr.intercept_[0], lr.coef_[0][0], np.nan))
    keep = ["team", "key_npb", "name", "npb_en", "key_mlbam", "pos", "n"] + [c for c in new.columns if c[:2] in ("Y1", "Y2", "Y3", "Y4", "P1", "P2", "P3", "S1")]
    new[keep].to_csv(f"pred26_{kind}.csv", index=False)
    print(new[["npb_en", "n"] + [c for c in new.columns if c.startswith(("Y1_", "P1_"))]].round(4).to_string())
pd.DataFrame(coef, columns=["kind", "outcome", "model", "b0", "b1", "b2"]).to_csv("pred26_coef.csv", index=False)
print("written")
