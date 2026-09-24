"""Fetch npb.jp player pages for every Chadwick person that has both key_npb and key_mlbam.

Saves raw HTML to pages/<key_npb>.html (skips ones already saved), 1 request/second.
Parsing is done separately so the fetch is never repeated.
"""
import glob, os, time, urllib.request, urllib.error
import pandas as pd

cols = ("key_npb", "key_mlbam")
d = pd.concat([pd.read_csv(f, dtype=str, usecols=lambda c: c in cols)
               for f in sorted(glob.glob(os.path.expanduser("~/claude-scratch/npbid/people-*.csv")))])
ids = sorted(d[d.key_npb.notna() & d.key_mlbam.notna()].key_npb.unique())
os.makedirs("pages", exist_ok=True)
print("targets", len(ids), flush=True)
ok = miss = err = 0
for i, k in enumerate(ids):
    out = f"pages/{k}.html"
    if os.path.exists(out):
        continue
    try:
        req = urllib.request.Request(f"https://npb.jp/bis/players/{k}.html",
                                     headers={"User-Agent": "python-requests/2.32 (research; contact via github.com/yasumorishima)"})
        body = urllib.request.urlopen(req, timeout=20).read()
        open(out, "wb").write(body)
        ok += 1
    except urllib.error.HTTPError as e:
        open(f"pages/{k}.http{e.code}", "w").close()
        miss += 1
    except Exception as e:
        err += 1
        print("ERR", k, e, flush=True)
    if i % 100 == 0:
        print(i, ok, miss, err, flush=True)
    time.sleep(1.0)
print("done", ok, miss, err, flush=True)
