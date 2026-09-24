"""Layer 2 step 1: per-player season sums from league-wide daily AAA/MLB files (PREREG_layer2.md md5 8a7305c9…).

usage: python l2_agg.py <season>
Writes l2/agg_<level>_<season>_<role>.parquet with one row per (player, team) and numerator/denominator sums,
and l2/start_<level>_<season>.parquet (pitcher games / starts / first date).
Gates (all asserted):
  G1 the sums reproduce ana1.mlb_features exactly on per-player MLB files for this season;
  G2 league-wide MLB sums equal the per-player-file sums for every Pillar-1/2026 player-season in this season
     (so the league-wide fetch has no missing day for them).
No NPB outcome is used (importing ana1 loads the NPB tables, which this script does not touch).
"""
import glob, os, sys
import numpy as np, pandas as pd
import ana1
from ana1 import PA_EVENTS, EXCL_EVENTS, SWSTR, SWING_EXTRA, PITCH_EXCL, DEFAULTS

assert ana1.hashlib.md5(open("PREREG_layer2.md", "rb").read()).hexdigest() == "8a7305c938eb50d04d319add64746ebe"
S = ["pa", "wv", "xwv", "k", "bb", "hbp", "hr", "brl", "np", "swstr", "swings", "ooz", "oozsw", "csw"]


def prep(d):
    d = d[d.game_type == "R"].copy()
    ev = d.events
    unknown = set(ev.dropna()) - PA_EVENTS - EXCL_EVENTS
    assert not unknown, unknown
    ispa = ev.isin(PA_EVENTS)
    assert not d.loc[ispa, "woba_value"].isna().any()
    ls, la = d.launch_speed, d.launch_angle
    dflt = pd.Series([(a, b) in DEFAULTS for a, b in zip(ls.round(1), la.round(1))], index=d.index, dtype=bool)
    valid = ls.notna() & la.notna() & ~dflt
    bbe = d.type == "X"
    usex = ispa & bbe & valid & d.estimated_woba_using_speedangle.notna()
    d["pa"] = ispa.astype(int)
    d["wv"] = np.where(ispa, d.woba_value.astype(float), 0.0)
    d["xwv"] = np.where(usex, d.estimated_woba_using_speedangle.astype(float), d.wv)
    d["k"] = (ispa & ev.isin({"strikeout", "strikeout_double_play"})).astype(int)
    d["bb"] = (ispa & (ev == "walk")).astype(int)
    d["hbp"] = (ispa & (ev == "hit_by_pitch")).astype(int)
    d["hr"] = (ispa & (ev == "home_run")).astype(int)
    d["brl"] = (ispa & bbe & valid & (d.launch_speed_angle == 6)).astype(int)
    desc = d.description
    ne = ~desc.isin(PITCH_EXCL)
    sw = desc.isin(SWSTR)
    swing = sw | desc.isin(SWING_EXTRA) | desc.str.startswith("hit_into_play")
    ooz = d.zone.isin([11, 12, 13, 14])
    d["np"] = ne.astype(int)
    d["swstr"] = (ne & sw).astype(int)
    d["swings"] = (ne & swing).astype(int)
    d["ooz"] = (ne & ooz).astype(int)
    d["oozsw"] = (ne & ooz & swing).astype(int)
    d["csw"] = (ne & (sw | (desc == "called_strike"))).astype(int)
    top = d.inning_topbot == "Top"
    d["bat_team"] = np.where(top, d.away_team, d.home_team)
    d["pit_team"] = np.where(top, d.home_team, d.away_team)
    return d


def rates(t):
    pa = t.pa
    return pd.DataFrame(dict(n=pa, woba=t.wv / pa, xwoba=t.xwv / pa, k=t.k / pa, bb=t.bb / pa, hr=t.hr / pa,
                             brl=t.brl / pa, kbb=(t.k - t.bb) / pa, fipn=(13 * t.hr + 3 * (t.bb + t.hbp) - 2 * t.k) / pa,
                             whiff=t.swstr / t.swings, chase=t.oozsw / t.ooz, csw=t.csw / t.np), index=t.index)


def starts(d):
    g = d.sort_values(["game_pk", "at_bat_number", "pitch_number"]).groupby(["pitcher", "game_pk"]).head(1)
    st = ((g.inning == 1) & (g.outs_when_up == 0) & g.on_1b.isna() & g.on_2b.isna() & g.on_3b.isna()
          & (g.pitch_number == 1))
    return pd.DataFrame(dict(pitcher=g.pitcher, games=1, starts=st.astype(int), date=g.game_date))


