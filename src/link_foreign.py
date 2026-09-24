"""Link NPB first-season foreign players (baseball-data.com names) to MLBAM ids.

Route: Chadwick register (key_npb -> key_mlbam) + npb.jp player pages (key_npb -> registered
name + seasons played). A foreign player is linked when (normalized name, NPB season) matches
exactly one npb.jp page. Prints the link rate and writes links.csv / unlinked.csv.
"""
import glob, os, re, unicodedata
import pandas as pd

def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s = re.sub(r"^([A-Za-z]\.)+", "", s)          # leading initials: "T.オースティン"
    return re.sub(r"[・=\s\.]", "", s)

TEAM = {"読売": "巨人", "北海道日本ハム": "日本ハム", "福岡ソフトバンク": "ソフトバンク", "千葉ロッテ": "ロッテ",
        "埼玉西武": "西武", "東北楽天": "楽天", "広島東洋": "広島", "東京ヤクルト": "ヤクルト", "横浜DeNA": "DeNA"}

def teamnorm(s):
    s = re.sub(r"\s", "", unicodedata.normalize("NFKC", s))
    return TEAM.get(s, s)

# --- npb.jp pages -> (norm name, year) -> key_npb
rows = []
for f in glob.glob("pages/*.html"):
    t = open(f, encoding="utf-8", errors="ignore").read()
    m = re.search(r"<title>([^（<]+)（", t)
    if not m:
        continue
    name = m.group(1)
    pairs = {(int(y), teamnorm(tm)) for y, tm in re.findall(
        r'<td class="year">\s*(\d{4})\s*</td>\s*<td class="team">([^<]*)</td>', t)}
    for y, tm in pairs:
        rows.append((norm(name), y, tm, os.path.basename(f)[:-5], name))
pg = pd.DataFrame(rows, columns=["nname", "year", "team", "key_npb", "npb_name"])

cols = ("key_npb", "key_mlbam", "name_first", "name_last")
ch = pd.concat([pd.read_csv(f, dtype=str, usecols=lambda c: c in cols)
                for f in sorted(glob.glob(os.path.expanduser("~/claude-scratch/npbid/people-*.csv")))])
ch = ch[ch.key_npb.notna() & ch.key_mlbam.notna()].drop_duplicates("key_npb")
pg = pg.merge(ch, on="key_npb")

kat = re.compile(r"^[゠-ヿ・＝ー]+$")
out = []
for f, kind in [("npb_hitters_2015_2025.csv", "bat"), ("npb_pitchers_2015_2025.csv", "pit")]:
    d = pd.read_csv(f, encoding="utf-8-sig")
    d["player"] = d.player.str.strip()
    fr = d[d.player.map(lambda s: bool(kat.match(s)))]
    first = fr.sort_values("year").groupby(["player", "team"]).head(1)
    first = first[first.year >= 2016].copy()
    first["nname"] = first.player.map(norm)
    first["kind"] = kind
    out.append(first)
fs = pd.concat(out)

cand = fs.merge(pg[["nname", "year", "team", "key_npb", "key_mlbam", "npb_name", "name_first", "name_last"]],
                on=["nname", "year", "team"], how="left")
n_cand = cand.groupby(["kind", "player", "team", "year"]).key_npb.nunique()
amb = (n_cand > 1).sum()
linked = cand[cand.key_npb.notna()].groupby(["kind", "player", "team", "year"]).filter(lambda g: g.key_npb.nunique() == 1)
linked = linked.drop_duplicates(["kind", "player", "team", "year"])
# a move between NPB clubs is not a first season: keep only the player's first NPB year (from npb.jp)
first_npb = pg.groupby("key_npb").year.min().rename("npb_first_year")
linked = linked.merge(first_npb, on="key_npb")
moved = linked[linked.year != linked.npb_first_year]
print("dropped as NPB club moves (not first season):", len(moved))
linked = linked[linked.year == linked.npb_first_year]
fs = fs.merge(moved[["kind", "player", "team", "year"]], how="left", indicator=True)
fs = fs[fs._merge == "left_only"].drop(columns="_merge")
key = ["kind", "player", "team", "year"]
unl = fs.merge(linked[key], on=key, how="left", indicator=True)
unl = unl[unl._merge == "left_only"]
for kind, pt, thr in [("bat", "PA", 100), ("pit", "IP", 30)]:
    a = fs[fs.kind == kind]; l = linked[linked.kind == kind]
    print(f"{kind}: first-season {len(a)} linked {len(l)} ({len(l)/len(a):.1%}) | "
          f"{pt}>={thr}: {(a[pt]>=thr).sum()} linked {(l[pt]>=thr).sum()} ({(l[pt]>=thr).sum()/(a[pt]>=thr).sum():.1%})")
print("ambiguous (name+year+team hits >1 page):", amb)
print("pages parsed:", pg.key_npb.nunique())
linked.to_csv("links.csv", index=False)
unl.drop(columns="_merge").to_csv("unlinked.csv", index=False)
print("unlinked sample:", unl[unl.PA.fillna(0).ge(100) | unl.IP.fillna(0).ge(30)].player.head(25).tolist())
