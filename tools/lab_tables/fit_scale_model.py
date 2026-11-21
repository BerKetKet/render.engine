import json,sys,os,re,numpy as np
sys.path.insert(0,os.path.abspath("."))
from kindle_render.config import Config
from kindle_render.fonts import Family
TH={"Standard":2880,"Compact":2496,"Large":3200}
rows=[]
for th,sz in TH.items():
    cfg=Config(); cfg.size26=sz; fam=Family(cfg); reg=fam.face(False,False,sz); bld=fam.face(True,False,sz)
    W=lambda f,s: sum(a for _,a in f.shape(s))/64.0
    logs=[json.loads(l) for l in open(f"tools/lab_tables/work/log_{th}.jsonl")]
    meas={m['k']:m for m in json.load(open(f"tools/lab_tables/work/meas_{th}.json"))}
    for k,e in enumerate(logs):
        m=meas.get(k,{})
        if m.get('s_dev') is None or m.get('peak',0)<250: continue
        mx={};mn={}
        for ri,ci,t,h,cs,rs in e['cells']:
            if cs!=1: continue
            f=bld if h else reg
            mx[ci]=max(mx.get(ci,0),W(f,t))
            pcs=[]
            for w in t.split(): pcs+=re.findall(r"[^-/]+[-/]?|[-/]",w) or [w]
            mn[ci]=max(mn.get(ci,0),(max([W(f,p) for p in pcs] or [0]) if h else 0))
        rows.append(dict(th=th,k=k,n=e['ncols'],spans=e['spans'],avail=e['avail_w'],px=sz/64,mx=[mx.get(j,0) for j in range(e['ncols'])],mn=[mn.get(j,0) for j in range(e['ncols'])],dev=m['s_dev'],model=e['sc'],peak=m['peak']))
def pred(r,pad,cap):
    P=pad*r['px']; C=cap*r['px']
    W=sum(max(a,min(b,C))+P for b,a in zip(r['mx'],r['mn']))
    return 1.0 if W<=r['avail'] else r['avail']/W
use=[r for r in rows if not r['spans']]
best=None
for pad in np.arange(1.0,1.7,0.01):
    for cap in np.arange(4,10,0.1):
        err=np.mean([abs(pred(r,pad,cap)-min(1.0,r['dev']))/ max(0.3,min(1.0,r['dev'])) for r in use])
        if best is None or err<best[0]: best=(err,pad,cap)
print("best mean rel err",best, "n tables",len(use))
err,pad,cap=best
for r in rows:
    pm=pred(r,pad,cap); d=min(1.0,r['dev'])
    print(r['th'][:3],"k",r['k'],"n",r['n'],"S" if r['spans'] else " ","dev",r['dev'],"pred",round(pm,3),"engine",round(r['model'],3),"err%",round(100*(pm-d)/d,1))
