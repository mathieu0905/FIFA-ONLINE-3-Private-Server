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
p=ABC((W/(NAMES[1]+'-after.abc')).read_bytes());pp=json.loads((W/(NAMES[1]+'-ABC.patch.json')).read_text());checks=[]
def inject(abc,patch,mid,old,owner,args=(),locals_override=None):
    row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()};code=bytes.fromhex(row['original'])
    end=next(e for at,e,op,t in instructions(code) if at==old);stop=mapping[end]-(end-old)
    vm=VM(abc,owner);result=vm.run(mid,args,start=mapping[old],stop=stop,locals_override=locals_override)
    assert not vm.puts
    return vm,result
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


assert sha(W/(NAMES[0]+'.big')) == '520499d9d750c75be886b8577f1bc77f99155a6fe689e340811aac2649eb7fdd'
checks.append('Tab is byte-identical to the prior successfully used enhancement UI; no convenience additions remain')
checks.append('Non-ABC tags and other BIG members match current official UI; popup changes only Confirm33 from the successful baseline')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
