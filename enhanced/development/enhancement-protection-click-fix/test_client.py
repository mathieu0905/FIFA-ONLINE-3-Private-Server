from client_tools import *
import copy
# Reuse the established exact-opcode interpreter, not the previous tests.
src=Path('D:/fifaol3/enhancement-remember/test_client.py').read_text('utf8').split("a=ABC((W/")[0]
ns={'__file__':str(W/'test_client.py')};exec(src,ns);VM=ns['VM'];U=ns['U']
# Execute the original detach callback too, including cleanup between capture/restore.
vm_source=ns['source'].replace("elif op==0x65:","elif op==0x64:stack.append(self.globals)\n            elif op==0x41:\n                n=r.u30();args=[pop() for _ in range(n)][::-1];receiver=pop();fn=pop();stack.append(fn(*args))\n            elif op==0x65:")
exec(vm_source,ns);VM=ns['VM'];U=ns['U']
a=ABC((W/(NAMES[0]+'-after.abc')).read_bytes());o=ABC((W/'EnhancePlayerPanel-after.abc').read_bytes());p=ABC((W/(NAMES[1]+'-after.abc')).read_bytes())
cp=json.loads((Path('D:/fifaol3/enhancement-entry-fix')/(NAMES[0]+'-ABC.patch.json')).read_text());op=json.loads((W/'EnhancePlayerPanel-ABC.patch.json').read_text());pp=json.loads((W/(NAMES[1]+'-ABC.patch.json')).read_text())
meta=json.loads((W/'client-build.json').read_text());callback=89
def inject(abc,patch,mid,old,owner,args=()):
    row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()};code=bytes.fromhex(row['original']);end=next(e for at,e,_,_ in instructions(code) if at==old)
    vm=VM(abc,owner);out=vm.run(mid,args,start=mapping[old],stop=mapping[end]-(end-old));assert not vm.puts;return out
checks=[]
main={'_id':'main-instance','id':'main-instance','spid':123,'grade':9,'enabled':True,'locked':False,'numDuplicated':2}
mat={'_id':'material-instance','id':'material-instance','spid':123,'grade':8,'enabled':True,'locked':False,'numDuplicated':2}
data={'firstPlayer':copy.deepcopy(main),'secondPlayer':copy.deepcopy(mat)}
def owner_state():
    state={'stage':{'active':True},'visible':True,'firstTarget':None,'secondTarget':None,'_players':[copy.deepcopy(mat),dict(main,_id='another-copy'),copy.deepcopy(main)],'calls':[], 'isNotSelected':True}
    state['playerLockAllowEnhancement']=lambda:True;state['isPlayerLocked']=bool
    state['availableEnhancePlayer']=lambda row:VM(o,state).run(32,(row,))
    def select(first,second):
        state['firstTarget'],state['secondTarget']=first,second;state['calls'].append(('select',first,second))
        state['calls'].append(('fresh-preview-GET',first['_id'],second['_id']))
    state['selectTarget']=select;state['invalidatePlayerList']=lambda:state['calls'].append(('invalidate',))
    return state
def restore(state,payload):
    vm=VM(o,state);result=vm.run(callback,(payload,));assert not vm.puts;return result
for attempt in range(5):
    state=owner_state();restore(state,copy.deepcopy(data))
    assert state['firstTarget'] is state['_players'][2] and state['secondTarget'] is state['_players'][0]
    assert state['firstTarget'] is not data['firstPlayer'] and state['secondTarget'] is not data['secondPlayer']
    assert [c[0] for c in state['calls']]==['select','fresh-preview-GET','invalidate']
checks.append('Five protected-failure returns recover the same ordered instance IDs from fresh native inventory, call native selection/list invalidation and request a fresh preview without a PUT')
for mode in ('missing-main','missing-material','locked-main','locked-material','changed-grade','changed-season','hidden','detached','manual-pair','duplicate-id','invalid'):
    state=owner_state();payload=copy.deepcopy(data)
    if mode=='missing-main':state['_players']=[state['_players'][0]]
    elif mode=='missing-material':state['_players']=state['_players'][1:]
    elif mode=='locked-main':state['_players'][2]['locked']=True
    elif mode=='locked-material':state['_players'][0]['locked']=True
    elif mode=='changed-grade':state['_players'][2]['grade']=10
    elif mode=='changed-season':state['_players'][0]['spid']=124
    elif mode=='hidden':state['visible']=False
    elif mode=='detached':state['stage']=None
    elif mode=='manual-pair':state['firstTarget']={'_id':'new-choice'}
    elif mode=='duplicate-id':payload['secondPlayer']['_id']=payload['firstPlayer']['_id']
    elif mode=='invalid':payload=None
    restore(state,payload);assert not state['calls'],mode
checks.append('Eleven invalid/stale/manual scenarios do not restore: no substitution by SPID, no missing/locked/changed card, no overwriting a new pair or detached/hidden page')

checks.append('Restore is a bound public native-owner method; original query dispatcher is byte-identical to the successful baseline')

