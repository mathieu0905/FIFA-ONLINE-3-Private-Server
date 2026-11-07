"""Run exact production callback/restore bodies in AVMplus with UI-only stubs."""
from pathlib import Path
import sys,json,subprocess,hashlib,re
sys.dont_write_bytecode=True
W=Path(__file__).parent;AVM=Path(r'D:\fifaol3\enhancement-avm-check');SDK=AVM/'lib/redtamarin'
T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(T))
import avm_patch
from avm_patch import ABC,Code,R,u30
flags=subprocess.CREATE_NO_WINDOW
engine=SDK/'bin/redshell_dd.exe';core=SDK/'lib/redtamarin.abc';asc=SDK/'support/asc.jar'
def run(cmd,log):
 p=subprocess.run([str(v) for v in cmd],cwd=W,capture_output=True,text=True,errors='replace',creationflags=flags)
 (W/log).write_text(p.stdout+p.stderr,encoding='utf8');return p
def compile_as(name,imports=()):
 cmd=['java','-jar',asc,'-AS3','-import',core]
 for item in imports:cmd+=['-import',item]
 result=run(cmd+[W/(name+'.as')],name+'-compile.log')
 assert result.returncode==0 and (W/(name+'.abc')).is_file(),result.stdout+result.stderr

names={('fok.interfaces','IAttachable')}
for name in ('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen'):
 a=ABC((W/(name+'-before.abc')).read_bytes())
 for i,n in enumerate(a.A['mn']):
  ns=a.A['mnns'][i]
  if ns and ':' not in ns and n[:1].isupper() and n not in ('EnhanceControlPanel','TeamManagementPlayerEnhancingPopupScreen'):names.add((ns,n))
hierarchy={'EventDispatcher':'Object','DisplayObject':'flash.events.EventDispatcher','InteractiveObject':'flash.display.DisplayObject','DisplayObjectContainer':'flash.display.InteractiveObject','Sprite':'flash.display.DisplayObjectContainer','MovieClip':'flash.display.Sprite','UIComponent':'flash.display.MovieClip','ComboBox':'flash.display.MovieClip','CheckBoxEx':'flash.display.MovieClip','ButtonEx':'flash.display.MovieClip','TextField':'flash.display.DisplayObject','DynamicLoader':'flash.display.MovieClip'}
def depth(n):return 1+depth(hierarchy[n].split('.')[-1]) if n in hierarchy and hierarchy[n]!='Object' else 0
rows=[]
for ns,n in sorted(names,key=lambda row:(depth(row[1]),row)):
 if ns=='flash.events' or (ns=='flash.utils' and n in ('Timer','Dictionary')):continue
 if n=='IEventDispatcher' or ns.endswith('.interfaces'):rows.append('package '+ns+' { public interface '+n+' {} }');continue
 base=hierarchy.get(n,'Object');extra=''
 if n=='UIComponent':extra='protected function configUI():void {}'
 if n=='MovieClip':extra='public var children:Object={}; public var currentLabel:String=""; public function getChildByName(s:String):Object{return children[s];} public function addChild(o:Object):Object{children[o.name]=o;return o;} public function gotoAndPlay(v:Object):void{currentLabel=String(v);} public function gotoAndStop(v:Object):void{currentLabel=String(v);} public function stop():void{}'
 if n=='DynamicLoader':extra='public var value:Object; public function setData(v:Object):void{value=v;}'
 if n=='FeatureManager':extra='public static var instance:FeatureManager=new FeatureManager(); public function featuresAt(...args):FeatureManager{return this;} public function checkOne(v:Object):Boolean{return v=="v2_5";}'
 if n=='PlayerListUtil':extra='public static var callbacks:Array=[]; public static function expandPlayerStaticData(data:Object,fn:Function):void{callbacks.push(fn);fn(data);}'
 if n=='ObjectUtil':extra='public static function deepCopy(v:Object):Object{return v;}'
 if n=='StringUtil':extra='public static function formatToCurrency(v:Object):String{return String(v);}'
 if n=='Localization':extra='public static function getLocalizedString(v:Object):String{return String(v);} public static function getLocalizedStringWithArgs(v:Object,...args):String{return String(v);}'
 imports=('import '+base+'; ' if '.' in base else '')
 rows.append('package '+ns+' { '+imports+'public dynamic class '+n+' extends '+base.split('.')[-1]+' { public function '+n+'(...args){super();} '+extra+' } }')
(W/'avm-stubs.as').write_text('\n'.join(rows),encoding='utf8');compile_as('avm-stubs')
parser_source=avm_patch.SOURCE.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []')
parser_source=parser_source.replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
ns={'__name__':'diagnostic_traits'};exec(parser_source,ns)
def append_method(a,code,ret='void',params=1,initial=11,maxscope=12,local_count=2,needs_activation=False):
 mid=len(a.A['meth'])+len(a.methods);sig=u30(params)+u30(a.name(ret))+b''.join(u30(a.name('Object')) for _ in range(params))+u30(0)+bytes([2 if needs_activation else 0])
 body=u30(mid)+u30(32)+u30(local_count)+u30(initial)+u30(maxscope)+u30(len(code))+code+b'\0\0';a.methods.append((sig,body));return mid
def expose(a,cls,traits):
 # Add aliases; retain every original private/native trait so internal calls work.
 name_indices={name:a.name(name) for name,mid in traits};data=a.output();parsed=ns['parse'](data,0)
 row=next(r for r in parsed['trait_records'] if r['values']==cls[3]);reader=R(data,row['start']);count=reader.u30();entries=data[reader.p:row['end']]
 extra=b''.join(u30(name_indices[name])+b'\x01'+u30(0)+u30(mid) for name,mid in traits)
 return data[:row['start']]+u30(count+len(traits))+entries+extra+data[row['end']:]

