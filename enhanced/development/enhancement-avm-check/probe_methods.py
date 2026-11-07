from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import *
W=Path(__file__).resolve().parent
import avm_patch
src=avm_patch.SOURCE.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []')
src=src.replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
ns={'__name__':'trait_bounds'};exec(compile(src,'<trait bounds>','exec'),ns)
for label,folder,suffix,prefix,cname in [('stable','enhancement-remember','before','TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel'),('failed','enhancement-entry-fix','after','TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel'),('fixed','enhancement-ui-loop-fix','after','TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel'),('owner-failed','enhancement-entry-fix','after','EnhancePlayerPanel','EnhancePlayerPanel'),('owner-fixed','enhancement-ui-loop-fix','after','EnhancePlayerPanel','EnhancePlayerPanel')]:
 data=(W.parent/folder/(prefix+'-'+suffix+'.abc')).read_bytes();a=ABC(data)
 cls=next(c for c in a.A['cls'] if c[0]==cname)
 mids=sorted(set(mid for kind,name,mid in cls[3] if kind in ('method','get','set')))
 names={mid:a.name('probe_'+str(mid)) for mid in mids}
 updated=a.output();parsed=ns['parse'](updated,0);row=next(r for r in parsed['trait_records'] if r['values']==cls[3]);r=R(updated,row['start']);count=r.u30()
 records=[]
 for _ in range(count):
  begin=r.p;name=r.u30();flags=r.u8();kind=flags&15
  if kind in (1,2,3):
   dispatch=r.u30();mid=r.u30()
   if flags&0x40:
    for _ in range(r.u30()):r.u30()
   records.append(u30(names[mid])+b'\x01'+u30(0)+u30(mid))
  else:
   assert kind in (0,6)
   r.u30();r.u30();value=r.u30()
   if value:r.u8()
   if flags&0x40:
    for _ in range(r.u30()):r.u30()
   records.append(updated[begin:r.p])
 assert r.p==row['end']
 updated=updated[:row['start']]+u30(count)+b''.join(records)+updated[row['end']:]
 (W/(label+'.abc')).write_bytes(updated)
 cases=[]
 for mid in mids:
  cases.append('try { c["probe_'+str(mid)+'"].apply(c, '+json.dumps([None]*len(a.A['sig'][mid]))+'); trace("'+str(mid)+' OK"); } catch(e:Error) { trace("'+str(mid)+' "+e.toString()); }')
 harness='import fok.display.screens.teammanagement.'+cname+'; var c:Object=new '+cname+'();\n'+'\n'.join(cases)
 (W/(label+'-probe.as')).write_text(harness,encoding='utf8')
print('Probe aliases added only to isolated diagnostic ABC; all original method bodies unchanged')
