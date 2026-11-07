"""Replay the exact patched AVM2; no native GUI or typed-verifier claim."""
from client_tools import *
import math,types,urllib.parse
source=(T/'test_bp_client.py').read_text('utf8')
source=source[source.index('class Undefined:'):source.index('\ndef load(name):')]
source=source.replace("elif op in (0x09,0x1d):pass", "elif op in (0x09,0x1d):pass\n            elif op in (0xf0,0xf1):r.u30()\n            elif op==0xef:r.u8();r.u30();r.u8();r.u30()")
source=source.replace("elif op==0x66:k=name();stack.append(self.get(pop(),k))", "elif op==0x66:\n                k=name()\n                if k=='[late]':key=pop();obj=pop();stack.append(obj[key])\n                else:stack.append(self.get(pop(),k))")
source=source.replace("if isinstance(o,dict):return o.get(k,U)","if isinstance(o,dict):return o.get(k,U)\n        if isinstance(o,(list,tuple)) and k=='length':return len(o)")
source=source.replace("elif op==0xa9:","elif op==0xa2:b=pop();a=pop();stack.append(a*b)\n            elif op==0xa9:")
source=source.replace("elif op==0xa1:","elif op==0xa3:b=pop();a=pop();stack.append(a/b)\n            elif op==0xa1:")
source=source.replace("elif op==0x57:stack.append({})","elif op==0x57:\n                activation={'_slots':{}};locals['_activation']=activation;stack.append(activation)")
source=source.replace("elif op==0x6c:","elif op==0x6d:\n                slot=r.u30();value=pop();obj=pop();obj['_slots'][slot]=value\n            elif op==0x73:stack.append(int(pop()))\n            elif op==0x6c:")
source=source.replace("elif 0x10<=op<=0x1a:","elif 0x0c<=op<=0x1a:")
source=source.replace("b=pop();a=pop();equal=eq(a,b,op in (0x19,0x1a));jump=equal if op in (0x13,0x19) else not equal", "b=pop();a=pop();equal=eq(a,b,op in (0x19,0x1a))\n                    if op in (0x13,0x14,0x19,0x1a):jump=equal if op in (0x13,0x19) else not equal\n                    else:jump={0x0c:lambda:not(a<b),0x0d:lambda:not(a<=b),0x0e:lambda:not(a>b),0x0f:lambda:not(a>=b),0x15:lambda:a<b,0x16:lambda:a<=b,0x17:lambda:a>b,0x18:lambda:a>=b}[op]()")
env=dict(R=R,instructions=instructions,urllib=types.SimpleNamespace(parse=urllib.parse))
exec(source,env);VM=env['VM'];U=env['U']
a=ABC((W/(NAMES[0]+'-after.abc')).read_bytes());p=ABC((W/(NAMES[1]+'-after.abc')).read_bytes())
cp=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text());pp=json.loads((W/(NAMES[1]+'-ABC.patch.json')).read_text())
checks=[]
def inject(abc,patch,mid,old,owner,args=(),locals_override=None):
    row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()};code=bytes.fromhex(row['original'])
    end=next(e for at,e,op,t in instructions(code) if at==old);stop=mapping[end]-(end-old)
    vm=VM(abc,owner);result=vm.run(mid,args,start=mapping[old],stop=stop,locals_override=locals_override)
    assert not vm.puts
    return vm,result
def own():
    mark={'visible':False};caption={'text':''};box={'selected':False,'enabled':True,'_children':{'fo3ProtectionMark':mark,'fo3ProtectionCaption':caption}}
    box['getChildByName']=lambda name:box['_children'].get(name,U)
    state={'_children':{'fo3ProtectionCheckbox':box},'_available':True,'_money':{'es':1000},'_selectedTargets':[{'_id':'a','grade':9},{'_id':'b','grade':8}],
           '_selectItem':None,'usePointCheckBox':{'selected':False},'itemCombobox':{'selectedIndex':0},'requests':[]}
    state['getChildByName']=lambda name:state['_children'].get(name,U)
    state['setEsLabel']=lambda v:state.setdefault('es_labels',[]).append(v)
    state['requestPreview']=lambda:state['requests'].append((box['selected'],state['usePointCheckBox']['selected'],state['_selectItem']))
    return state,box
