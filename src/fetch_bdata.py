"""Fetch NPB 2015-2025 season lines from baseball-data.com team pages -> npb_hitters_2015_2025.csv / npb_pitchers_2015_2025.csv.

Written 2026-09-25 in cloud to rebuild the input of link_foreign.py / ana1.py (the original fetcher was not committed).
One page per (year, team, role) with the "all players" filter, 1 request per 2 s; raw HTML kept in bdata/.
Rows whose stat cells are "-" (on the roster, did not play) are dropped. Mid-season trades give one row per team.
The tables are not committed (baseball-data.com: credit required, no redistribution).
"""
import os, re, time, urllib.request
import pandas as pd

TEAMS = {"t": "阪神", "yb": "DeNA", "g": "巨人", "d": "中日", "c": "広島", "s": "ヤクルト",
         "h": "ソフトバンク", "f": "日本ハム", "bs": "オリックス", "e": "楽天", "l": "西武", "m": "ロッテ"}
HCOLS = ["number", "player", "AVG", "G", "PA", "AB", "H", "HR", "RBI", "SB", "BB", "HBP", "SO", "SH", "GDP",
         "OBP", "SLG", "OPS", "RC27", "XR27"]
PCOLS = ["number", "player", "ERA", "G", "W", "L", "SV", "HLD", "WPCT", "BF", "IP", "H", "HRA", "BB", "HBP", "SO",
         "R", "ER", "WHIP", "DIPS"]
URL = {"bat": "https://baseball-data.com/{yy}/stats/hitter-{t}/tpa-1.html",
       "pit": "https://baseball-data.com/{yy}/stats/pitcher-{t}/"}
HEAD = {"bat": "打<br />席<br />数", "pit": "投<br />球<br />回"}


def get(url, out):
    if not os.path.exists(out):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; github.com/yasumorishima)"})
        open(out, "wb").write(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(2)
    return open(out, encoding="utf-8").read()


def rows(html, ncol, kind):
    assert HEAD[kind] in html
    body = html[html.index("<tbody>"):html.index("</tbody>")]
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        assert len(cells) == ncol, (len(cells), cells[:3])
        if cells[3] == "-":
            assert set(cells[2:]) == {"-"}, cells
            continue
        out.append(cells)
    return out


os.makedirs("bdata", exist_ok=True)
for kind, cols, fn in [("bat", HCOLS, "npb_hitters_2015_2025.csv"), ("pit", PCOLS, "npb_pitchers_2015_2025.csv")]:
    recs = []
    for year in range(2015, 2026):
        for t, team in TEAMS.items():
            html = get(URL[kind].format(yy=year % 100, t=t), f"bdata/{kind}_{year}_{t}.html")
            assert f"{year}年" in html
            for c in rows(html, len(cols), kind):
                recs.append(dict(zip(cols, c), year=year, team=team))
    d = pd.DataFrame(recs)
    d.to_csv(fn, index=False, encoding="utf-8-sig")
    d = pd.read_csv(fn, encoding="utf-8-sig")
    print(fn, len(d), "rows; per year:", d.groupby("year").size().to_dict())
    print("  duplicate (player, year) rows:", int(d.duplicated(["player", "year"], keep=False).sum()),
          "| duplicate (player, team, year):", int(d.duplicated(["player", "team", "year"]).sum()))