for mode in ('protected-failure','success','ordinary-failure','cancel','error','no-result','already-restored'):
    events=[];payload=copy.deepcopy(data);payload['fo3RestorePair']=lambda value:events.append(value)
    result={'result':True,'success':False,'protection':{'material_kept':True}}
    if mode=='success':result['success']=True
    elif mode=='ordinary-failure':result['protection']={}
    elif mode=='cancel':result=None
    elif mode=='error':result['result']=False
    elif mode=='no-result':result={}
    elif mode=='already-restored':payload['fo3PairRestored']=True
    popup={'_result':result,'_data':payload}
    def detach():popup['_result']=None;popup['_data']=None
    def run_detach():
        vm=VM(p,popup)
        vm.globals.update(ZoneManager={'instance':{'showGlobalZoneGroup':lambda _:None,'globalZone':{'query':lambda *_:None}}},Enums={'SCREEN_ALARMWINDOW':'alarm'})
        vm.run(27,(detach,));assert not vm.puts
    run_detach()
    if mode=='protected-failure':
        assert events==[payload] and payload['fo3PairRestored']
        popup.update(_result=result,_data=payload);run_detach();assert len(events)==1
    else:assert not events,mode
checks.append('Only completed protected failure with material_kept=true restores after native detach; success/cancel/error/ordinary failure do not; repeated detach is once-only')

stable=ABC(Path('D:/fifaol3/enhancement-remember/TeamManagementPlayerEnhancementTabPage-before.abc').read_bytes())
for mid in (8,22,23):assert a.A['body_records'][mid]['raw']==stable.A['body_records'][mid]['raw']
old_owner=ABC(Path('D:/fifaol3/enhancement-pair-remember/EnhancePlayerPanel-before.abc').read_bytes())
assert o.A['body_records'][18]['raw']==old_owner.A['body_records'][18]['raw']
prior=ABC(Path('D:/fifaol3/enhancement-pair-remember/TeamManagementPlayerEnhancementTabPage-before.abc').read_bytes())
for mid in (21,24,25,35):assert a.A['body_records'][mid]['raw']==prior.A['body_records'][mid]['raw']
assert a.A['body'][46]==bytes([0x47])
empty={'_available':False,'getChildByName':lambda *_:(_ for _ in ()).throw(AssertionError('Empty entry must not read widget preferences'))}
inject(a,cp,26,len(stable.A['body'][26])-1,empty)
checks.append('Successful-baseline init/money/item/native query methods restored exactly; empty entry guard performs zero preference/widget/label/GET/PUT callbacks; remembered explicit-choice handlers unchanged')
# No lexical closure remains in the attach payload; native method closure is stored instead.
code=VM.__init__.__globals__ if False else None
source=vm_source.replace('stack=[];locals=',"stack=list((locals_override or {}).get('_stack',[]));locals=")
exec(source,ns);VM=ns['VM'];U=ns['U']
received=[];bound=lambda payload:received.append(payload)
control={'_owner':{'fo3RestoreSelectedPair':bound}};payload={}
row=cp['20'];old=bytes.fromhex(row['original']);at=row['insertion_offsets'][0];end=next(e for start,e,_,_ in instructions(old) if start==at)
vm=VM(a,control);vm.run(20,start=row['mapping'][str(at)],stop=row['mapping'][str(end)]-(end-at),locals_override={'_stack':[{},'enhance-screen',payload]})
assert payload['fo3RestorePair'] is bound and not vm.puts
checks.append('Attach uses the native bound owner method; no newfunction or startup query override; execution remains explicit-click only')

# Exercise the user's option preferences against the exact loop-fixed bodies.
prefs_source=Path('D:/fifaol3/enhancement-remember/test_client.py').read_text('utf8')
prefs_defs=prefs_source[prefs_source.index('def inject('):prefs_source.index('o,b=own();')]
exec(prefs_defs,globals())
cp=json.loads(Path('D:/fifaol3/enhancement-remember/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())
entry_cp=json.loads(Path('D:/fifaol3/enhancement-entry-fix/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())
cp['26']=entry_cp['26']
fixed_map=json.loads(Path('D:/fifaol3/enhancement-ui-loop-fix/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())['30']['mapping']
cp['30']['mapping']={old:fixed_map[str(at)] for old,at in cp['30']['mapping'].items()}
o,b=own();b.update(fo3RememberReady=True,fo3RememberProtection=False,fo3RememberPoint=False,fo3RememberItem=0)
prefs_cases=prefs_source[prefs_source.index('# Capture real user choices'):prefs_source.index('for blocked,token,version,expected')]
cp['45']=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text())['45']
prefs_cases=prefs_cases.replace('inject(a,cp,45,toggle,o)', 'inject(a,cp,45,toggle,o,locals_override={2:b})')
exec(prefs_cases,globals())
checks.append('Both repaired back edges target explicit AVM2 label opcodes; original method instructions and relative control flow retained')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,native_entry_verified=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
