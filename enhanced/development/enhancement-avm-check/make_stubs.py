from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-remember')
from client_tools import ABC,dis
W=Path(__file__).resolve().parent
paths=[Path(r'D:\fifaol3\enhancement-entry-fix\TeamManagementPlayerEnhancementTabPage-after.abc')]
paths.append(Path(r'D:\fifaol3\enhancement-ui-loop-fix\EnhancePlayerPanel-after.abc'))
names=set()
for path in paths:
 a=ABC(path.read_bytes())
 for i,n in enumerate(a.A['mn']):
  ns=a.A['mnns'][i]
  if ns and ':' not in ns and n[:1].isupper() and n not in ('EnhanceControlPanel','EnhancePlayerPanel'):names.add((ns,n))
hierarchy={'EventDispatcher':'Object','DisplayObject':'flash.events.EventDispatcher','InteractiveObject':'flash.display.DisplayObject','DisplayObjectContainer':'flash.display.InteractiveObject','Sprite':'flash.display.DisplayObjectContainer','MovieClip':'flash.display.Sprite','UIComponent':'flash.display.MovieClip','ComboBox':'flash.display.MovieClip','CheckBoxEx':'flash.display.MovieClip','ButtonEx':'flash.display.MovieClip','TextField':'flash.display.DisplayObject'}
rows=[]
def depth(n):return 1+depth(hierarchy[n].split('.')[-1]) if n in hierarchy and hierarchy[n]!='Object' else 0
for ns,n in sorted(names,key=lambda row:(depth(row[1]),row)):
 if ns=='flash.events' or (ns=='flash.utils' and n in ('Timer','Dictionary')):continue
 if n=='IEventDispatcher':rows.append('package '+ns+' { public interface '+n+' {} }');continue
 base=hierarchy.get(n,'Object')
 extra=''
 if n=='UIComponent':extra='protected function configUI():void {}'
 if n=='MovieClip':extra='public function getChildByName(s:String):Object { return this.children[s]; } public var children:Object={}; public function addChild(o:Object):Object {this.children[o.name]=o;return o;}'
 imports=('import '+base+'; ' if '.' in base else '')
 rows.append('package '+ns+' { '+imports+'public dynamic class '+n+' extends '+base.split('.')[-1]+' { public function '+n+'(...args) {super();} '+extra+' } }')
(W/'stubs.as').write_text('\n'.join(rows),encoding='utf8')
print(len(rows))
print('\n'.join(dis(a.A,a.A['body'][4])))
