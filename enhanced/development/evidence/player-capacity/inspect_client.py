"""Read-only extraction of the actual roster-capacity UI contract."""
from pathlib import Path
import sys,struct,zlib,json,re,hashlib
sys.dont_write_bytecode=True
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
sys.path.insert(0,str(W));from avm_patch import ABC,dis
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
O=Path(__file__).parent;out=[]
for name in ['libs/Module.big','TransferPurchaseTabPage.big','TeamManagementTeamInfoTabPage.big']:
    p=Path('D:/FO3ID/32795/data/ui')/name
    for member,*_ in bigdir.entries(p):
        if not member.endswith('.gfx'):continue
        g=bigdir.read(p,member);swf=g if g[:3] in (b'FWS',b'GFX') else b'FWS'+g[3:8]+zlib.decompress(g[8:])
        for hit in re.finditer(b'\x10\x00\x2e\x00',swf):
            try:a=ABC(swf[hit.start():])
            except (ValueError,IndexError,AssertionError,struct.error):continue
            names={}
            for cls,sup,ii,traits,ci,ct in a.A['cls']:
                names[ii]=cls+'.init';names[ci]=cls+'.cinit'
                for kind,n,mid in traits+ct:
                    if kind in ('get','set','method'):names[mid]=cls+'.'+n
            keys=[i for i,n in enumerate(a.A['mn']) if re.search(r'limitPlayer|[Mm]axPlayer|[Pp]layerLimit|firstTeamLimit',n)]
            for mid,code in a.A['body'].items():
                lines=dis(a.A,code)
                if any(re.search(r'limitPlayer|[Mm]axPlayer|[Pp]layerLimit|baseplayers|firstTeam|getproperty limits',line) for line in lines):
                    traits=[t for cls,sup,ii,ts,ci,ct in a.A['cls'] for t in ts+ct if re.search(r'limitPlayer|[Mm]axPlayer',str(t))]
                    out.append(dict(archive=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),abc=hit.start(),method=mid,name=names.get(mid,str(mid)),capacity_traits=traits,code='\n'.join(lines)))
(O/'client-capacity-contract.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
print(json.dumps([dict(archive=r['archive'],name=r['name'],method=r['method']) for r in out],indent=2))
