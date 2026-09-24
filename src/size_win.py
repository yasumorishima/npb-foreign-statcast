import pandas as pd
HF="https://huggingface.co/datasets/yasumorishima/mlb-stats/resolve/main/"
L=pd.read_csv("links.csv")
L["ok"]=((L.kind=="bat")&(L.PA>=100))|((L.kind=="pit")&(L.IP>=30))
for kind,t in [("bat","statsapi_batting"),("pit","statsapi_pitching")]:
    m=pd.read_parquet(HF+t+".parquet")
    col="plateAppearances" if kind=="bat" else "battersFaced"
    X=L[L.kind==kind]
    for lo in [3,99]:
        n=[]
        for _,r in X.iterrows():
            s=m[(m.player_id==r.key_mlbam)&(m.season<r.year)&(m.season>=r.year-lo)][col].sum(); n.append(s)
        X=X.assign(**{f"w{lo}":n})
    for thr in [150,100]:
        print(kind,"thr",thr,"linked",len(X),"| last3:",(X.w3>=thr).sum(),"(npb-ok",((X.w3>=thr)&X.ok).sum(),") | all2015+:",(X.w99>=thr).sum(),"(npb-ok",((X.w99>=thr)&X.ok).sum(),")")
    print(kind,"by year last3>=150:",X[X.w3>=150].groupby("year").size().to_dict())
