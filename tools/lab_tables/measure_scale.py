"""Scale of each table in the device capture by template matching engine row-bands (resized by r) against the device page.
usage (from repo root): python3 tools/lab_tables/measure_scale.py THEME -> tools/lab_tables/work/meas_THEME.json"""
import json,sys,os,numpy as np,cv2
from PIL import Image
TH={"Standard":(2880,79,1001),"Compact":(2496,39,1041),"Large":(3200,131,949)}
th=sys.argv[1]; sz,x0,right=TH[th]; size_px=sz/64.0
CAP=f"exam/tables_images_exam/theme_{th}"; ENG=f"tools/lab_tables/work/out_{th}"
def load(p): return (255-np.array(Image.open(p).convert("L"))).astype(np.float32)/255.0
def bands(ink,ya,yb):
    m=ink[ya:yb]>0.45; rows=m.any(axis=1); out=[]; i=0
    while i<len(rows):
        if rows[i]:
            j=i
            while j<len(rows) and rows[j]: j+=1
            out.append((ya+i,ya+j)); i=j
        else: i+=1
    return out
rows=[json.loads(l) for l in open(f"tools/lab_tables/work/log_{th}.jsonl")]
res=[]
for k,e in enumerate(rows):
    p=e['page0']
    rec=dict(k=k,page=p,ncols=e['ncols'],nrows=e['nrows'],spans=e['spans'],cap=e['cap'],sc_model=e['sc'],avail=e['avail_w'],tot_1x=e['tot_1x'],split=e['page0']!=e['page1'])
    if rec['split']: res.append(rec); print(k,"split skip"); continue
    ie=load(f"{ENG}/page_{p:03d}.png"); idv=load(f"{CAP}/page_{p:03d}.png")
    tbl_size26=int(round(sz*e['sc'])); s_eng=tbl_size26/float(sz)
    ya,yb=e['y0']-10,e['y1']+2
    tb=[]
    for b0,b1 in bands(ie,ya,yb):
        h=b1-b0
        if h<8: continue
        cols=np.where((ie[b0:b1]>0.45).any(axis=0))[0]
        if len(cols)==0: continue
        a,b=max(cols[0],x0-6),min(cols[-1]+1,right+8)
        w=b-a
        if h<=7 and w>0.6*(right-x0): continue          # rule
        fill=(ie[b0:b1,a:b]>0.45).sum()/float(h*w)
        if h>=40 and fill>0.5: continue                   # icon
        cl=np.where((ie[b0:b1,a:b]>0.45).any(axis=0))[0]
        gap=0.30*size_px*s_eng
        if len(cl)==0: continue
        st=cl[0]; pv=cl[0]; segs=[]
        for x in cl[1:]:
            if x-pv>gap: segs.append((st,pv)); st=x
            pv=x
        segs.append((st,pv))
        for sa,sb in segs:
            if sb-sa+1>=14: tb.append((b0-1,b1+1,a+sa-2,a+sb+3))
    tb=sorted(tb,key=lambda q:-(q[1]-q[0])*(q[3]-q[2]))[:10]
    rec['nbands']=len(tb)
    if not tb: res.append(rec); continue
    wy0=max(0,e['y0']-130); wy1=min(idv.shape[0],e['y1']+190)
    rng=np.random.default_rng(0)
    strip=idv[wy0:wy1].astype(np.float64); strip=(strip+rng.normal(0,0.02,strip.shape)).astype(np.float32)
    lo,hi=max(0.30,0.5*s_eng),min(1.08,1.8*s_eng)
    rgrid=np.exp(np.arange(np.log(lo/s_eng),np.log(hi/s_eng),0.02))
    scores=[]
    for r in rgrid:
        tot=0.0
        for (b0,b1,a,b) in tb:
            t=ie[b0:b1,a:b]
            tw,th_=int(round(t.shape[1]*r)),int(round(t.shape[0]*r))
            if tw<8 or th_<6 or th_>=strip.shape[0] or tw>=strip.shape[1]: continue
            tt=cv2.resize(t,(tw,th_),interpolation=cv2.INTER_AREA if r<1 else cv2.INTER_LINEAR)
            if tt.std()<1e-3: continue
            tt=(tt.astype(np.float64)+rng.normal(0,0.02,tt.shape)).astype(np.float32)
            m=cv2.matchTemplate(strip,tt,cv2.TM_CCOEFF_NORMED)
            tot+=max(0.0,float(m.max()))*(t.shape[0]*t.shape[1])**0.5
        scores.append(tot)
    scores=np.array(scores); i=int(scores.argmax())
    rec['s_dev']=round(float(rgrid[i]*s_eng),3); rec['peak']=round(float(scores[i]),2); rec['second']=round(float(np.sort(scores)[-5]),2)
    rec['s_eng']=round(s_eng,3)
    res.append(rec)
    print(k,p,"n",e['ncols'],"model",round(e['sc'],3),"eng_eff",rec['s_eng'],"DEV",rec['s_dev'],"peak",rec['peak'],"bands",len(tb),flush=True)
json.dump(res,open(f"tools/lab_tables/work/meas_{th}.json","w"))
