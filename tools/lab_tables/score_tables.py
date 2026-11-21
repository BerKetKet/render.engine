"""Score tables_images in all 3 themes against exam/tables_images_exam (run from repo root).
usage: python3 tools/lab_tables/score_tables.py ENGINEDIR TAG [extra render args]
ENGINEDIR is the directory that contains kindle_render (use . for the repo). The epub path below must point to the tables_images epub in your checkout (tools/profiles.json lists it)."""
import sys,subprocess,os,glob,json
B=os.getcwd(); sys.path.insert(0,B)
from kindle_render.compare import compare
eng,tag=sys.argv[1],sys.argv[2]; extra=sys.argv[3:]
TH={"Standard":(44,2880,68,79,1001),"Compact":(35,2496,53,39,1041),"Large":(57,3200,82,131,949)}
tot=0; res={}
for th,(n,sz,p,x0,r) in TH.items():
    o=f"tools/lab_tables/work/score_{tag}_{th}"
    subprocess.run(["python3","-m","kindle_render","epub","exam/tables_images_exam/kindle_tables_images_exam.epub",o,"--pages","200","--size26",str(sz),"--x0",str(x0),"--right",str(r),"--pitch",str(p),"--top","168","--page-bottom","2203"]+extra,capture_output=True,env={**os.environ,"PYTHONPATH":eng})
    cap=f"{B}/exam/tables_images_exam/theme_{th}"
    nout=len(glob.glob(o+"/page_*.png")); ident=0; diff=0; per={}
    for i in range(1,n+1):
        f=f"{o}/page_{i:03d}.png"
        if not os.path.exists(f): per[i]=None; continue
        c=compare(f"{cap}/page_{i:03d}.png",f); ident+=c['bitwise_exact']; diff+=c['diff_pixel_count']; per[i]=c['diff_pixel_count']
    tot+=diff; res[th]=dict(pages=nout,dev=n,exact=ident,diff=diff,per=per)
    worst=sorted([(v,i) for i,v in per.items() if v],reverse=True)[:5]
    print(f"{th:9} pages {nout}/{n} exact {ident} diff_px {diff:,} worst {[i for v,i in worst]}",flush=True)
print("TOTAL diff_px",f"{tot:,}")
json.dump(res,open(f"tools/lab_tables/work/score_{tag}.json","w"))
