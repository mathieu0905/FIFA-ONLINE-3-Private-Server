from pathlib import Path
import sys,json,hashlib,struct,zlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;V3=W.parent/'lineup-enhance-v3'
src3=(V3/'test.py').read_text('utf8');exec(compile(src3.split('\nbuild=json.loads')[0],'<replay support>','exec'))
# Execute the real native query switch and first/second setters, not a model
# that assumes a rendered row exists or assumes a click selected the card.
old="elif op in (0x61,0x68):k=name();v=pop();o=pop();o[k]=v"
assert old in source
source=source.replace(old,"""elif op in (0x61,0x68):
                k=name();v=pop()
                if k=='[late]':k=pop();o=pop();o[k]=v
                else:o=pop();assign(o,k,v)
            elif op==0x08:locals.pop(r.u30(),None)
            elif op==0x1b:
                default=r.s24();n=r.u30();offsets=[r.s24() for _ in range(n+1)];index=int(pop());r.p=at+(offsets[index] if 0<=index<=n else default)""")
source=source.replace("if isinstance(o,dict):return o.get(k,U)","if isinstance(o,dict):\n            if k in o.get('__getters',{}):return o['__getters'][k]()\n            return o.get(k,U)")
def assign(obj,key,value):
 fn=obj.get('__setters',{}).get(key) if isinstance(obj,dict) else None
 if fn:fn(value)
 else:obj[key]=value