if __name__ == "__main__":
    season = int(sys.argv[1])
    os.makedirs("l2", exist_ok=True)
    # G1: exact reproduction of ana1.mlb_features on single-season per-player files
    files = sorted(glob.glob(f"mlb/*_{season}.csv"))
    assert files, "no per-player files for this season"
    ref = {}
    for f in files:
        kind, pid = os.path.basename(f).split("_")[:2]; pid = int(pid)
        a = ana1.mlb_features(kind, pid, season + 1, min_season=season)
        assert a is not None, f
        d = prep(pd.read_csv(f, low_memory=False))
        s = d[S].sum()
        r = rates(s.to_frame().T).iloc[0]
        for c in ["n", "woba", "xwoba", "k", "bb", "hr", "brl", "kbb", "fipn", "whiff", "chase", "csw"]:
            assert np.isclose(r[c], a[c], rtol=0, atol=1e-12, equal_nan=True), (f, c, r[c], a[c])
        if kind == "pit":
            st = starts(d)
            assert np.isclose(st.starts.sum() / st.games.sum(), a["start_share"], rtol=0, atol=1e-12), (f, "start_share")
        ref[(kind, pid)] = s
    print(f"G1 ok: {len(files)} per-player files reproduce ana1.mlb_features (incl. start_share) exactly", flush=True)
    # completeness of the daily league-wide fetch (Amendment 1 §2)
    log = open("fetch_lg.log").read()
    assert "FAIL" not in log, "fetch_lg reported FAIL"
    assert f"season done {season}" in log, "season not finished"
    import datetime as dt
    day = dt.date(season, 3, 15)
    while day <= dt.date(season, 10, 5):
        for lv in ("aaa", "mlb"):
            assert os.path.exists(f"aaa_lg/{lv}_{day}.csv.gz") or os.path.exists(f"aaa_lg/{lv}_{day}.none"), (lv, day)
        day += dt.timedelta(days=1)
    print("completeness: every date has a file or an empty-day marker", flush=True)
    # league-wide aggregation, streamed by day
    for level in ("aaa", "mlb"):
        days = sorted(glob.glob(f"aaa_lg/{level}_{season}-*.csv.gz"))
        acc = {"bat": [], "pit": []}; stp = []; bfd = []; slim = []; pks = set()
        for f in days:
            d = prep(pd.read_csv(f, low_memory=False))
            pks |= set(d.game_pk.unique())
            acc["bat"].append(d.groupby(["batter", "bat_team"])[S].sum())
            acc["pit"].append(d.groupby(["pitcher", "pit_team"])[S].sum())
            stp.append(starts(d))
            bfd.append(d.groupby("batter").game_date.min())
            if level == "aaa":  # slim pitch rows for the split-half reliability secondary
                slim.append(d[["batter", "pitcher", "game_date", "game_pk", "at_bat_number", "pitch_number"] + S]
                            .astype({c: "int16" for c in S if c not in ("wv", "xwv")}))
        # game_pk set vs the statsapi schedule of completed regular-season games (Amendment 1 §2)
        import json, urllib.request
        sid = 11 if level == "aaa" else 1
        u = (f"https://statsapi.mlb.com/api/v1/schedule?sportId={sid}&season={season}&gameType=R"
             f"&startDate={season}-03-15&endDate={season}-10-05")
        sch = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "python-requests/2.32"}), timeout=60))
        final = {g["gamePk"] for dd in sch["dates"] for g in dd["games"] if g["status"]["codedGameState"] == "F"}
        miss, extra = final - pks, pks - final
        print(f"{level} {season}: schedule final {len(final)} | fetched {len(pks)} | missing {len(miss)} | extra {len(extra)}"
              f" | missing ids {sorted(miss)[:20]}", flush=True)
        if level == "mlb":
            assert not miss, "MLB games missing from the league-wide fetch"
        else:
            assert len(miss) <= 0.01 * len(final), "more than 1% of AAA games missing"
        for role, key in (("bat", "batter"), ("pit", "pitcher")):
            t = pd.concat(acc[role]).groupby(level=[0, 1]).sum()
            t.index.names = ["player", "team"]
            t.reset_index().to_parquet(f"l2/agg_{level}_{season}_{role}.parquet")
            if level == "mlb":  # G2
                tot = t.groupby(level=0).sum()
                missing = [(k, p) for (k, p) in ref if k == role and p not in tot.index]
                bad = [(k, p) for (k, p), s in ref.items() if k == role and p in tot.index and not np.allclose(
                    tot.loc[p, S].values.astype(float), s[S].values.astype(float), rtol=0, atol=1e-9)]
                assert not missing and not bad, (role, missing[:5], bad[:5])
                print(f"G2 ok: {level} {role} league-wide sums equal per-player files for "
                      f"{sum(1 for k, _ in ref if k == role)} players", flush=True)
            else:  # G3: league-wide AAA sums == per-player AAA files (game_type R only)
                tot = t.groupby(level=0).sum(); n3 = e3 = 0
                for f in glob.glob(f"aaa/{role}_*_{season}.csv"):
                    pid = int(os.path.basename(f).split("_")[1])
                    d3 = prep(pd.read_csv(f, low_memory=False))
                    if d3.empty:  # header-only: the player had no AAA regular-season pitch; league-wide must agree
                        assert pid not in tot.index, (f, "G3 empty file but player present league-wide")
                        e3 += 1; continue
                    s3 = d3[S].sum()
                    assert pid in tot.index and np.allclose(tot.loc[pid, S].values.astype(float),
                                                            s3.values.astype(float), rtol=0, atol=1e-9), (f, "G3")
                    n3 += 1
                print(f"G3 ok: aaa {role}: {n3} non-empty per-player files equal league-wide sums; "
                      f"{e3} empty files absent league-wide", flush=True)
        sp = pd.concat(stp)
        sp.groupby("pitcher").agg(games=("games", "sum"), starts=("starts", "sum"), first=("date", "min")) \
          .to_parquet(f"l2/start_{level}_{season}.parquet")
        if slim:
            pd.concat(slim, ignore_index=True).to_parquet(f"l2/slim_aaa_{season}.parquet")
        pd.concat(bfd).groupby(level=0).min().rename("first").to_frame() \
          .to_parquet(f"l2/firstbat_{level}_{season}.parquet")
        print(level, season, "days", len(days), "pitches", int(pd.concat(acc["bat"])["np"].sum()), flush=True)
    print("done", flush=True)
