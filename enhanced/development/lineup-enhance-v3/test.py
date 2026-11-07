"""Readiness and native event-path regressions; no GUI/native-runtime claim."""
from pathlib import Path
import sys,json,struct
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent
base=Path(r'D:\fifaol3\lineup-enhance-repair\test.py').read_text('utf8').split('build=json.loads')[0]
exec(compile(base,'<replay helpers>','exec'))
source=source.replace('elif op==0x87:', '''elif op==0xb4:
                obj=pop();key=pop();stack.append(key in obj)
            elif op==0x49:
                n=r.u30();args=[pop() for _ in range(n)][::-1];obj=pop();obj.update(type=args[0],bubbles=args[1],cancelable=args[2])
            elif op==0x87:''')
exec(source,ns);VM=ns['VM'];U=ns['U']
src=src.replace('elif op in (0xa0,','elif op==0xb4:pops=2;pushes=1\n        elif op in (0xa0,');exec(src,stackns)
build=json.loads((W/'client-build.json').read_text());stacks={};checks=[]
for key,b in build.items():
 for prefix,block in b['blocks'].items():
  a=ABC((W/(prefix+'-after.abc')).read_bytes());stacks[prefix]={str(m):stackns['check'](a,m) for m in block['changed']+block['added']}
renderer=ABC((W/'components-ScrollingList-3451-after.abc').read_bytes());screen=ABC((W/'TeamManagementScreen-29-after.abc').read_bytes());panel=ABC((W/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes());eventabc=ABC((W/'native-ListEvent.abc').read_bytes())
rm=build['components-ScrollingList']['blocks']['components-ScrollingList-3451']['callbacks'];drive=build['TeamManagementScreen']['blocks']['TeamManagementScreen-29']['callbacks']['drive'];PENDING='fo3LineupRequestV2';ICON='fo3LineupEnhanceV3'
class Display(dict):
 def __bool__(self):return True
def display(**values):
 d=Display(visible=True,stage=True,x=0,y=0,width=64,height=37,children=[],listeners={},graphics={});d.update(values)
 d['getChildByName']=lambda name:next((c for c in d['children'] if c.get('name')==name),None)
 def add(child):d['children'].append(child);d['numChildren']=len(d['children']);return child
 d.update(addChild=add,numChildren=len(d['children']),getChildAt=lambda i:d['children'][i],addEventListener=lambda e,fn:d['listeners'].update({e:fn}),removeEventListener=lambda e,fn:d['listeners'].pop(e,None))
 for fn in ('beginFill','moveTo','lineTo','endFill'):d['graphics'][fn]=lambda *args:None
 return d
def setup(eligible=True):
 clock=[10000];nav=[];calls=[];root=display();selected={'_id':'target-instance','spid':123,'grade':10};decoy={'_id':'same-spid-decoy','spid':123,'grade':10};inventory=[decoy,selected]
 dp={'length':2,'requestItemAt':lambda i:inventory[i]};rendered=display(data=selected)
 listing=display(dataProvider=dp,scrollPosition=0,getRendererAt=lambda i,offset:rendered if i==1 else None,validateNow=lambda:None)
 nativepanel={'enhanceList':listing,'availableEnhancePlayer':lambda item:eligible,'selectedIndex':lambda id:-1,'getEmptyPlayerIndex':lambda:0,'selectedIndexBySPID':lambda spid:-1,'selectTarget':lambda main,material:calls.append(('select',main,material)),'invalidatePlayerList':lambda:calls.append(('invalidate',))}
 def dispatch(event):
  assert root.get(PENDING) is None and not root['listeners'];assert event['type']=='itemClick' and event['itemRenderer'] is rendered and event['itemData'] is selected
  machine(panel,nativepanel).run(31,(event,));return True
 listing['dispatchEvent']=dispatch
 view=display(playerPanel={'enhanceList':listing},query=lambda command,data:calls.append(('clear-native',command,data)))
 wrapper=display();wrapper['addChild'](view)
 subtab={'selectedIndex':1,'indexOfByClassName':lambda name:1,'selectedTabPage':wrapper}
 root['teamManagementTab']={'switchTabPage':lambda route:nav.append(route),'selectedTabPage':{'playerSettingTab':subtab}}
 skins=[]
 def machine(a,obj):
  v=VM(a,obj)
  def getclass(name):assert name=='TransferMarketRollOverButton';skins.append(name);return display
  def eventctor(*args):
   assert len(args)==11 and args[0]=='itemClick' and args[3]==1 and args[4:6]==(-1,-1)
   event={};machine(eventabc,event).run(1,args);return event
  v.globals.update(ZoneManager={'instance':{'currentZone':{'query':lambda url,data:machine(screen,root).run(2,(data,))}}},getTimer=lambda:clock[0],getDefinitionByName=getclass,MovieClip=display,ButtonEvent={'CLICK':'buttonClick'},ListEvent=eventctor,ArrayUtil={'NOT_FOUND':-1});return v
 root['fo3LineupDriveV3']=lambda e:machine(screen,root).run(drive,(e,))
 row=display(data={'id':'target-instance','spid':123,'grade':10,'__lockButtonVisible':True},playerDetailInfoButton=display(x=407),playerLockButton=display(x=467),playerUnLockButton=display(x=467))
 row['fo3LineupClickV3']=lambda e:machine(renderer,row).run(rm['click'],(e,))
 return locals()
def click(x):x['machine'](renderer,x['row']).run(rm['click'],({'stopPropagation':lambda:None},))
def tick(x):x['machine'](screen,x['root']).run(drive,(None,))
x=setup();row=x['row'];before={key:dict(row[key]) for key in ('playerDetailInfoButton','playerLockButton','playerUnLockButton')}
x['machine'](renderer,row).run(rm['init'],(None,));x['machine'](renderer,row).run(rm['sync'],(None,));icon=row['getChildByName'](ICON)
assert (icon['x'],icon['width'],icon['height'])==(527,64,37) and icon['visible'] and x['skins']==['TransferMarketRollOverButton']
assert all(dict(row[k])==v for k,v in before.items());assert icon['children'][0]['mouseEnabled'] is False and icon['children'][0]['mouseChildren'] is False
assert 'buttonClick' in icon['listeners']
checks.append('Blank native capsule plus code-drawn blue upward arrow uses fixed 64x37 geometry; existing search/lock/unlock objects and coordinates untouched; glyph does not intercept input')
x=setup();click(x);assert not x['nav'];tick(x);assert len(x['nav'])==1 and not x['calls']
tick(x);assert not x['calls'] and x['listing']['selectedIndex']==1
tick(x);assert not x['calls'];tick(x)
assert x['calls']==[('clear-native','clear selected player',None),('select',x['selected'],None),('invalidate',)]
assert x['root'][PENDING] is None;tick(x);assert len(x['calls'])==3
checks.append('Click returns before navigation; waits for populated native DataProvider, actual matching renderer and two stable frames; executes original ListEvent constructor and native onClickListItem31; exact instance selected once as main with material null')
for mode in ('unloaded-tab','unloaded-wrapper','empty-children','unloaded-panel','unloaded-list','empty-list','null-renderer','stale-renderer','wrong-grade','wrong-spid','missing','expired','timer-reset','too-many-children','poll-limit'):
 x=setup();click(x);tick(x)
 if mode=='unloaded-tab':x['root']['teamManagementTab']['selectedTabPage']=None
 if mode=='unloaded-wrapper':x['subtab']['selectedTabPage']=None
 if mode=='empty-children':x['wrapper']['children']=[];x['wrapper']['numChildren']=0
 if mode=='unloaded-panel':x['view']['playerPanel']=None
 if mode=='unloaded-list':x['view']['playerPanel']['enhanceList']=None
 if mode=='empty-list':x['dp']['length']=0
 if mode=='null-renderer':x['listing']['getRendererAt']=lambda *args:None
 if mode=='stale-renderer':x['rendered']['data']=x['decoy']
 if mode=='wrong-grade':x['selected']['grade']=11
 if mode=='wrong-spid':x['selected']['spid']=124
 if mode=='missing':x['inventory'][1]=dict(x['decoy'])
 if mode=='expired':x['clock'][0]=50000
 if mode=='timer-reset':x['clock'][0]=0
 if mode=='too-many-children':x['wrapper']['numChildren']=33
 if mode=='poll-limit':x['root'][PENDING]['polls']=600
 for _ in range(4):tick(x)
 assert not x['calls'],mode
 assert len(x['nav'])==1,mode
checks.append('15 not-ready/stale/missing/changed/deadline cases never select or loop synchronously; navigation is gated once even if frame handler removal fails')
x=setup(False);click(x)
for _ in range(4):tick(x)
assert x['calls']==[('clear-native','clear selected player',None)]
checks.append('Original native eligibility handler rejects unavailable/locked card without a select or asset request')
original=(W.parent/'lineup-enhance-shortcut/TeamManagementPlayerEnhancementTabPage-289.abc').read_bytes();assert (W/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes()==original
assert build['TeamManagementPlayerEnhancementTabPage']['sha256']=='cd8f7b2d8dd747eb617b6b64b93631602a99ad77bdead962403b690fbbdde314'
assert not any('fo3Lineup' in name or 'fo3Accept' in name for name in panel.A['mn'])
checks.append('ENTIRE enhancement BIG is byte-identical to pre-shortcut stable resource, including constant pools, traits, method metadata and startup handlers; zero new enhancement startup/inventory/frame hooks')
result=dict(status='PASS',checks=checks,stack_checks=stacks,source_sha256={k:v['source_sha256'] for k,v in build.items()},output_sha256={k:v['sha256'] for k,v in build.items()},native_verified=False,crash_fixed_proven=False,gui_used=False,real_assets_written=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
