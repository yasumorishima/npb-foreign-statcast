import re, os, time, urllib.request, pandas as pd, glob
UA = {"User-Agent": "python-requests/2.32 (research; contact via github.com/yasumorishima)"}
r = pd.read_csv("r26_roster.csv", dtype=str)
out = []
for x in r.itertuples():
    f = f"pages26/{x.key_npb}.html"
    if not os.path.exists(f):
        for a in range(3):
            try:
                open(f, "wb").write(urllib.request.urlopen(urllib.request.Request(f"https://npb.jp/bis/players/{x.key_npb}.html", headers=UA), timeout=20).read()); break
            except Exception as e:
                print("retry", x.key_npb, e); time.sleep(10)
        time.sleep(2)
    t = open(f, encoding="utf-8", errors="ignore").read()
    yrs = sorted({int(y) for y in re.findall(r"<td class=\"year\">\s*(\d{4})\s*</td>", t)})
    out.append((x.team, x.key_npb, x.name, yrs[0] if yrs else None, len(yrs)))
d = pd.DataFrame(out, columns=["team", "key_npb", "name", "first_year", "n_years"])
d.to_csv("r26_first.csv", index=False)
print(d.first_year.value_counts(dropna=False).sort_index().to_dict())
