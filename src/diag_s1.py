import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score
for k in ["bat","pit"]:
    f=pd.read_csv(f"feat_{k}.csv"); e=f[f.n>=150].reset_index(drop=True)
    pred=np.array([e.ok100[e.year!=y].mean() for y in e.year])  # intercept-only, leave-one-year-out
    print(k,"n",len(e),"intercept-only pooled OOF AUC",round(roc_auc_score(e.ok100,pred),4))
    print("  reached-cut rate by year",e.groupby("year").ok100.mean().round(2).to_dict())
