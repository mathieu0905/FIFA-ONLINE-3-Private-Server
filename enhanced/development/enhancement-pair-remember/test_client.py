from client_tools import *
import copy
# Reuse the established exact-opcode interpreter, not the previous tests.
src=Path('D:/fifaol3/enhancement-remember/test_client.py').read_text('utf8').split("a=ABC((W/")[0]
ns={'__file__':str(W/'test_client.py')};exec(src,ns);VM=ns['VM'];U=ns['U']
# Execute the original detach callback too, including cleanup between capture/restore.
vm_source=ns['source'].replace("elif op==0x65:","elif op==0x64:stack.append(self.globals)\n            elif op==0x41:\n                n=r.u30();args=[pop() for _ in range(n)][::-1];receiver=pop();fn=pop();stack.append(fn(*args))\n            elif op==0x65:")
exec(vm_source,ns);VM=ns['VM'];U=ns['U']
a=ABC((W/(NAMES[0]+'-after.abc')).read_bytes());o=ABC((W/'EnhancePlayerPanel-after.abc').read_bytes());p=ABC((W/(NAMES[1]+'-after.abc')).read_bytes())
cp=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text());op=json.loads((W/'EnhancePlayerPanel-ABC.patch.json').read_text());pp=json.loads((W/(NAMES[1]+'-ABC.patch.json')).read_text())
meta=json.loads((W/'client-build.json').read_text());callback=meta[NAMES[0]]['blocks']['control']['callbacks']['restore_callback']
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
def restore(state,payload):return inject(o,op,18,7,state,('restore protected pair',payload))
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

forward=[];control={'_owner':{'query':lambda command,payload:forward.append((command,payload))}}
vm=VM(a,control);vm.run(callback,(data,));assert forward==[('restore protected pair',data)] and not vm.puts
checks.append('Native popup data receives a scoped callback to its original control/owner; no quote/token is carried into restored selection')

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

for prefix,abc,patch in ((NAMES[0],a,cp),('EnhancePlayerPanel',o,op),(NAMES[1],p,pp)):
    old=ABC((W/(prefix+'-before.abc')).read_bytes())
    for mid,row in patch.items():
        before=bytes.fromhex(row['original']);after=abc.A['body'][int(mid)];mapping={int(k):v for k,v in row['mapping'].items()};ins={at:(e,code,t) for at,e,code,t in instructions(after)}
        for at,end,code,targets in instructions(before):
            preserved=mapping[end]-(end-at);ne,nc,nt=ins[preserved];assert nc==code
            if targets is not None:assert nt==[mapping[t] for t in targets]
            else:assert after[preserved:ne]==before[at:end]
    for mid,record in old.A['body_records'].items():
        if str(mid) not in patch:assert record['raw']==abc.A['body_records'][mid]['raw']
checks.append('All original instructions/branches and unrelated methods, previous preference memory, native confirm, signed execution/result logic remain byte-identical')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
