"""Descriptive interim look at the frozen 2026 predictions using in-season npb.jp stats (not a registered test).

Checks the md5 of every frozen prediction file first. Outcomes follow PREREG_pillar1 §3 using npb.jp team pages
(r26live/, fetched mid-season): OPS_rel with OBP = (H+BB+HBP)/(PA−SH), SLG = TB/AB, league = all hitters who do not
appear on that team's pitching page; K−BB% = (SO−BB)/BF. Reports n and MAE only.
"""
import hashlib, re, glob, unicodedata, sys
import numpy as np, pandas as pd

FROZEN = {"pred26_bat.csv": "89dfb2bf5fd8b545718616bc0bd4894e", "pred26_pit.csv": "d08d150e702b4bcd4aaa355c84b0ec5f",
          "l2/pred26L2_bat.csv": "63936907a96361d336fcb8f6403efcd9", "l2/pred26L2_pit.csv": "f568d209176a89921e16bc0fdf23f8e5"}
for f, h in FROZEN.items():
    assert hashlib.md5(open(f, "rb").read()).hexdigest() == h, f


def norm(s):
    s = unicodedata.normalize("NFKC", s).strip().lstrip("*+"); s = re.sub(r"^([A-Za-z]\.)+", "", s)  # * = left, + = switch
    return re.sub(r"[・=\s\.]", "", s)


def rows(path):
    t = open(path, encoding="utf-8").read()
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, flags=re.S):
        cells = [re.sub(r"<[^>]*>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if cells:
            out.append(cells)
    return out


def num(x):
    x = x.replace(",", "")
    return float(x) if x.strip("-") != "" else np.nan if x.startswith("--") else 0.0  # "----" = undefined rate


bat, pit = [], []
for f in glob.glob("r26live/idb1_*.html"):
    team = f.split("_")[1][:-5]
    for c in rows(f):
        if len(c) != 23:
            continue
        name = c[0]
        v = [num(x) for x in c[1:20]]
        bat.append(dict(team=team, nname=norm(name), PA=v[1], AB=v[2], H=v[4], HR=v[7], TB=v[8], SH=v[12],
                        SF=v[13], BB=v[14], HBP=v[16], SO=v[17], slg_pub=num(c[21]), obp_pub=num(c[22])))
for f in glob.glob("r26live/idp1_*.html"):
    team = f.split("_")[1][:-5]
    for c in rows(f):
        if len(c) != 24:
            continue
        name = c[0]
        ip = c[12]  # "53.1" = 53 1/3 IP, "53", or "+" (faced batters, no out recorded)
        if ip == "+":
            outs = 0.0
        else:
            w, _, fr = ip.partition(".")
            assert fr in ("", "1", "2"), ip
            outs = 3 * float(w) + (int(fr) if fr else 0)
        rest = c[13:]
        pit.append(dict(team=team, nname=norm(name), BF=num(c[11]), OUTS=outs, HR=num(rest[1]), BB=num(rest[2]),
                        SO=num(rest[5]), ER=num(rest[9]), era_pub=num(rest[10])))
B, P = pd.DataFrame(bat), pd.DataFrame(pit)
assert len(B) > 300 and len(P) > 300, (len(B), len(P))
# parse checks against the rates printed on the page (published OBP uses SF, so compare with the SF formula)
q = B[B.AB >= 50]
assert (abs(q.TB / q.AB - q.slg_pub) < 0.0006).all(), "SLG column mismatch"
assert (abs((q.H + q.BB + q.HBP) / (q.AB + q.BB + q.HBP + q.SF) - q.obp_pub) < 0.0006).all(), "OBP column mismatch"
r = P[(P.OUTS >= 30) & P.era_pub.notna()]
assert (abs(27 * r.ER / r.OUTS - r.era_pub) < 0.006).all(), "ERA / innings column mismatch"
print(f"parse checks ok: {len(q)} hitters (SLG, OBP) and {len(r)} pitchers (ERA) match the published rates")
# a hitter is treated as a pitcher only if he is on the same team's pitching page AND faced at least as many
# batters as his own plate appearances (keeps position players who pitched in blowouts, e.g. 281 PA / 0.2 IP)
bf = dict(zip(zip(P.team, P.nname), P.BF))
H = B[[not ((t, n) in bf and bf[(t, n)] >= pa) for t, n, pa in zip(B.team, B.nname, B.PA)]]
lg_obp = (H.H + H.BB + H.HBP).sum() / (H.PA - H.SH).sum(); lg_slg = H.TB.sum() / H.AB.sum()
lg_ops = lg_obp + lg_slg
lg_era = 27 * P.ER.sum() / P.OUTS.sum()
print(f"league 2026 (to date): OPS {lg_ops:.4f} (non-pitcher hitters {len(H)}), ERA {lg_era:.3f}; pitchers {len(P)}")
B["Y1"] = ((B.H + B.BB + B.HBP) / (B.PA - B.SH) + B.TB / B.AB) / lg_ops
P["P1"] = (P.SO - P.BB) / P.BF


def score(pred, obs, y, models, cut, extra=None):
    d = pred.copy(); d["nname"] = d.name.map(norm)
    d = d.merge(obs, on=["team", "nname"], how="left")
    miss = d[obs.columns[2]].isna().sum()
    assert miss == 0, ("arrival not found on stats pages", d[d[obs.columns[2]].isna()].name.tolist())
    below = int((~cut(d)).sum()); d = d[cut(d)]
    out = {"n": len(d), "below_cut": below}
    for m in models:
        out[m] = float(np.abs(d[y] - d[f"{y}_{m}"]).mean()) if len(d) else np.nan
    return out, d


for label, fb, fp in [("pillar1 (MLB only)", "pred26_bat.csv", "pred26_pit.csv"),
                      ("layer2 (MLB+AAA)", "l2/pred26L2_bat.csv", "l2/pred26L2_pit.csv")]:
    pb, pp = pd.read_csv(fb), pd.read_csv(fp)
    for role, pr, obs, y, cutf in [("bat", pb, B, "Y1", lambda d: d.PA >= 100), ("pit", pp, P, "P1", lambda d: d.OUTS >= 90)]:
        res, d = score(pr, obs, y, ["C", "A", "B"], cutf)
        print(label, role, y, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()})
        if "aaa_only" in d:
            for flag in (True, False):
                sub = d[d.aaa_only == flag]
                print("   aaa_only" if flag else "   mlb≥150 ", role, "n", len(sub),
                      {m: round(float(np.abs(sub[y] - sub[f"{y}_{m}"]).mean()), 4) if len(sub) else None for m in "CAB"})
