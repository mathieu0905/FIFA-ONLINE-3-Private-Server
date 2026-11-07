"""Execute the emitted AVM2 helpers with display and native selection contracts."""
from pathlib import Path
import sys,json,copy
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,R,instructions,T
W=Path(__file__).resolve().parent
ns={'__file__':str(W/'test.py')}
exec(Path(r'D:\fifaol3\enhancement-remember\test_client.py').read_text('utf8').split('a=ABC((W/')[0],ns)
source=ns['source'].replace('elif op==0x65:', '''elif op==0x42:
                n=r.u30();args=[pop() for _ in range(n)][::-1];fn=pop();stack.append(fn(*args))
            elif op==0x41:
                n=r.u30();args=[pop() for _ in range(n)][::-1];receiver=pop();fn=pop();stack.append(fn(*args))
            elif op==0x56:
                n=r.u30();stack.append([pop() for _ in range(n)][::-1])
            elif op==0x65:''')
exec(source,ns);VM=ns['VM'];U=ns['U']
stackns={'__file__':str(W/'test.py')};stacksource=Path(r'D:\fifaol3\enhancement-entry-fix\test_stacks.py').read_text('utf8').split('results={}')[0]
stacksource=stacksource.replace('elif op==0x41:', 'elif op==0x42:pops=1+operand();pushes=1\n        elif op==0x41:')
stacksource=stacksource.replace('(0x46,0x4a,0x4f)', '(0x45,0x46,0x4a,0x4f)')
stacksource=stacksource.replace('0x85,0x90', '0x85,0x86,0x90').replace('(0x73,0x76', '(0x73,0x74,0x75,0x76')
exec(stacksource,stackns)
def display(**values):
 d=dict(visible=True,parent=None,stage=True,children=[],x=0,y=0,graphics={});d.update(values)
 def add(child):
  child['parent']=d;d['children'].append(child);return child
 def remove(child):d['children'].remove(child);child['parent']=None;return child
 d.update(getChildByName=lambda n:next((v for v in d['children'] if v.get('name')==n),None),addChild=add,removeChild=remove,hasOwnProperty=lambda n:n in d)
 for name in ('beginFill','drawRoundRect','endFill','lineStyle','moveTo','lineTo'):d['graphics'][name]=lambda *args:None
 d['listeners']={};d['addEventListener']=lambda event,callback:d['listeners'].update({event:callback})
 return d
def vm(a,obj):
 v=VM(a,obj);v.globals.update(MovieClip=display,getTimer=lambda:10000);return v
build=json.loads((W/'client-build.json').read_text());checks=[];stacks={}
for file,row in build.items():
 for prefix,block in row['blocks'].items():
  a=ABC((W/(prefix+'-after.abc')).read_bytes())
  stacks[prefix]={str(mid):stackns['check'](a,mid) for mid in block['changed']+block['added']}
