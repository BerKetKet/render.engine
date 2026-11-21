import json,sys,os,numpy as np
sys.path.insert(0,os.path.abspath("."))
from kindle_render.config import Config
from kindle_render.fonts import Family
TH={"Standard":2880,"Compact":2496,"Large":3200}
out=[]
for th,sz in TH.items():
    cfg=Config(); cfg.size26=sz; fam=Family(cfg); reg=fam.face(False,False,sz); bld=fam.face(True,False,sz)
    W=lambda f,s: sum(a for _,a in f.shape(s))/64.0
    logs=[json.loads(l) for l in open(f"tools/lab_tables/work/log_{th}.jsonl")]
    meas={m['k']:m for m in json.load(open(f"tools/lab_tables/work/meas_{th}.json"))}
    for k,e in enumerate(logs):
        m=meas.get(k,{})
        cols={}
        for ri,ci,t,h,cs,rs in e['cells']:
            if cs!=1: continue
            f=bld if h else reg
            d=cols.setdefault(ci,[0.0,0.0,0.0])
            d[0]=max(d[0],W(f,t)); d[1]=max(d[1],max([W(f,w) for w in t.split()] or [0])); d[2]=max(d[2],len(t.split()))
        mx=sum(v[0] for v in cols.values()); mn=sum(v[1] for v in cols.values())
        out.append(dict(th=th,k=k,page=e['page0'],ncols=e['ncols'],spans=e['spans'],avail=e['avail_w'],size=e['size_px'],pitch=e['pitch'],maxsum=mx,minsum=mn,maxw=max(v[0] for v in cols.values()) if cols else 0,model=e['sc'],dev=m.get('s_dev'),split=m.get('split')))
json.dump(out,open("tools/lab_tables/work/feat.json","w"))
for r in out:
    if r['dev'] is None: continue
    impl=r['avail']/r['dev']
    print(f"{r['th'][:3]} k{r['k']:2d} p{r['page']:2d} n{r['ncols']} {'S' if r['spans'] else ' '} avail {r['avail']:.0f} max {r['maxsum']:.0f} min {r['minsum']:.0f} dev {r['dev']:.3f} model {r['model']:.3f} impliedW {impl:.0f} impl/max {impl/max(1,r['maxsum']):.2f} impl/min {impl/max(1,r['minsum']):.2f}")
