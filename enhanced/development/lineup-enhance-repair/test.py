"""Exact bytecode regressions for native skin, event unwinding and Zone routing."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,R,instructions
W=Path(__file__).resolve().parent
ns={'__file__':str(W/'test.py')};exec(Path(r'D:\fifaol3\enhancement-remember\test_client.py').read_text('utf8').split('a=ABC((W/')[0],ns)
source=ns['source'].replace('elif op==0x65:', '''elif op==0x87:
                kind=pop();value=pop();stack.append(value)
            elif op==0x42:
                n=r.u30();args=[pop() for _ in range(n)][::-1];fn=pop();stack.append(fn(*args))
            elif op==0x56:
                n=r.u30();stack.append([pop() for _ in range(n)][::-1])
            elif op==0x65:''')
exec(source,ns);VM=ns['VM'];U=ns['U']
stackns={'__file__':str(W/'test.py')};src=Path(r'D:\fifaol3\enhancement-entry-fix\test_stacks.py').read_text('utf8').split('results={}')[0]
src=src.replace('elif op==0x41:', 'elif op==0x42:pops=1+operand();pushes=1\n        elif op==0x41:').replace('(0x46,0x4a,0x4f)', '(0x45,0x46,0x4a,0x4f)').replace('0x85,0x90','0x85,0x86,0x90').replace('(0x73,0x76','(0x73,0x74,0x75,0x76')
exec(src,stackns)
build=json.loads((W/'client-build.json').read_text());stacks={};checks=[]
for key,b in build.items():
 for prefix,block in b['blocks'].items():
  a=ABC((W/(prefix+'-after.abc')).read_bytes())
  stacks[prefix]={str(m):stackns['check'](a,m) for m in block['changed']+block['added']}
renderer=ABC((W/'components-ScrollingList-3451-after.abc').read_bytes());panel=ABC((W/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes());screen=ABC((W/'TeamManagementScreen-29-after.abc').read_bytes())
zoneabc=ABC((W/'native-Zone.abc').read_bytes())
rm=build['components-ScrollingList']['blocks']['components-ScrollingList-3451']['callbacks'];pm=build['TeamManagementPlayerEnhancementTabPage']['blocks']['TeamManagementPlayerEnhancementTabPage-289']['callbacks'];sm=build['TeamManagementScreen']['blocks']['TeamManagementScreen-29']['callbacks']
ICON='fo3NativeEnhanceIcon';PENDING='fo3LineupRequestV2'
class Display(dict):
 def __bool__(self):return True
def display(**values):
 d=Display(visible=True,stage=True,x=0,y=0,width=30,height=30,children=[],listeners={});d.update(values)
 d['getChildByName']=lambda name:next((c for c in d['children'] if c.get('name')==name),None)
 d['addChild']=lambda child:d['children'].append(child)
 d['addEventListener']=lambda e,fn:d['listeners'].update({e:fn})
 d['removeEventListener']=lambda e,fn:d['listeners'].pop(e,None)
 return d
def setup():
 nav=[];native_skins=[];root=display(teamManagementTab={'switchTabPage':lambda route:nav.append(route)});clock=[10000]
 def instance(a,obj):
  v=VM(a,obj)
  def query(url,data):
   assert url=='TeamManagementScreen.swf'
   # Execute shipped Zone.query/callOnQuery/getScreenFromLoader/getLoaderName.
   root['onQuery']=lambda data:instance(screen,root).run(2,(data,))
   root['toString']=lambda:'TeamManagementScreen'
   loader={'content':root}
   zone={'_attachedScreens':{'getChildByName':lambda name:loader if name=='TeamManagementScreen.swfLoader' else None}}
   for name,mid in [('getLoaderName',8),('query',51),('callOnQuery',52),('getScreenFromLoader',54)]:
    zone[name]=lambda *args,mid=mid:instance(zoneabc,zone).run(mid,args)
   instance(zoneabc,zone).run(51,(url,data))
  def skin(name):
   assert name=='PlayerGrowthIncreaseButton';native_skins.append(name);return display
  v.globals.update(ZoneManager={'instance':{'currentZone':{'query':query}}},ButtonEvent={'CLICK':'buttonClick'},getDefinitionByName=skin,getTimer=lambda:clock[0],StringUtil={'GetFileName':lambda s:s.rsplit('/',1)[-1]},LoaderEx=object,IAttachable=object,DisplayObjectContainer=object);return v
 root['fo3LineupNavigateV2']=lambda e:instance(screen,root).run(sm['navigate'],(e,))
 row=display(data={'id':'selected-instance','spid':123,'grade':10,'__lockButtonVisible':True},playerDetailInfoButton=display(x=407,visible=True),playerLockButton=display(x=467),playerUnLockButton=display(x=467))
 row['fo3NativeEnhanceClickV2']=lambda e:instance(renderer,row).run(rm['click'],(e,))
 row['fo3NativeEnhanceSyncV2']=lambda e:instance(renderer,row).run(rm['sync'],(e,))
 return root,row,nav,instance,clock,native_skins
root,row,nav,vm,clock,skins=setup()
originals={k:dict(row[k]) for k in ('playerDetailInfoButton','playerLockButton','playerUnLockButton')}
vm(renderer,row).run(rm['init'],(None,));vm(renderer,row).run(rm['sync'],(None,));icon=row['getChildByName'](ICON)
assert icon['visible'] and icon['x']==527 and icon['width']==30 and icon['height']==30 and 'buttonClick' in icon['listeners']
assert all(dict(row[k])==v for k,v in originals.items())
vm(renderer,row).run(rm['init'],(None,));assert len(row['children'])==1 and skins==['PlayerGrowthIncreaseButton']
row['playerDetailInfoButton']['visible']=False;vm(renderer,row).run(rm['sync'],(None,));assert not icon['visible']
row['data']=None;vm(renderer,row).run(rm['sync'],(None,));assert not icon['visible']
row['data']={'id':'selected-instance','spid':123,'grade':10,'__lockButtonVisible':True};row['playerDetailInfoButton']['visible']=True
row['playerLockButton']=None;vm(renderer,row).run(rm['sync'],(None,));assert icon['visible']
row['playerUnLockButton']=None;vm(renderer,row).run(rm['sync'],(None,));assert not icon['visible']
checks.append('Actual native PlayerGrowthIncreaseButton class, native ButtonEvent.CLICK and native dimensions; new icon x527 after untouched search407/lock467; no graphics, no native button moves, duplicate creation or null-anchor crash')

def event():return {'stopPropagation':lambda:None}
root,row,nav,vm,clock,skins=setup();v=vm(renderer,row);v.run(rm['click'],(event(),));assert not v.puts and not nav
assert root[PENDING]['id']=='selected-instance' and root[PENDING]['createdAt']==10000
assert set(root['listeners'])=={'enterFrame'}
root['listeners']['enterFrame'](None);assert not root['listeners']
assert nav==[[{'pageClassname':'TeamManagementPlayerTabPage'},{'tabname':'playerSettingTab','pageClassname':'TeamManagementPlayerEnhancementTabPage'}]]
row['data']={'id':'recycled-instance','spid':123,'grade':10};vm(renderer,row).run(rm['click'],(event(),));assert root[PENDING]['id']=='recycled-instance'
checks.append('Actual Zone.query reaches TeamManagementScreen.onQuery; click returns before navigation; one-shot next-frame handler invokes native nested Tab switch; recycled row reads current instance')

def primary(mode):
 root,row,nav,vm,clock,skins=setup();vm(renderer,row).run(rm['click'],(event(),));root['listeners']['enterFrame'](None)
 calls=[];chosen={'_id':'selected-instance','spid':123,'grade':10};decoy={'_id':'same-spid-decoy','spid':123,'grade':10}
 p=display(_players=[decoy,chosen])
 def clear():p.update(firstTarget=None,secondTarget=None);calls.append('clear')
 def select(first,second):p.update(firstTarget=first,secondTarget=second);calls.append('select');assert root[PENDING] is None
 p.update(clearSelectedPlayer=clear,selectTarget=select,availableEnhancePlayer=lambda _:mode!='native-ineligible',invalidatePlayerList=lambda:calls.append('invalidate'))
 p['fo3LineupAcceptV2']=lambda e:vm(panel,p).run(pm['accept'],(e,))
 if mode=='empty':p['_players']=[]
 if mode=='missing':p['_players']=[decoy]
 if mode=='grade-changed':chosen['grade']=11
 if mode=='season-changed':chosen['spid']=124
 if mode=='expired':clock[0]=80000
 if mode=='timer-reset':clock[0]=0
 if mode=='detached':p['stage']=None
 if mode=='hidden':p['visible']=False
 if mode=='no-request':root[PENDING]=None
 vm(panel,p).run(pm['schedule'],(None,));assert not calls
 p['listeners']['enterFrame'](None);assert not p['listeners']
 if mode=='valid':
  assert calls==['clear','select','invalidate'] and p['firstTarget'] is chosen and p['secondTarget'] is None
  vm(panel,p).run(pm['accept'],(None,));assert calls==['clear','select','invalidate']
 elif mode=='native-ineligible':assert calls==['clear']
 else:assert not calls,mode
 if mode in ('hidden','detached','empty'):assert root[PENDING] is not None
 else:assert root[PENDING] is None
for mode in ('valid','empty','missing','grade-changed','season-changed','expired','timer-reset','detached','hidden','no-request','native-ineligible'):primary(mode)
checks.append('Primary selection also waits one frame after native inventory/start; 11 exact-instance/decoy/empty/changed/expired/detached/native-ineligible cases; material empty, consume before re-entry, no purchase/enhance PUT')
# Run the actual injected root-detach cleanup slice with no native side effects.
root,row,nav,vm,clock,skins=setup();vm(renderer,row).run(rm['click'],(event(),))
patch=json.loads((W/'TeamManagementScreen-29-patch.json').read_text())['7'];old=bytes.fromhex(patch['original']);at=patch['insertion_offsets'][0];end=next(e for x,e,_,_ in instructions(old) if x==at)
vm(screen,root).run(7,start=patch['mapping'][str(at)],stop=patch['mapping'][str(end)]-(end-at));assert root[PENDING] is None and not root['listeners']
checks.append('Native screen detach clears pending request and deferred navigation listener')
old=ABC((W.parent/'lineup-enhance-shortcut/TeamManagementPlayerEnhancementTabPage-289.abc').read_bytes())
for m in (1,2,3,4,18,31,32,79,80,85,86,89):assert panel.A['body_records'][m]['raw']==old.A['body_records'][m]['raw']
for a,mids in ((renderer,(36,37,38)),(panel,(90,))):
 for m in mids:assert a.A['body'][m]==b'\x47'
checks.append('Faulty v1 callbacks are inert; native lock/eligibility/setters/query/selectTarget/protected-pair restore unchanged; no parent walks or carrier MovieClips')
result=dict(status='PASS',checks=checks,stack_checks=stacks,source_sha256={k:v['source_sha256'] for k,v in build.items()},output_sha256={k:v['sha256'] for k,v in build.items()},native_verified=False,unique_crash_cause_proven=False,gui_used=False,real_assets_written=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
