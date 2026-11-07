"""Verify the exact shipped drive method using stock AVMplus; no game GUI."""
from pathlib import Path
import sys,subprocess,json
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,Code,u30,instructions
W=Path(__file__).resolve().parent;SDK=Path(r'D:\fifaol3\enhancement-avm-check\lib\redtamarin')
engine=SDK/'bin/redshell_dd.exe';core=SDK/'lib/redtamarin.abc';asc=SDK/'support/asc.jar'
def run(cmd,label):
 p=subprocess.run([str(v) for v in cmd],cwd=W,capture_output=True,text=True,errors='replace',timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 (W/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf8');return p
def compile_as(name,imports=()):
 cmd=['java','-jar',asc,'-AS3','-import',core]
 for p in imports:cmd+=['-import',p]
 p=run(cmd+[W/(name+'.as')],name+'-compile');assert p.returncode==0,p.stdout+p.stderr
data=Path(r'D:\fifaol3\lineup-enhance-v3\TeamManagementScreen-29-after.abc').read_bytes();a=ABC(data)
hier={'DisplayObject':'flash.events.EventDispatcher','InteractiveObject':'flash.display.DisplayObject','DisplayObjectContainer':'flash.display.InteractiveObject','Sprite':'flash.display.DisplayObjectContainer','MovieClip':'flash.display.Sprite','UIComponent':'flash.display.MovieClip'}
names={(a.A['mnns'][i],n) for i,n in enumerate(a.A['mn']) if a.A['mnns'][i] and ':' not in a.A['mnns'][i] and n[:1].isupper() and n!='TeamManagementScreen'}
names.add(('fok.interfaces','IAttachable'))
for n,ns in [('DisplayObject','flash.display'),('InteractiveObject','flash.display'),('DisplayObjectContainer','flash.display'),('Sprite','flash.display'),('MovieClip','flash.display'),('UIComponent','scaleform.clik.core')]:names.add((ns,n))
def depth(n):return 1+depth(hier[n].rsplit('.',1)[-1]) if n in hier else 0
rows=[]
for ns,n in sorted(names,key=lambda p:(depth(p[1]),p)):
 if ns=='flash.events' or ns=='flash.utils':continue
 if n in ('IAttachable','ITabPage','IEventDispatcher'):rows.append('package '+ns+' { public interface '+n+' {} }');continue
 parent=hier.get(n,'Object');imp='import '+parent+'; ' if '.' in parent else '';extra=''
 if n=='UIComponent':extra='protected function configUI():void{} protected function initialize():void{}'
 rows.append('package '+ns+' { '+imp+'public dynamic class '+n+' extends '+parent.rsplit('.',1)[-1]+' {public function '+n+'(...args){super();} '+extra+'} }')
(W/'stubs.as').write_text('\n'.join(rows),encoding='utf8');compile_as('stubs')
result={}
for version in ('broken','labels_fixed'):
 b=ABC(data)
 if version=='labels_fixed':
  code=b.A['body'][20];targets={t for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at and code[t]!=9};assert len(targets)==2
  b.modify(20,{t:b'\x09' for t in targets})
 # Isolate construction from Scaleform timeline resources only. The inspected
 # drive method's production body, signature and class traits remain unchanged.
 rec=b.A['body_records'][1];stub=bytes.fromhex('d030d0490047')
 b.changed[1]=u30(1)+b''.join(u30(x) for x in rec['fields'])+u30(len(stub))+stub+rec['suffix']
 out=b.output();(W/(version+'.abc')).write_bytes(out)
 if version=='broken':assert ABC(out).A['body'][20]==a.A['body'][20]
 harness='import fok.display.screens.teammanagement.TeamManagementScreen; var c:Object=new TeamManagementScreen(); try { c.fo3LineupDriveV3(null); trace("DRIVE_RETURNED"); } catch(e:Error) { trace("DRIVE_ERROR "+e.toString()); }'
 (W/(version+'-probe.as')).write_text(harness,encoding='utf8');compile_as(version+'-probe',[W/'stubs.abc',W/(version+'.abc')])
 p=run([engine,W/'stubs.abc',W/(version+'.abc'),W/(version+'-probe.abc')],version+'-result')
 result[version]=dict(exit=p.returncode,output=p.stdout+p.stderr)
(W/'real-avm-results.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps({k:{'exit':v['exit'],'tail':v['output'].splitlines()[-2:]} for k,v in result.items()}))
