"""How many linked NPB arrivals gain usable pre-NPB tracking data once AAA Statcast is added?

For each linked first-season player with npb_year in 2024..2025, fetch that player's AAA
pitch-level Statcast for season npb_year-1 (AAA is complete from 2023). Saves raw CSVs to
aaa/<kind>_<mlbam>_<season>.csv (skips existing), 1 request per 2 seconds, then compares
"MLB-only >=150 PA" with "MLB+AAA >=150 PA" coverage.
"""
import os, time, urllib.request
import pandas as pd

BASE = "https://baseballsavant.mlb.com/statcast-search-minors/csv"
HF = "https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
os.makedirs("aaa", exist_ok=True)
links = pd.read_csv("links.csv")
links = links[links.year.between(2024, 2025)]

def fetch(kind, pid, season):
    out = f"aaa/{kind}_{pid}_{season}.csv"
    if not os.path.exists(out):
        role = "batters_lookup%5B%5D" if kind == "bat" else "pitchers_lookup%5B%5D"
        ptype = "batter" if kind == "bat" else "pitcher"
        q = (f"?all=true&type=details&minors=true&hfLevel=AAA%7C&hfSea={season}%7C"
             f"&player_type={ptype}&{role}={pid}")
        req = urllib.request.Request(BASE + q, headers={"User-Agent": "python-requests/2.32"})
        open(out, "wb").write(urllib.request.urlopen(req, timeout=90).read())
        time.sleep(2.0)
    d = pd.read_csv(out, low_memory=False)
    col = "batter" if kind == "bat" else "pitcher"
    d = d[d[col] == pid]  # the lookup must return only this player
    return d[d.events.notna()].shape[0]  # plate appearances (batter) / batters faced (pitcher)

for kind, tbl, thr_col, thr in [("bat", "sc_batter_expected", "PA", 100), ("pit", "sc_pitcher_expected", "IP", 30)]:
    mlb = pd.read_parquet(HF + tbl + ".parquet")[["player_id", "year", "pa"]]
    L = links[links.kind == kind].copy()
    rows = []
    for _, r in L.iterrows():
        pid = int(r.key_mlbam)
        m = mlb[(mlb.player_id == pid) & (mlb.year < r.year)].pa.sum()
        a = fetch(kind, pid, int(r.year) - 1)
        rows.append((r.player, int(r.year), r[thr_col], m, a))
    t = pd.DataFrame(rows, columns=["player", "npb_year", thr_col, "mlb_pa", "aaa_pa_prev"])
    ok_npb = t[thr_col] >= thr
    print(f"{kind}: linked 2024-25 arrivals {len(t)} | NPB {thr_col}>={thr}: {ok_npb.sum()}")
    print(f"   MLB-only >=150: {((t.mlb_pa >= 150) & ok_npb).sum()} | "
          f"MLB>=150 or AAA(prev yr)>=150: {(((t.mlb_pa >= 150) | (t.aaa_pa_prev >= 150)) & ok_npb).sum()}")
    t.to_csv(f"aaa_size_{kind}.csv", index=False)
