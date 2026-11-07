from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent))
import real_avm as r
from avm_patch import ABC,Code
W=Path(__file__).parent
(W/'scope-base.as').write_text('''package restorefixture {
public dynamic class Recovery {
 public var _restorePlayerData:Object={restoreSpaceState:"active",grade:0}; public var count:int=0;public var phase:String="";
 public function Recovery(){}
 public function loop():void{count++;_restorePlayerData.grade=count;phase="loop";}
 public function complete():void{phase="complete";}
}}
''',encoding='utf8')
r.compile_as('scope-base')
results={}
for version in ('before','after'):
 a=ABC((W/'scope-base.abc').read_bytes());cls=a.A['cls'][0]
 for name in ('loop','complete'):
  mid=next(v for k,n,v in cls[3] if k=='method' and n==name)
  def player(c):
   index=a.name('_restorePlayerData')
   return c.op(0x5d,index).op(0x66,index) if version=='before' else c.local(0).op(0x66,index)
  c=Code(a);player(c).jump(0x12,'native')
  if name=='loop':
   player(c).prop('restoreSpaceState').string('pending').jump(0x13,'skip')
   player(c).prop('restoreSpaceState').string('done').jump(0x14,'native');c.label('skip').op(0x47)
  else:player(c).string('done').set('restoreSpaceState')
  c.label('native');a.modify(mid,{0:c.done()})
 (W/('scope-'+version+'.abc')).write_bytes(a.output())
 (W/('scope-'+version+'-probe.as')).write_text('''import restorefixture.Recovery;var c:Recovery=new Recovery();
 try{c.loop();trace("LOOP_OK "+c.count+" "+c._restorePlayerData.grade);}catch(e:Error){trace("LOOP_ERROR "+e.toString());}
 try{c.complete();trace("COMPLETE_OK "+c.phase+" "+c._restorePlayerData.restoreSpaceState);}catch(e:Error){trace("COMPLETE_ERROR "+e.toString());}
''',encoding='utf8')
 r.compile_as('scope-'+version+'-probe',[W/('scope-'+version+'.abc')])
 out=r.run([r.engine,W/('scope-'+version+'.abc'),W/('scope-'+version+'-probe.abc')],'scope-'+version+'-result.log');results[version]=out.stdout+out.stderr;print(version,results[version])
assert 'ReferenceError' in results['before'] and 'LOOP_OK 1 1' in results['after'] and 'COMPLETE_OK complete done' in results['after']
raw=json.loads((W/'avm-raw-results.json').read_text('utf8'))
assert '#1006' in raw['callback-before'] and 'CALLBACK_OK true true' in raw['callback-after'] and 'PREVIEW_CALLED' in raw['callback-after']
result=dict(status='PASS',engine='Redtamarin AVMplus 2.1',exact_callback_1006_reproduced_and_fixed=True,restore_guard_before_pushscope_reference_error_reproduced_and_fixed=True,
 restore_guard_fixture_namespace_indices_remapped=True,full_popup_stock_avm_load_limitation='Both baseline and new full popup require additional Scaleform-compatible dependencies; stock VM reports #1107',
 game_gui_used=False,native_game_verified=False)
(W/'real-avm-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