ns['assign']=assign;exec(source,ns);VM=ns['VM'];U=ns['U']
build=json.loads((W/'client-build.json').read_text());renderer=ABC((W/'components-ScrollingList-3451-after.abc').read_bytes());screen=ABC((W/'TeamManagementScreen-29-after.abc').read_bytes());native=ABC((V3/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes());PENDING='fo3LineupRequestV2';ICON='fo3LineupEnhanceV3'
checks=[];stacks={}
for a,key,mid in [(renderer,'renderer',43),(screen,'driver',20)]:
 stacks[key]=stackns['check'](a,mid)
 for code in a.A['body'].values():assert all(code[t]==9 for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at)
fixture=src3[src3.index('class Display'):src3.index('def setup(')];exec(compile(fixture,'<display fixture>','exec'))
class ButtonClass(dict):
 def __call__(self,*args):return dict(type=args[0])
def setup(single=False,locked=False,expired=False,disabled=False):
 clock=[10000];nav=[];calls=[];root=display();main=dict(_id='target-instance',spid=123,grade=10,numDuplicated=1 if single else 2,enabled=not disabled,locked='expired' if expired else 'future' if locked else None)
 decoy=dict(_id='same-spid-decoy',spid=123,grade=10,numDuplicated=2,enabled=True,locked=None)
 inventory=[decoy,main];visible=[decoy] if single else list(inventory)
 dp={'length':len(visible),'requestItemAt':lambda i:visible[i]}
 listing=display(dataProvider=dp,validateNow=lambda:None,invalidateData=lambda:None,getRendererAt=lambda *args:(_ for _ in ()).throw(AssertionError('Renderer must not be used')))
 checkbox=display(selected=False)
 def showall(event):assert event['type']=='buttonClick';visible[:]=inventory;dp['length']=len(visible);calls.append('showall');return True
 checkbox['dispatchEvent']=showall
 player={'_selectedTargets':[None,None],'showAllPlayersButton':checkbox,'enhanceList':listing}
 view=display(playerPanel=player,lockinfo={'enhance':True});wrapper=display();wrapper['addChild'](view)
 subtab={'selectedIndex':1,'indexOfByClassName':lambda _:1,'selectedTabPage':wrapper}
 root['teamManagementTab']={'switchTabPage':lambda route:nav.append(route),'selectedTabPage':{'playerSettingTab':subtab}}
 def machine(a,obj):
  m=VM(a,obj);m.globals.update(getTimer=lambda:clock[0],Array=list,ZoneManager={'instance':{'currentZone':{'query':lambda url,q:machine(screen,root).run(2,(q,))}}},ButtonEvent=ButtonClass(CLICK='buttonClick'),getDefinitionByName=lambda name:(lambda:display()),TimerUtil={'parseW3CDTF':lambda s:{'value':s,'getFullYear':lambda:2026},'getTime2':lambda:0},DateUtils={'getMinutesDiff':lambda now,date:-1 if date['value']=='expired' else 1})
  return m
 for key,mid in [('firstTarget',2),('secondTarget',4)]:
  player.setdefault('__setters',{})[key]=lambda value,mid=mid:machine(native,player).run(mid,(value,))
 for key,mid in [('firstTarget',1),('secondTarget',3)]:player.setdefault('__getters',{})[key]=lambda mid=mid:machine(native,player).run(mid)
 def query(command,data):
  if command=='clear selected player':machine(native,player).run(18,('post selected players',[None,None]));calls.append('clear')
  elif command=='post selected players':machine(native,player).run(18,(command,data));calls.append('post')
  elif command=='selected player':calls.append(('selected',data[0],data[1]))
 view['query']=query
 root['fo3LineupDriveV3']=lambda event:machine(screen,root).run(20,(event,))
 row=display(data=dict(id='target-instance',spid=123,grade=10,__lockButtonVisible=True),playerDetailInfoButton=display(x=407),playerLockButton=display(x=467),playerUnLockButton=display(x=467))
 row['fo3LineupClickV3']=lambda e:machine(renderer,row).run(42,(e,))
 return locals()
def click(x):x['machine'](renderer,x['row']).run(42,({'stopPropagation':lambda:None},))
def tick(x):x['machine'](screen,x['root']).run(20,(None,))
for single in (False,True):
 x=setup(single=single);click(x)
 for _ in range(7):tick(x)
 assert x['player']['_selectedTargets'][0] is x['main'] and x['player']['_selectedTargets'][1] is None
 assert x['calls'].count('post')==1 and len([v for v in x['calls'] if isinstance(v,tuple) and v[0]=='selected'])==1
 assert len(x['nav'])==1 and x['root'][PENDING] is None
 tick(x);assert x['calls'].count('post')==1
checks.append('Exact native query18 + first/second setter2/4 select the requested instance as primary, material null, for duplicate and singleton cards; same-SPID decoy ignored; no renderer dependency; once-only')
for mode in ('locked','expired','disabled','grade-changed','spid-changed','missing','loading','deadline','left-screen'):
 x=setup(locked=mode=='locked',expired=mode=='expired',disabled=mode=='disabled');click(x);tick(x)
 if mode=='grade-changed':x['main']['grade']=11
 if mode=='spid-changed':x['main']['spid']=124
 if mode=='missing':x['inventory'][:]=[x['decoy']]
 if mode=='loading':x['checkbox']['dispatchEvent']=lambda _:None;x['dp']['length']=0
 if mode=='deadline':x['clock'][0]=50000
 if mode=='left-screen':x['subtab']['selectedIndex']=0
 for _ in range(6):tick(x)
 if mode=='expired':assert x['player']['_selectedTargets'][0] is x['main']
 else:assert x['player']['_selectedTargets']==[None,None],mode
checks.append('Lockinfo/timestamp semantics, expired lock, disabled, changed identity fields, missing/loading, deadline and other tab regressions pass; no auto-unlock/purchase/enhance')
for mid in (18,1,2,3,4,79,80,85,86):assert native.A['body_records'][mid]['raw']==ABC((W.parent/'lineup-enhance-shortcut/TeamManagementPlayerEnhancementTabPage-289.abc').read_bytes()).A['body_records'][mid]['raw']
current=Path(r'D:\FO3ID\32795\data\ui\TeamManagementPlayerEnhancementTabPage.big');assert hashlib.sha256(current.read_bytes()).hexdigest()=='cd8f7b2d8dd747eb617b6b64b93631602a99ad77bdead962403b690fbbdde314'
raw=json.loads((W/'real-avm-results.json').read_text('utf8'));assert 'VerifyError: Error #1021' in raw['broken']['output'];assert 'DRIVE_RETURNED' in raw['labels_fixed']['output'] and 'VerifyError' not in raw['labels_fixed']['output']
assert ABC((W/'labels_fixed.abc').read_bytes()).A['body'][20]==screen.A['body'][20]
checks.append('Real AVMplus validates exact produced root driver; broken negative control reproduces #1021; enhancement BIG remains completely untouched')
# The new button inherits only the original stop-frame method bodies.
skin=ABC((W/'Fo3LineupUpgradeButton.abc').read_bytes());assert skin.A['cls'][0][0]=='Fo3LineupUpgradeButton'
assert build['components-Button']['metadata']['all_original_symbols_and_dds_preserved']
checks.append('New upward double-chevron vector symbol retains original native capsule states/natural size; old exchange symbol and every DDS remain unchanged')
result=dict(status='PASS',checks=checks,stack_checks=stacks,real_avm_verifier_pass=True,source_sha256={k:v['source_sha256'] for k,v in build.items()},output_sha256={k:v['sha256'] for k,v in build.items()},native_game_verified=False,GUI_used=False,real_assets_written=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