o,b=own();init=len(bytes.fromhex(cp['8']['original']))-1
inject(a,cp,8,init,o);assert b['fo3RememberReady'] and not b['fo3RememberProtection'] and not b['fo3RememberPoint'] and b['fo3RememberItem']==0
assert '失败双卡保留' in b['_children']['fo3ProtectionCaption']['text']
# Capture real user choices by executing the inserted operand paths.
b['selected']=True
toggle=cp['45']['insertion_offsets'][0];inject(a,cp,45,toggle,o)
o['usePointCheckBox']['selected']=True;inject(a,cp,21,109,o)
o['_selectItem']={'value':1000052,'label':'gold'};inject(a,cp,24,52,o)
assert b['fo3RememberProtection'] and b['fo3RememberPoint'] and b['fo3RememberItem']==1000052
checks.append('Explicit protection/ES/gold choices captured in current-page memory; first entry stays unselected')

def restore_items(rows,programmatic=False):
    o['_selectItem']=None;o['itemCombobox']['selectedIndex']=0
    def select(arr,index):
        VM(a,o).run(29,(arr,index))  # Original native selection logic.
        if programmatic:inject(a,cp,24,52,o)
    o['selectDefaultBoostItem']=select
    inject(a,cp,30,7,o)
    if programmatic:
        o['_selectItem']=None;inject(a,cp,24,52,o)
        assert b['fo3RememberItem']==1000052,'Native list rebuild must not erase preference'
    inject(a,cp,30,327,o,locals_override={2:rows})

for attempt in range(5):
    # These are precisely the reset operations emitted by original updateSelectedTarget/buttons/list rebuild.
    b['selected']=False;b['_children']['fo3ProtectionMark']['visible']=False;o['usePointCheckBox']['selected']=False;o['_selectItem']=None
    inject(a,cp,25,567,o,([o['_selectedTargets'][0],o['_selectedTargets'][1]],))
    restore_items([{'value':0,'label':'none'},{'value':1000053,'label':'silver'},{'value':1000052,'label':'gold'}],programmatic=True)
    inject(a,cp,35,50,o)
    assert b['selected'] and b['_children']['fo3ProtectionMark']['visible'] and o['usePointCheckBox']['selected']
    assert o['_selectItem']['value']==1000052 and o['itemCombobox']['selectedIndex']==2
    # Pending preview/coin events cannot clear remembered ES behind the in-flight URI.
    o['usePointCheckBox']['selected']=False;inject(a,cp,26,364,o);assert o['usePointCheckBox']['selected']
checks.append('Five failed-attempt return/list rebuild cycles retain protection/gold/ES; native default selection events are suppressed from memory; pending preview reset repaired')

restore_items([{'value':0,'label':'none'},{'value':1000053,'label':'silver'}]);assert o['_selectItem'] is None and o['itemCombobox']['selectedIndex']==0
assert b['fo3RememberItem']==1000052
restore_items([{'value':0,'label':'none'},{'value':1000052,'label':'gold'}]);assert o['_selectItem']['value']==1000052
o['_money']['es']=99;inject(a,cp,35,50,o);assert not o['usePointCheckBox']['selected'] and b['fo3RememberPoint']
o['_money']['es']=100;inject(a,cp,35,50,o);assert o['usePointCheckBox']['selected']
o['_money']=None;inject(a,cp,35,50,o);assert not o['usePointCheckBox']['selected']
o['_money']={'es':1000}
checks.append('Exhausted/ineligible remembered coupon falls back to none without substitution; restocked same ID restores; ES shortage/absent wallet is unchecked and restores when affordable')

