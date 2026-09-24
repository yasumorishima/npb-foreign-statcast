import re,os,time,glob,urllib.request,unicodedata,pandas as pd
UA={"User-Agent":"python-requests/2.32 (research; contact via github.com/yasumorishima)"}
d=pd.read_csv("r26_first.csv",dtype={"key_npb":str}); a=d[d.first_year==2026]
ch=pd.concat([pd.read_csv(f,dtype=str,usecols=lambda c:c in ("key_npb","key_mlbam","name_first","name_last")) for f in glob.glob(os.path.expanduser("~/claude-scratch/npbid/people-*.csv"))])
m=a.merge(ch[ch.key_npb.notna()],on="key_npb",how="left")
def fold(s): return unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower()
rows=[]
for x in m.itertuples():
    f=f"eng26/{x.key_npb}.html"
    if not os.path.exists(f):
        for k in range(3):
            try: open(f,"wb").write(urllib.request.urlopen(urllib.request.Request(f"https://npb.jp/bis/eng/players/{x.key_npb}.html",headers=UA),timeout=20).read()); break
            except Exception as e: time.sleep(10)
        time.sleep(2)
    t=open(f,encoding="utf-8",errors="ignore").read() if os.path.exists(f) else ""
    en=re.search(r"<title>([^|<(]+)",t); en=en.group(1).strip() if en else ""
    ok=fold(x.name_last) in fold(en) if isinstance(x.name_last,str) else None
    rows.append((x.team,x.key_npb,x.name,en,x.name_first,x.name_last,x.key_mlbam,ok))
r=pd.DataFrame(rows,columns=["team","key_npb","name","npb_en","name_first","name_last","key_mlbam","last_match"])
r.to_csv("r26_links.csv",index=False); print(r.last_match.value_counts(dropna=False).to_dict())
print(r[r.last_match!=True].to_string())
