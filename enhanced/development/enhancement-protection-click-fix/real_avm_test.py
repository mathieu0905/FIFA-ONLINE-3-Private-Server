from pathlib import Path
import json,sys,subprocess,re,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;AVM=W.parent/'enhancement-avm-check'
sys.path.insert(0,str(W))
from client_tools import ABC,Code,u30,sha,NAMES
logs={}
for label,path in [('before',W/(NAMES[0]+'-before.abc')),('after',W/(NAMES[0]+'-after.abc'))]:
 a=ABC(path.read_bytes())
 # Preserve the native class, owner setter and closure creation scope exactly.
 # Diagnostic init only supplies state and creates the original callback45;
 # requestPreview is replaced by a counter to avoid any network or assets.
 c=Code(a).local(0).local(0).ownprop('_owner').prop('available').ownset('_available')
 c.local(0).ownprop('_owner').op(0x40,45).set('callback').op(0x47)
 init=a.A['body'][8][:10]+c.done()
 preview=Code(a).local(0).op(0x30).local(0).ownprop('_owner').local(0).ownprop('_owner').prop('previewCount').number(1).op(0xa0).set('previewCount').op(0x47).done()
 for mid,code in ((8,init),(35,preview)):
  rec=a.A['body_records'][mid]
  a.changed[mid]=u30(mid)+b''.join(u30(v) for v in rec['fields'])+u30(len(code))+code+rec['suffix']
 diagnostic=a.output();d=ABC(diagnostic)
 assert d.A['body_records'][45]['raw']==a.A['body_records'][45]['raw']
 (W/(label+'-closure.abc')).write_bytes(diagnostic)
 harness='''
import fok.display.screens.teammanagement.EnhanceControlPanel;
import flash.display.MovieClip;
function assertTrue(b:Boolean,s:String):void {if(!b)throw new Error(s);}
var config:Object={available:true,previewCount:0};
var panel:Object=new EnhanceControlPanel(); panel.owner=config;
var box:MovieClip=new MovieClip();box.enabled=true;box.selected=false;
box.children.fo3ProtectionMark={visible:false};
var evt:Object={currentTarget:box};
var receiver:Object={notTheControlPanel:true};
'''
 if label=='before':
  harness+='''
try { config.callback.call(receiver,evt);throw new Error("Expected error absent"); }
catch(e:TypeError) {assertTrue(e.errorID==1006,"Wrong error: "+e);trace("REPRODUCED "+e);}
assertTrue(box.selected===true && box.children.fo3ProtectionMark.visible===true,"Native toggle should occur first");
assertTrue(config.previewCount==0,"Old error must interrupt fresh quote");
trace("BEFORE_EXPECTED_FAILURE_PASS");
'''
 else:
  harness+='''
for(var i:int=0;i<6;i++) {
 config.callback.call(receiver,evt);
 var selected:Boolean=(i%2==0);
 assertTrue(box.selected===selected,"toggle");
 assertTrue(box.fo3RememberProtection===selected,"memory");
 assertTrue(box.children.fo3ProtectionMark.visible===selected,"mark");
 assertTrue(config.previewCount==i+1,"one preview each click");
}
box.enabled=false;config.callback.call(receiver,evt);
assertTrue(config.previewCount==6 && box.selected===false,"disabled skip");
box.enabled=true;config.available=false;panel.owner=config;
config.callback.call(receiver,evt);
assertTrue(config.previewCount==6 && box.selected===false,"unavailable skip");
trace("AFTER_SIX_TOGGLES_DISABLED_UNAVAILABLE_PASS");
'''
 harness_path=W/(label+'-event.as');harness_path.write_text(harness,encoding='utf8')
 compile_result=subprocess.run(['java','-jar',str(AVM/'lib/redtamarin/support/asc.jar'),'-AS3','-import',str(AVM/'lib/redtamarin/lib/redtamarin.abc'),'-import',str(AVM/'stubs.abc'),'-import',str(W/(label+'-closure.abc')),str(harness_path)],capture_output=True,text=True,timeout=30)
 assert (W/(label+'-event.abc')).exists(),compile_result.stdout+compile_result.stderr
 proc=subprocess.run([str(AVM/'lib/redtamarin/bin/redshell_dd.exe'),str(AVM/'stubs.abc'),str(W/(label+'-closure.abc')),str(W/(label+'-event.abc'))],capture_output=True,text=True,timeout=20)
 log=proc.stdout+proc.stderr;(W/(label+'-real-avm.log')).write_text(log,encoding='utf8')
 assert proc.returncode==0,log
 assert ('BEFORE_EXPECTED_FAILURE_PASS' if label=='before' else 'AFTER_SIX_TOGGLES_DISABLED_UNAVAILABLE_PASS') in log,log
 logs[label]=log
result=dict(status='PASS',before_error='TypeError #1006 getChildByName is not a function',before_native_toggle_succeeded_but_quote_interrupted=True,
 after_six_toggles_memory_mark_single_preview_pass=True,disabled_and_unavailable_no_preview=True,
 actual_method45_unchanged_in_native_closure_test=True,engine='Redtamarin AVMplus 2.1 debug-debugger',
 limitation='External UI dependencies are stubs; init/counter are diagnostic-only; actual closure45 and owner binding retained; game UI remains unverified',
 native_game_verified=False,game_gui_used=False,source_sha256={str(W/(NAMES[0]+'-after.abc')):sha(W/(NAMES[0]+'-after.abc'))},
 logs={label:str(W/(label+'-real-avm.log')) for label in logs})
(W/'real-avm-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