b['selected']=False;inject(a,cp,45,toggle,o);o['usePointCheckBox']['selected']=False;inject(a,cp,21,109,o)
o['_selectItem']=None;inject(a,cp,24,52,o)
inject(a,cp,25,567,o,([{},{}],));restore_items([{'value':0},{'value':1000052}]);inject(a,cp,35,50,o)
assert not b['selected'] and not o['usePointCheckBox']['selected'] and o['_selectItem'] is None
b.update(fo3RememberProtection=True,fo3RememberPoint=True,fo3RememberItem=1000052)
inject(a,cp,18,7,o);assert not b['fo3RememberProtection'] and not b['fo3RememberPoint'] and b['fo3RememberItem']==0
checks.append('Manual uncheck/none selections persist; explicit Reset clears all remembered options')

for blocked,token,version,expected in ((False,'signed-token','protection40-v3-both',True),(True,'signed-token','v3',False),(False,None,'v3',False),(False,'signed-token',None,False)):
    data={'info':{'protection':{'blocked':blocked,'token':token,'version':version}}}
    pop={'_data':data};vm,result=inject(p,pp,33,2,pop)
    assert data.get('_bpConfirmed',False)==expected and not vm.dialogs and not vm.puts
checks.append('Extra fee-dialog bypass applies only when native Confirm is clicked with a current signed nonblocked quote; it never submits payment by itself')

data={'firstPlayer':{'_id':'main'},'secondPlayer':{'_id':'material','spid':1},'usePoint':True,'boostItemId':1000052,'boostEventId':-1,
      'info':{'protection':{'version':'protection40-v3-both','token':'fresh-token'}},'_bpConfirmed':False}
pop={'_data':data,'_version':'v2_5','_restoreStep':0,'_enableBoostItem':False,'_enableGuardItem':False}
inject(p,pp,33,2,pop)
uri=VM(p,pop).run(31);query=urllib.parse.parse_qs(urllib.parse.urlsplit(uri).query)
assert '/1/1000052/-1?' in uri and query['protection_ack']==['protection40-v3-both'] and query['protection_token']==['fresh-token']
checks.append('Native execution URI still binds current points, chosen coupon, protection version and fresh token; no old token or quote is remembered')
pop.update(confirmButton={},cancelButton={},textContainer=None,boostInfoPanel=None,container={'gotoAndPlay':lambda _:None},titleContainer={},enableQuitScreen=lambda _:None,setEnhanceCautionLabelString=lambda _:None)
data['resultCallback']=lambda *_:None
data['samePlayers']=[data['firstPlayer'],data['secondPlayer']]
pop['_self']=pop
pop['getURI']=lambda:VM(p,pop).run(31)
data['_bpConfirmed']=False
native_confirm=VM(p,pop);native_confirm.globals['Localization']={'getLocalizedString':lambda key:key};native_confirm.run(33)
assert not native_confirm.dialogs and len(native_confirm.puts)==1
assert 'protection_token=fresh-token' in native_confirm.puts[0]['uri']
checks.append('Full native Confirm handler executes one signed PUT and zero extra dialogs; only clicking native Confirm invokes it')

for name,abc,patch in ((NAMES[0],a,cp),(NAMES[1],p,pp)):
    before=ABC((W/(name+'-before.abc')).read_bytes())
    for mid,row in patch.items():
        old=bytes.fromhex(row['original']);new=abc.A['body'][int(mid)];mapping={int(k):v for k,v in row['mapping'].items()};ins={at:(e,op,t) for at,e,op,t in instructions(new)}
        for at,end,op,targets in instructions(old):
            preserved=mapping[end]-(end-at);ne,no,nt=ins[preserved];assert no==op
            if targets is not None:assert nt==[mapping[t] for t in targets]
            else:assert new[preserved:ne]==old[at:end]
    for mid in ((20,34,36,38) if name==NAMES[0] else (18,31,32,36,37,63)):
        assert before.A['body_records'][mid]['raw']==abc.A['body_records'][mid]['raw']
checks.append('All original instructions/branches preserved; stale-response filter, native confirm, signed payment/restore/result handlers and numeric/font rendering stay intact')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
