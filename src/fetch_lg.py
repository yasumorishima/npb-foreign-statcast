"""League-wide regular-season pitch-level Statcast by day, AAA and MLB, seasons 2023-2025.
Saves aaa_lg/<level>_<date>.csv.gz (empty days saved as 0-byte marker .none). 1 request / 4 s, 3 retries.
Used only to estimate AAA->MLB translation factors from same-player same-season pairs (no NPB data)."""
import os, time, gzip, datetime as dt, urllib.request
URL = {"aaa": "https://baseballsavant.mlb.com/statcast-search-minors/csv?all=true&type=details&minors=true&hfLevel=AAA%7C",
       "mlb": "https://baseballsavant.mlb.com/statcast_search/csv?all=true&type=details"}
for season in (2023, 2024, 2025):
    d = dt.date(season, 3, 15)
    while d <= dt.date(season, 10, 5):
        for lv in ("aaa", "mlb"):
            out = f"aaa_lg/{lv}_{d}.csv.gz"
            if os.path.exists(out) or os.path.exists(out[:-7] + ".none"):
                continue
            q = f"{URL[lv]}&hfSea={season}%7C&hfGT=R%7C&game_date_gt={d}&game_date_lt={d}&player_type=batter"
            for a in range(3):
                try:
                    b = urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "python-requests/2.32"}), timeout=180).read()
                    break
                except Exception as e:
                    print("retry", lv, d, e, flush=True); time.sleep(30); b = None
            if b is None:
                print("FAIL", lv, d, flush=True)
            elif b.count(b"\n") <= 1:
                open(out[:-7] + ".none", "w").close()
            else:
                assert b.count(b"\n") < 24000, (lv, d, "near row cap")
                with gzip.open(out + ".tmp", "wb") as f: f.write(b)
                os.replace(out + ".tmp", out)
            time.sleep(4)
        d += dt.timedelta(days=1)
    print("season done", season, flush=True)
print("done", flush=True)
