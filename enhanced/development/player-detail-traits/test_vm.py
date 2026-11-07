"""Execute the actual patched tab dispatcher and closures in AVM2 with UI stubs.
No game process or formal asset is modified. This is not native rendering QA.
"""
from build_ui import *
import subprocess
V=ROOT/'vm';V.mkdir(exist_ok=True)
SDK=Path('D:/fifaol3/enhancement-avm-check/lib/redtamarin')
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf8',errors='replace',cwd=V)
 if p.returncode or '[Compiler] Error' in p.stdout+p.stderr:raise RuntimeError(p.stdout+'\n'+p.stderr)
 return p.stdout+p.stderr
def prepare():
 a=ABC((ROOT/'ui-build/popup-after.abc').read_bytes());cls=next(x for x in a.A['cls'] if x[0]=='PlayerDetailPopup')
 # Only the diagnostic copy's timeline constructor is bypassed, so no missing
 # Scaleform timeline instances are required. Production constructor is exact.
 ctor=Code(a).local(0).op(0x30).local(0).op(0x49,0)
 ctor.local(0).lex('PlayerDetailTraitScrollPan','fok.dynamicobjects').op(0x42,0).ownset('myTraitScrollPanel').op(0x47)
 record(a,cls[2],ctor.done(),[3,1,11,12])
 # Only diagnostic environment adapters are bypassed; dispatch/visibility code
 # remains the actual patched method, and these production methods are exact.
 for mid in (29,33,36):record(a,mid,b'\x47',a.A['body_records'][mid]['fields'])
 alias=a.name('probeTab');updated=a.output()
 import avm_patch
 src=avm_patch.SOURCE.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []')
 src=src.replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
 ns={'__name__':'trait_bounds'};exec(compile(src,'<trait bounds>','exec'),ns)
 parsed=ns['parse'](updated,0);row=next(r for r in parsed['trait_records'] if r['values']==cls[3])
 from avm_patch import R
 reader=R(updated,row['start']);count=reader.u30();records=[]
 for _ in range(count):
  begin=reader.p;name=reader.u30();tail=reader.p;flags=reader.u8();kind=flags&15;mid=None
  if kind in (1,2,3):reader.u30();mid=reader.u30()
  elif kind in (0,6):
   reader.u30();reader.u30();value=reader.u30()
   if value:reader.u8()
  else:raise RuntimeError('Unexpected trait kind')
  if flags&0x40:
   for _ in range(reader.u30()):reader.u30()
  records.append((u30(alias)+b'\x01'+b'\x00'+u30(mid)) if mid==24 else updated[begin:reader.p])
 assert reader.p==row['end']
 updated=updated[:row['start']]+u30(count)+b''.join(records)+updated[row['end']:]
 (V/'popup-probe.abc').write_bytes(updated)
 names=set()
 for i,n in enumerate(a.A['mn']):
  namespace=a.A['mnns'][i]
  if namespace and ':' not in namespace and n[:1].isupper() and n!='PlayerDetailPopup':names.add((namespace,n))
 hierarchy={'EventDispatcher':'Object','DisplayObject':'flash.events.EventDispatcher','InteractiveObject':'flash.display.DisplayObject',
  'DisplayObjectContainer':'flash.display.InteractiveObject','Sprite':'flash.display.DisplayObjectContainer','MovieClip':'flash.display.Sprite',
  'UIComponent':'flash.display.MovieClip','TextField':'flash.display.DisplayObject','HtmlLabel':'flash.display.MovieClip',
  'ScrollingListEx':'flash.display.MovieClip','Tab':'flash.display.MovieClip','ButtonEx':'flash.display.MovieClip'}
 extra={
  'MovieClip':'public var children:Object={}; public function addChild(o:Object):Object { children[o.name]=o; return o; } public function getChildByName(n:String):Object {return children[n];} public function removeChild(o:Object):Object {delete children[o.name]; return o;}',
  'UIComponent':'public function invalidateData():void {} protected function configUI():void {} protected function draw():void {} public function get width():Number {return 0;} public function get height():Number {return 0;}',
  'Localization':'public static function TEAMNAME(id:*):String {return "club-"+id;} public static function getLocalizedString(s:String):String {return s;}',
  'DataProvider':'public function requestItemAt(i:int):Object {return this[i];}',
  'PlayerListUtil':'public static var PLAYER_TRAITS:Array=[];',
  'SquadScreenHandler':'public static function updatePlayerTrait(a:*,b:*):void {for(var i:int=1;i<=8;i++)a.content["_traitDescription"+i].visible=true;} public static function updatePlayerBadges(a:*,b:*):void {} public static function updateWorkrate(a:*,b:*):void {} public static function updatePlayerClubHistory(a:*,b:*):void {}',
  'PlayerDetailTraitScrollPan':'public function refresh():void {} public function setScrollPercent(n:Number):void {}'
 }
 # This class belongs to the same asset and the diagnostic code references it;
 # its original definition is present only in its own ABC, so stub it here.
 for key in ('PlayerDetailTraitScrollPan','SquadScreenHandler'):
  names.add(('fok.dynamicobjects',key))
 names.add(('scaleform.clik.data','DataProvider'))
 lines=[]
 def depth(name):return 1+depth(hierarchy[name].split('.')[-1]) if name in hierarchy and hierarchy[name]!='Object' else 0
 for namespace,n in sorted(names,key=lambda row:(-1 if row[1]=='IDataProvider' else depth(row[1]),row)):
  if (namespace=='flash.events' and n!='MouseEvent') or namespace=='flash.utils':continue
  if n=='IDataProvider':
   lines.append('package '+namespace+' { public interface IDataProvider {} }');continue
  base=hierarchy.get(n,'Object');imports='import '+base+'; ' if '.' in base else ''
  if n=='DataProvider':imports+='import scaleform.clik.interfaces.IDataProvider; '
  implement=' implements IDataProvider' if n=='DataProvider' else ''
  ctor='if(args.length && args[0] is Array) { for(var i:int=0;i<args[0].length;i++)this[i]=args[0][i]; this.length=args[0].length; }' if n=='DataProvider' else ''
  lines.append('package '+namespace+' { '+imports+'public dynamic class '+n+' extends '+base.split('.')[-1]+implement+' { public function '+n+'(...args){super();'+ctor+'} '+extra.get(n,'')+' } }')
 (V/'stubs.as').write_text('\n'.join(lines),'utf8')
 probe=r'''
import fok.dynamicobjects.PlayerDetailPopup;
import fok.dynamicobjects.PlayerDetailTraitScrollPan;
import scaleform.clik.data.DataProvider;
import scaleform.clik.controls.ScrollingListEx;
import scaleform.clik.controls.Tab;
import scaleform.clik.controls.ButtonEx;
import flash.display.MovieClip;
import flash.text.TextField;
import fok.components.HtmlLabel;
import fok.events.TabEvent;
import fok.utils.PlayerListUtil;
function check(v:Boolean,s:String):void {if(!v) throw new Error(s); trace("PASS "+s);}
var c:PlayerDetailPopup=new PlayerDetailPopup();
c.pricePage=new MovieClip(); c.statList=new ScrollingListEx(); c.positionSubTabBar=new Tab(); c.myPlayerTraitInfo=new MovieClip();
c.ovrPreviewPage=new MovieClip(); c.ovrPreviewPage.enhancementComboBox={};c.ovrPreviewPage.levelComboBox={};
c.averageStatsName=new HtmlLabel();c.averageStatsLeft=new TextField(); c.contractButton=new ButtonEx();c.remainingPlaysName=new HtmlLabel();c.traitscrollBar=new MovieClip();
function history(spid:int,tid:int,h:Array,pid:int=0):Array {
 c.dataProvider=new DataProvider([{spid:spid,staticdata:{playerid:pid,teamid:tid,clubhistory:h}}]);
 var event:TabEvent=new TabEvent();event.tabIndex=2;c.probeTab(event);var result:Array=[];for(var i:int=0;i<c.statList.dataProvider.length;i++)result.push(c.statList.dataProvider[i].stat_name);return result;
}
var rows:Array=history(84037576,999984,null);
check(rows.indexOf("club-243")>=0,"Ronaldo contains Real Madrid with hidden native history");
check(rows.indexOf("club-44")>=0,"Ronaldo contains Inter");
check(rows.indexOf("club-999984")<0,"season placeholder excluded");
rows=history(13158023,241,[{teamid:241},{teamid:241},{teamid:73}]);
var count:int=0;for each(var s:String in rows)if(s=="club-241")count++;
check(count==1,"current and repeated historical clubs deduplicated");
check(rows.indexOf("club-73")>=0,"current native additions preserved");
rows=history(999999999,999999,null);
check(rows.length==1 && rows[0]=="暂无可显示的俱乐部户口","empty history handled");
check(c.statList.visible && !c.myPlayerTraitInfo.visible && !c.positionSubTabBar.visible && !c.pricePage.visible,"history page visibility");
check(!c.ovrPreviewPage.levelComboBox.enabled,"history page disables stat preview");
c.myPlayerTraitInfo.content=new MovieClip();c.myPlayerTraitInfo.clubhistorypanel={visible:true};c.myPlayerTraitInfo.barMC={visible:true};
for(var k:int=1;k<=8;k++)c.myPlayerTraitInfo.content["_traitDescription"+k]={x:10,y:100,width:400,textField:{defaultTextFormat:{font:"native"},embedFonts:true},visible:true};
PlayerListUtil.PLAYER_TRAITS=["A","B","C","D","E","F","G","H","I","J","K","L"];
c.dataProvider=new DataProvider([{spid:84037576,__traits:[0,1,2,3,4,5,6,7,8,9,10,11],staticdata:{}}]);
var te:TabEvent=new TabEvent();te.tabIndex=1;c.probeTab(te);
var expanded:Object=c.myPlayerTraitInfo.content.getChildByName("_imNativeTraitList");
check(expanded!=null && expanded.text.split("\n").length==12,"all twelve traits displayed beyond original eight");
check(!c.myPlayerTraitInfo.content._traitDescription1.visible,"original truncated labels hidden for IM");
check(!c.myPlayerTraitInfo.clubhistorypanel.visible && !c.myPlayerTraitInfo.barMC.visible,"history split out of trait tab");
c.dataProvider=new DataProvider([{spid:13037576,__traits:[0],staticdata:{}}]);c.probeTab(te);
check(c.myPlayerTraitInfo.content.getChildByName("_imNativeTraitList")==null,"expanded trait field removed when switching to season card");
check(c.myPlayerTraitInfo.content._traitDescription1.visible,"original season trait renderer retained");
c.positionSubTabBar.selectedIndex=0;te.tabIndex=0;c.probeTab(te);
check(c.statList.visible && c.positionSubTabBar.visible && !c.myPlayerTraitInfo.visible,"history to ability tab restores native controls");
check(c.ovrPreviewPage.levelComboBox.enabled && c.ovrPreviewPage.enhancementComboBox.enabled,"ability tab restores level and enhancement preview");
te.tabIndex=3;c.probeTab(te);
check(c.pricePage.visible && !c.statList.visible && !c.myPlayerTraitInfo.visible,"optional native price tab moved to index three");
trace("ALL_HISTORY_VM_PASS");
'''
 # Discover the exact original class namespaces rather than guessing them.
 for n in ('ScrollingListEx','Tab','ButtonEx','HtmlLabel','PlayerListUtil'):
  idx=next(i for i,s in enumerate(a.A['mn']) if s==n and a.A['mnns'][i])
  probe=__import__('re').sub(r'import [\w.]+\.'+n+';', 'import '+a.A['mnns'][idx]+'.'+n+';',probe)
 # PlayerDetailTraitScrollPan's actual namespace is read from the patched ABC.
 for n in ('PlayerDetailTraitScrollPan','SquadScreenHandler'):
  pass
 with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  bypid=collections.defaultdict(set)
  for pid,tid in db.execute('SELECT playerid,teamid FROM playerhistory'):bypid[pid].add(tid)
 ids=sorted(bypid);selected=sorted(set(ids[::48]+ids[47::48]+ids[-1:]))
 cases=[[pid,sorted(t for t in bypid[pid] if 0<t<900000)] for pid in selected]
 boundary='var cases:Array='+json.dumps(cases)+';\n'
 boundary+='''for each(var sample:Array in cases) {var actual:Array=history(84000000+sample[0],999984,null,sample[0]); var expected:Array=sample[1]; if(expected.length){if(actual.length!=expected.length)throw new Error("boundary count "+sample[0]);for each(var tid:int in expected)if(actual.indexOf("club-"+tid)<0)throw new Error("boundary team "+sample[0]);} } trace("PASS all lookup chunk boundaries: "+cases.length);\n'''
 probe=probe.replace('trace("ALL_HISTORY_VM_PASS");',boundary+'trace("ALL_HISTORY_VM_PASS");')
 (V/'probe.as').write_text(probe,'utf8')
 asc=['java','-jar',SDK/'support/asc.jar','-AS3','-import',SDK/'lib/redtamarin.abc']
 for n in ('stubs.abc','probe.abc'):(V/n).unlink(missing_ok=True)
 print(run(asc+[V/'stubs.as']))
 print(run(asc+['-import',V/'stubs.abc','-import',V/'popup-probe.abc',V/'probe.as']))
 result=run([SDK/'bin/redshell.exe',V/'stubs.abc',V/'popup-probe.abc',V/'probe.abc'])
 (V/'result.log').write_text(result,'utf8');print(result)
 assert 'ALL_HISTORY_VM_PASS' in result
if __name__=='__main__':prepare()
