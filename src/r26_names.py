import re, glob, unicodedata, pandas as pd
kat = re.compile(r"^[゠-ヿ・＝ー．\s　A-Za-zＡ-Ｚ\.]+$")
def norm(s):
    s = unicodedata.normalize("NFKC", s).strip(); s = re.sub(r"^([A-Za-z]\.)+", "", s); return re.sub(r"[・=\s\.]", "", s)
ros = []
for f in glob.glob("r26/rst_*.html"):
    t = open(f, encoding="utf-8").read(); team = f.split("_")[1][:-5]
    for pid, nm in re.findall(r"bis/players/(\d+)\.html\">([^<]*)", t):
        if kat.match(nm) and re.search(r"[゠-ヿ]", nm): ros.append((team, pid, nm, norm(nm)))
ros = pd.DataFrame(ros, columns=["team", "key_npb", "name", "nname"]).drop_duplicates()
st = []
for f in glob.glob("r26/id[bp]1_*.html"):
    t = open(f, encoding="utf-8").read(); team = f.split("_")[1][:-5]; kind = "bat" if "idb1" in f else "pit"
    for nm in re.findall(r"<tr>\s*<td[^>]*>(?:<sup>[^<]*</sup>)?([^<]*)</td>", t):
        if kat.match(nm) and re.search(r"[゠-ヿ]", nm): st.append((team, kind, nm, norm(nm)))
st = pd.DataFrame(st, columns=["team", "kind", "name", "nname"]).drop_duplicates()
print("roster katakana", len(ros), "| played katakana", st[["team","nname"]].drop_duplicates().shape[0])
m = st.merge(ros[["team","nname","key_npb"]], on=["team","nname"], how="left")
print("played but not on roster:", m[m.key_npb.isna()][["team","kind","name"]].values.tolist())
ros.to_csv("r26_roster.csv", index=False); st.to_csv("r26_played.csv", index=False)