renderer=ABC((W/'components-ScrollingList-3451-after.abc').read_bytes());panel=ABC((W/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes())
meta=build['components-ScrollingList']['blocks']['components-ScrollingList-3451']['callbacks'];accept=build['TeamManagementPlayerEnhancementTabPage']['blocks']['TeamManagementPlayerEnhancementTabPage-289']['callbacks']['accept']
def bind(a,obj,name,mid):obj[name]=lambda arg:vm(a,obj).run(mid,(arg,))
def setup():
 nav=[];root=display(teamManagementTab={'switchTabPage':lambda path:nav.append(path)})
 row=display(data={'id':'chosen','spid':123,'grade':10,'__lockButtonVisible':True},playerDetailInfoButton=display(x=500,visible=True),playerLockButton=display(x=526,y=3),playerUnLockButton=display(x=526,y=3))
 root['addChild'](row)
 for name,mid in [('fo3LineupEnhanceClick',meta['click']),('fo3UpdateEnhanceIcon',meta['sync'])]:bind(renderer,row,name,mid)
 vm(renderer,row).run(meta['init'],(None,));return root,row,nav
root,row,nav=setup();icon=row['getChildByName']('fo3LineupEnhanceIcon');assert icon['x']==526 and icon['y']==3
assert [row[k]['x'] for k in ('playerDetailInfoButton','playerLockButton','playerUnLockButton')]==[474,500,500]
assert len(icon['listeners'])==1 and icon['buttonMode'] and not icon['mouseChildren']
vm(renderer,row).run(meta['init'],(None,));assert len(row['children'])==1 and row['playerLockButton']['x']==500
for data,visible,expected in [(row['data'],True,True),(None,True,False),({'__lockButtonVisible':False},True,False),({'__lockButtonVisible':True},False,False)]:
 row['data']=data;row['playerDetailInfoButton']['visible']=visible;vm(renderer,row).run(meta['sync'],(None,));assert icon['visible']==expected
checks.append('Vector arrow icon created once; search/lock shifted one slot; selected-row visibility and recycled-empty-row hiding verified')
root,row,nav=setup();stopped=[];event={'stopImmediatePropagation':lambda:stopped.append(True)}
v=vm(renderer,row);v.run(meta['click'],(event,));assert stopped and not v.puts
req=root['getChildByName']('fo3LineupEnhanceRequest');assert req['fo3id']=='chosen' and req['fo3spid']==123 and req['fo3grade']==10
assert nav==[[{'pageClassname':'TeamManagementPlayerTabPage'},{'tabname':'playerSettingTab','pageClassname':'TeamManagementPlayerEnhancementTabPage'}]]
# Recycled renderer callback must bind current card rather than its first row.
row['data']={'id':'new-instance','spid':123,'grade':11};v.run(meta['click'],(event,));assert req['fo3id']=='new-instance' and len(root['children'])==2
checks.append('Click stops row propagation; native nested Tab navigator opens enhancement; recycled row reads current instance; no network purchase/enhance request')
def run_case(mode):
 root,row,_=setup();vm(renderer,row).run(meta['click'],(event,));req=root['getChildByName']('fo3LineupEnhanceRequest')
 calls=[];chosen={'_id':'chosen','spid':123,'grade':10,'enabled':True,'numDuplicated':2};other={'_id':'same-spid-other-instance','spid':123,'grade':10}
 p=display(_players=[other,chosen]);root['addChild'](p)
 def clear():p['firstTarget']=None;p['secondTarget']=None;calls.append('clear')
 def select(first,second):p['firstTarget']=first;p['secondTarget']=second;calls.append('select')
 p.update(clearSelectedPlayer=clear,availableEnhancePlayer=lambda _:mode!='native-ineligible',selectTarget=select,invalidatePlayerList=lambda:calls.append('invalidate'))
 if mode=='missing':p['_players']=[other]
 if mode=='empty':p['_players']=[]
 if mode=='wrong-season':chosen['spid']=456
 if mode=='changed-grade':chosen['grade']=11
 if mode=='expired':req['fo3time']=-100000
 if mode=='timer-reset':req['fo3time']=20000
 if mode=='hidden':p['visible']=False
 if mode=='ancestor-hidden':root['visible']=False
 if mode=='detached':p['stage']=None
 if mode=='no-request':root['removeChild'](req)
 v=vm(panel,p);v.run(accept,(None,));assert not v.puts
 if mode=='valid':
  assert p['firstTarget'] is chosen and p['secondTarget'] is None and calls==['clear','select','invalidate']
  v.run(accept,(None,));assert calls==['clear','select','invalidate']
 elif mode=='native-ineligible':assert calls==['clear']
 else:assert not calls,mode
 if mode in ('empty','hidden','ancestor-hidden','detached'):assert root['getChildByName']('fo3LineupEnhanceRequest') is req
 else:assert root['getChildByName']('fo3LineupEnhanceRequest') is None
for mode in ('valid','missing','empty','wrong-season','changed-grade','expired','timer-reset','hidden','ancestor-hidden','detached','no-request','native-ineligible'):run_case(mode)
checks.append('12 primary-selection cases: exact instance only, same-SPID decoy ignored, one-shot removal before callbacks, stale/changed/missing rejected, hidden/detached/async empty deferred, native eligibility retained, material stays empty')
# Verify native eligibility, first/second setters and selection code remain exactly current.
old=ABC((W/'TeamManagementPlayerEnhancementTabPage-289.abc').read_bytes())
for mid in (1,2,3,4,18,31,32,79,80,85,86,89):assert old.A['body_records'][mid]['raw']==panel.A['body_records'][mid]['raw']
checks.append('Native eligibility/lock rules, query, selection setters, selectTarget and protected-pair restore unchanged byte-for-byte')
result=dict(status='PASS',checks=checks,stack_checks=stacks,source_sha256={k:v['source_sha256'] for k,v in build.items()},output_sha256={k:v['sha256'] for k,v in build.items()},native_verified=False,game_gui_used=False,real_assets_written=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