results={}
for version in ('before','after'):
 # Restoration probe uses the actual state-machine bodies, no paid API path.
 a=ABC((W/('TeamManagementPlayerEnhancingPopupScreen-'+version+'.abc')).read_bytes());cls=a.A['cls'][0]
 c=Code(a).local(0).op(0x30)
 for field,key in [('_restorePlayerData','player'),('_restoreCount','count'),('_result','result'),('_data','data'),('container','clip'),('priceResult','price'),('boostInfoPanel','boost'),('_restoreButton','button'),('failurePlayer','loader'),('failureCardContainer','failure')]:
  index=a.own(field) if sum(n==field for n in a.A['mn'])==1 else a.name(field)
  c.local(0).local(1).prop('fixture_'+key).op(0x61,index)
 c.local(0).number(0).ownset('_restoreStep');c.op(0x47)
 setup=append_method(a,c.done(),initial=11,maxscope=12)
 c=Code(a).local(0).op(0x30).string('count').local(0).ownprop('_restoreCount').string('grade').local(0).ownprop('_restorePlayerData').prop('grade').string('state').local(0).ownprop('_restorePlayerData').prop('restoreSpaceState').string('label').local(0).ownprop('container').prop('currentLabel').op(0x55,4).op(0x48)
 get=append_method(a,c.done(),ret='Object',params=0,initial=11,maxscope=12,local_count=1)
 diag=expose(a,cls,[('probe_setup',setup),('probe_state',get),('probe_loop',46),('probe_complete',48),('probe_check',44)])
 label='restore-'+version;(W/(label+'.abc')).write_bytes(diag)
 harness='''import fok.display.screens.teammanagement.TeamManagementPlayerEnhancingPopupScreen;
import flash.display.MovieClip; import fok.controls.DynamicLoader;
for each(var target:int in [0,1,12,20]) {
 var c:Object=new TeamManagementPlayerEnhancingPopupScreen(); var clip:MovieClip=new MovieClip();
 c.probe_setup({fixture_player:{grade:0,restoreSpaceState:"active",spid:19020289,levelinfo:{level:30,exp:0}},fixture_count:target==0?-1:0,
 fixture_result:{resultgrade:target,resultPrice:12345,grantes:140},fixture_data:{info:{grade:14}},fixture_clip:clip,
 fixture_price:{priceTextField:{text:""}},fixture_boost:new MovieClip(),fixture_button:{visible:false,enabled:false},fixture_loader:new DynamicLoader(),fixture_failure:new MovieClip()});
 try {c.probe_loop();trace("LOOP "+target+" "+JSON.stringify(c.probe_state()));}catch(e:Error){trace("LOOP_ERROR "+target+" "+e.toString());}
 try {c.probe_complete();trace("COMPLETE "+target+" "+JSON.stringify(c.probe_state()));}catch(e:Error){trace("COMPLETE_ERROR "+target+" "+e.toString());}
}
'''
 (W/(label+'-probe.as')).write_text(harness,encoding='utf8');compile_as(label+'-probe',[W/'avm-stubs.abc',W/(label+'.abc')])
 out=run([engine,W/'avm-stubs.abc',W/(label+'.abc'),W/(label+'-probe.abc')],label+'-result.log')
 results[label]=out.stdout+out.stderr

 # Capture the actual anonymous callback with the same scope depth as initPanel.
 a=ABC((W/('TeamManagementPlayerEnhancementTabPage-'+version+'.abc')).read_bytes());cls=a.A['cls'][0]
 c=Code(a).local(0).op(0x30).local(0).op(0x26).ownset('_available').op(0x57).op(0x30).op(0x57).op(0x30).op(0x40,45).op(0x48)
 factory=append_method(a,c.done(),ret='Function',params=0,initial=11,maxscope=14,local_count=1,needs_activation=True)
 record=a.A['body_records'][35];body=Code(a).op(0x5d,a.name('trace')).string('PREVIEW_CALLED').call('trace',1).op(0x29).op(0x47).done()
 # Only the network-producing dependency is stubbed in this diagnostic copy.
 a.changed[35]=u30(35)+b''.join(u30(v) for v in record['fields'])+u30(len(body))+body+record['suffix']
 diag=expose(a,cls,[('probe_factory',factory)])
 label='callback-'+version;(W/(label+'.abc')).write_bytes(diag)
 harness='''import fok.display.screens.teammanagement.EnhanceControlPanel; import flash.display.MovieClip;
var c:Object=new EnhanceControlPanel();var box:MovieClip=new MovieClip();box.enabled=true;box.selected=false;box.fo3RememberProtection=false;
box.children["fo3ProtectionMark"]={visible:false};c.children["fo3ProtectionCheckbox"]=box;
var fn:Function=c.probe_factory();try{fn({currentTarget:box});trace("CALLBACK_OK "+box.selected+" "+box.fo3RememberProtection);}catch(e:Error){trace("CALLBACK_ERROR "+e.toString());}
'''
 (W/(label+'-probe.as')).write_text(harness,encoding='utf8');compile_as(label+'-probe',[W/'avm-stubs.abc',W/(label+'.abc')])
 out=run([engine,W/'avm-stubs.abc',W/(label+'.abc'),W/(label+'-probe.abc')],label+'-result.log');results[label]=out.stdout+out.stderr
for key,value in results.items():print(key,value[-2500:])
(W/'avm-raw-results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
