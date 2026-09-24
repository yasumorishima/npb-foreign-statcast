"""Fetch MLB regular-season pitch-level Statcast per linked NPB arrival, one file per (role, player, season).

Candidates: linked arrivals (any NPB playing time) with >=100 pooled MLB PA/BF in 2015..(npb_year-1)
per statsapi (a superset of the registered >=150 pitch-level entry rule). Seasons fetched = seasons in
that window where statsapi shows any PA/BF. 1 request per 3 s. Existing files are skipped.
No NPB outcome is read here except the arrival year.
"""
import os, time, urllib.request
import pandas as pd
HF = "https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
BASE = "https://baseballsavant.mlb.com/statcast_search/csv"
L = pd.concat([pd.read_csv("links.csv", usecols=["kind", "key_mlbam", "year"]), pd.read_csv("r26_links.csv", usecols=["kind", "key_mlbam", "year"]).dropna()])
jobs = []
for kind, t, col in [("bat", "statsapi_batting", "plateAppearances"), ("pit", "statsapi_pitching", "battersFaced")]:
    m = pd.read_parquet(HF + t + ".parquet", columns=["player_id", "season", col])
    for _, r in L[L.kind == kind].iterrows():
        s = m[(m.player_id == r.key_mlbam) & (m.season >= 2015) & (m.season < r.year) & (m[col] > 0)]
        if s[col].sum() > 0:
            jobs += [(kind, int(r.key_mlbam), int(y)) for y in sorted(s.season.unique())]
jobs = sorted(set(jobs))
print("jobs", len(jobs), flush=True)
for i, (kind, pid, y) in enumerate(jobs):
    out = f"mlb/{kind}_{pid}_{y}.csv"
    if os.path.exists(out):
        continue
    role = "batters_lookup%5B%5D" if kind == "bat" else "pitchers_lookup%5B%5D"
    pt = "batter" if kind == "bat" else "pitcher"
    q = f"?all=true&type=details&hfGT=R%7C&hfSea={y}%7C&player_type={pt}&{role}={pid}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE + q, headers={"User-Agent": "python-requests/2.32"})
            data = urllib.request.urlopen(req, timeout=120).read()
            open(out + ".tmp", "wb").write(data); os.replace(out + ".tmp", out)
            break
        except Exception as e:
            print("retry", out, e, flush=True); time.sleep(30)
    time.sleep(3.0)
    if i % 25 == 0:
        print(i, out, flush=True)
print("done", flush=True)
