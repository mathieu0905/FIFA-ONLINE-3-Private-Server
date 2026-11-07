"""Exact candidate ABC relocation/contract replay; no claim of native AVM verifier or visual QA."""
from pathlib import Path
import sys,json,struct,copy,zlib,urllib.parse,hashlib
sys.dont_write_bytecode=True
from avm_patch import ABC,R,instructions
W=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online');OUT=Path(r'D:\fifaol3\enhancement-protection40')
class Undefined:pass
U=Undefined()
def truth(x):return x is not U and bool(x)
def eq(x,y,strict=False):
    if strict:return type(x)==type(y) and x==y
    if isinstance(x,str) and isinstance(y,(int,float)):return x==str(y)
    if isinstance(y,str) and isinstance(x,(int,float)):return str(x)==y
    return x==y
class Function:
    def __init__(self,mid,owner):self.mid=mid;self.owner=owner
class VM:
    def __init__(self,a,owner):
        self.a=a;self.owner=owner;self.dialogs=[];self.puts=[];self.calls=[]
        self.globals={'undefined':U,'DialogEvent':{'OK':'ok','CANCEL':'cancel','CLOSE':'close'},'NetEvent':{'ON_COMPLETE':'complete'},
                      'StringUtil':{'formatToCurrency':lambda v:format(v,',')},'encodeURIComponent':lambda v:urllib.parse.quote(str(v),safe="~()*!.'-_")}
        self.globals['Dialog']={'BUTTON_OK':1,'BUTTON_CANCEL':2,'BUTTON_CLOSE':4,'close':lambda:self.calls.append('close'), 'showMessage':self.dialogs.append}
        self.globals['ResourceController']={'instance':{'pushPUT':self.request}}
        self.globals['TextField']=lambda:{}
        self.globals['TextFormat']=lambda font,size,color:dict(font=font,size=size,color=color)
    def request(self,uri,body):
        row={'uri':uri,'body':body};self.puts.append(row)
        req={}
        def on(event,fn,owner):row['handler']=fn;return req
        req.update(on=on,end=lambda:None);return req
    def get(self,o,k):
        if o is U or o is None:raise AssertionError('Null access '+k)
        if isinstance(o,dict):return o.get(k,U)
        if isinstance(o,(str,int,float)) and k=='toString':return lambda:str(o)
        raise AssertionError((o,k))
    def run(self,mid,arguments=(),start=0,stop=None,locals_override=None):
        code=self.a.A['body'][mid];r=R(code,start);stack=[];locals={0:self.owner,**{i+1:v for i,v in enumerate(arguments)}}
        locals.update(locals_override or {});steps=0
        while r.p<len(code):
            if r.p==stop:return 'RESUME'
            steps+=1;assert steps<3000
            at=r.p;op=r.u8()
            def pop():assert stack,(mid,at);return stack.pop()
            def name():return self.a.A['mn'][r.u30()]
            if op==0x62:stack.append(locals.get(r.u30(),U))
            elif op==0x63:locals[r.u30()]=pop()
            elif 0xd0<=op<=0xd3:stack.append(locals.get(op-0xd0,U))
            elif 0xd4<=op<=0xd7:locals[op-0xd4]=pop()
            elif op in (0x30,0x1c):pop()
            elif op in (0x09,0x1d):pass
            elif op==0x2c:stack.append(self.a.A['str'][r.u30()])
            elif op==0x2d:stack.append(self.a.A['ints'][r.u30()])
            elif op==0x24:
                x=r.u8();stack.append(x if x<128 else x-256)
            elif op==0x25:stack.append(r.u30())
            elif op==0x20:stack.append(None)
            elif op==0x21:stack.append(U)
            elif op==0x26:stack.append(True)
            elif op==0x27:stack.append(False)
            elif op==0x29:pop()
            elif op==0x2a:stack.append(stack[-1])
            elif op==0x57:stack.append({})
            elif op==0x40:stack.append(Function(r.u30(),self.owner))
            elif op==0x65:r.u8();stack.append(locals.get('_activation',{}))
            elif op==0x6c:stack.append(self.get(pop(),'_slots')[r.u30()])
            elif op in (0x5d,0x5e):
                k=name();stack.append(self.owner if k in self.owner else self.globals)
            elif op==0x60:stack.append(self.globals[name()])
            elif op==0x66:k=name();stack.append(self.get(pop(),k))
            elif op in (0x61,0x68):k=name();v=pop();o=pop();o[k]=v
            elif op in (0x46,0x4f,0x4a):
                k=name();n=r.u30();args=[pop() for _ in range(n)][::-1];obj=pop();fn=self.get(obj,k)
                if isinstance(fn,Function):result=self.run(fn.mid,args)
                else:assert callable(fn),(k,fn);result=fn(*args)
                if op in (0x46,0x4a):stack.append(result)
            elif op==0x55:
                n=r.u30();obj={}
                for _ in range(n):value=pop();key=pop();obj[key]=value
                stack.append(obj)
            elif op in (0x82,0x85,0x76):
                if op==0x76:stack.append(truth(pop()))
            elif op==0x80:r.u30()
            elif op==0x96:stack.append(not truth(pop()))
            elif op==0xa0:
                b=pop();a=pop();stack.append(str(a)+str(b) if isinstance(a,str) or isinstance(b,str) else a+b)
            elif op==0xa9:b=pop();a=pop();stack.append(a|b)
            elif op==0xa1:b=pop();a=pop();stack.append(a-b)
            elif op==0xab:b=pop();a=pop();stack.append(eq(a,b))
            elif op==0x48:return pop()
            elif op==0x47:return None
            elif 0x10<=op<=0x1a:
                off=r.s24();target=r.p+off
                if op==0x10:jump=True
                elif op in (0x11,0x12):jump=truth(pop())==(op==0x11)
                else:
                    b=pop();a=pop();equal=eq(a,b,op in (0x19,0x1a));jump=equal if op in (0x13,0x19) else not equal
                if jump:r.p=target
            else:raise AssertionError(('Unsupported replay opcode',mid,hex(op),at))
        return None

def load(name):
    d=(OUT/(name+'.swf')).read_bytes()
    offset=0x246ff if 'TabPage' in name else 0x929ae
    return ABC(d[offset:]),json.loads((OUT/(name+'-ABC.patch.json')).read_text())
def resume(patch,mid,old):
    row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()}
    original=bytes.fromhex(row['original']);updated=bytes.fromhex(row['updated'])
    end=next(e for at,e,_,_ in instructions(original) if at==old)
    # Position of preserved original instruction after its inserted prefix.
    return mapping[end]-(end-old)
def injection(vm,patch,mid,old,**kw):return vm.run(mid,start=int(patch[str(mid)]['mapping'][str(old)]),stop=resume(patch,mid,old),**kw)

results=[]
popup,pp=load('TeamManagementPlayerEnhancingPopupScreen')
info={'protection':{'version':'bp-protect-v1','fee':123456789,'total_ep':123456999,'label':'保护费123,456,789 EP；总计123,456,999 EP。失败保级，材料仍消耗。','token':'signed-url_token.test'}}
data={'firstPlayer':{'_id':'target'},'secondPlayer':{'_id':'material','spid':1},'usePoint':True,'boostItemId':1000090,'boostEventId':-1,'info':info,'_bpConfirmed':False}
owner={'_data':data,'_version':'v2_5','_restoreStep':0,'_enableBoostItem':False,'_enableGuardItem':False}
vm=VM(popup,owner)
before=vm.run(31);assert '?' not in before
injection(vm,pp,33,2);assert not vm.puts and not data['_bpConfirmed']
terms=vm.dialogs[-1];assert terms['message']==info['protection']['label'] and terms['autoSizing'] and '确认付费' in terms['okayButtonLabel']
for event in ['cancel','close']:
    vm.run(terms['buttonHandler'].mid,({'type':event},));assert not data['_bpConfirmed'] and not vm.puts
owner['onConfirmButtonClick']=lambda:vm.puts.append({'uri':vm.run(31)})
vm.run(terms['buttonHandler'].mid,({'type':'ok'},));assert data['_bpConfirmed']
uri=vm.puts[-1]['uri'];query=urllib.parse.parse_qs(urllib.parse.urlsplit(uri).query)
assert query['protection_ack']==['bp-protect-v1'] and query['protection_token']==[info['protection']['token']]
info['protection']['version']='bp-protect-v2'
assert urllib.parse.parse_qs(urllib.parse.urlsplit(vm.run(31)).query)['protection_ack']==['bp-protect-v2']
owner['_restoreStep']=1;assert vm.run(31)=='/player/enhance2.5/restore'
results.append('exact candidate bytecode: full terms dialog; cancel/close zero PUT; only explicit OK attaches exact preview token/ack; restore URI excludes token')
old=ABC((OUT/'TeamManagementPlayerEnhancingPopupScreen-before.abc').read_bytes())
for version in ['v1','v2','v2_5']:
    for step in [0,1]:
        for point in [False,True]:
            o=copy.deepcopy(owner);o['_data']['info']={};o['_data']['_bpConfirmed']=False;o['_version']=version;o['_restoreStep']=step;o['_data']['usePoint']=point
            assert VM(old,o).run(31)==VM(popup,o).run(31)
results.append('12 unprotected v1/v2/v2.5, ES and restore URI cases equal native baseline exactly')
control,cp=load('TeamManagementPlayerEnhancementTabPage');calls=[]
pending={'version':'bp-protect-v1','blocked':True,'can_restore':True,'current_grade':9,'restore_grade':10,'restore':{'price':330},'discard_uri':'/player/enhance2.5/restore/discard','discard_token':'discard_token.signed'}
panel={'_preview':{'protection':pending},'updateTextLabel':lambda:None,'onClickResetButton':lambda event:calls.append('reset')}
vm=VM(control,panel);choice=len(control.A['meth'])-4
for event in ['close']:
    vm.run(choice,({'type':event},));assert not vm.puts
vm.run(choice,({'type':'ok'},));assert vm.puts[-1]['uri']=='/player/enhance2.5/restore' and vm.puts[-1]['body']=={}
vm.puts.clear();vm.run(choice,({'type':'cancel'},));discard=vm.dialogs[-1];assert '当前失败等级保持' in discard['message']
for event in ['cancel','close']:
    vm.run(discard['buttonHandler'].mid,({'type':event},));assert not vm.puts
vm.run(discard['buttonHandler'].mid,({'type':'ok'},));assert vm.puts[-1]['uri'].startswith(pending['discard_uri']+'?')
assert urllib.parse.parse_qs(urllib.parse.urlsplit(vm.puts[-1]['uri']).query)['protection_token']==[pending['discard_token']]
pending['version']='bp-protect-v2';vm.run(discard['buttonHandler'].mid,({'type':'ok'},))
assert urllib.parse.parse_qs(urllib.parse.urlsplit(vm.puts[-1]['uri']).query)['protection_ack']==['bp-protect-v2']
vm.run(vm.puts[-1]['handler'].mid,({'body':{'result':True}},));assert calls==['reset']
results.append('pending restore bytecode: restore exact original URI; discard requires second explicit OK, signed token and dynamic v1/v2 acknowledgement; both cancel/close preserve rights; success resets selection')
# Native error callback must intercept pending data before old generic preview usage.
panel.update(_selectItem={'value':1000090},enhanceButton={'enabled':True},usePointCheckBox={'enabled':False},previewUri='/private/preview')
vm=VM(control,panel);response={'result':False,'reason':'RESTORE_PENDING','protection':pending}
injection(vm,cp,34,167,arguments=({'getData':lambda uri:response},))
assert panel['_preview']==response and panel['enhanceButton']['enabled'] is False and panel['usePointCheckBox']['enabled'] is True
assert '330 ES' in vm.dialogs[-1]['message'] and vm.dialogs[-1]['okayButtonLabel']=='按原价恢复'
assert not vm.puts
results.append('RESTORE_PENDING callback displays exact old ES quote with restore/discard labels before original preview closure; no asset request')
pending.update(can_restore=False,current_grade=20,restore_grade=10,reason='RESTORE_NO_LONGER_NEEDED')
vm=VM(control,panel);injection(vm,cp,34,167,arguments=({'getData':lambda uri:response},))
assert '+20' in vm.dialogs[-1]['message'] and '+10' in vm.dialogs[-1]['message']
assert vm.dialogs[-1]['okayButtonLabel']=='查看不可恢复原因'
vm.run(choice,({'type':'ok'},));assert not vm.puts and '没有发出恢复请求' in vm.dialogs[-1]['message']
vm.run(choice,({'type':'cancel'},));invalid_discard=vm.dialogs[-1]
vm.run(invalid_discard['buttonHandler'].mid,({'type':'cancel'},));assert not vm.puts
vm.run(invalid_discard['buttonHandler'].mid,({'type':'ok'},));assert vm.puts[-1]['uri'].startswith(pending['discard_uri']+'?')
assert not any(put['uri']=='/player/enhance2.5/restore' for put in vm.puts)
pending.pop('can_restore');vm.puts.clear();vm.run(choice,({'type':'ok'},));assert not vm.puts
results.append('real pending hazard current20 versus old restore10: no restore PUT when can_restore=false or missing; signed explicit discard remains available and cancel preserves rights')
other={'blocked':True,'reason':'RESTORE_OTHER_MANAGER','label':'该旧恢复报价属于其他经理，请切回原经理处理。'}
panel['_preview']={'result':False,'reason':'RESTORE_PENDING','protection':other};response=panel['_preview'];vm=VM(control,panel)
injection(vm,cp,34,167,arguments=({'getData':lambda uri:response},))
readonly=vm.dialogs[-1];assert readonly['message']==other['label'] and readonly['okayButtonLabel']=='知道了' and 'buttonHandler' not in readonly and not vm.puts
vm.run(choice,({'type':'cancel'},));assert not vm.puts
vm.run(invalid_discard['buttonHandler'].mid,({'type':'ok'},));assert not vm.puts
results.append('other-manager pending without restore/token is label-only with no action handler; stale discard callback after manager switch emits zero PUT')
# Protected failure end animation cannot trigger simplify auto-restore or show restore.
for simplify in [False,True]:
    owner={'_result':{'success':False,'protection':{'applied':True}},'_restoreButton':{'visible':True,'enabled':True},'setLevelInfo':lambda:None,'setEnhanceCautionLabelString':lambda s:calls.append(s),'enableQuitScreen':lambda b:None,'isSimplify':lambda:simplify}
    vm=VM(popup,owner);vm.run(18)
    assert owner['_result']['success'] is False and owner['_restoreButton']=={'visible':False,'enabled':False} and not vm.puts
    assert '主卡保级' in calls[-1]
results.append('protected failure keeps success=false, hides/disables restore and skips simplify auto-restore; explicit kept-grade/material-consumed text')
owner={'_result':{'success':False,'grade':20,'rprice':999999999,'protection':{'applied':True}},'priceResult':{'priceTextField':{}}}
draw={'grade':0};vm=VM(popup,owner)
injection(vm,pp,36,353,locals_override={'_activation':{'_slots':{1:draw}}})
assert draw['grade']==20 and owner['priceResult']['priceTextField']['text']=='999,999,999 EP' and owner['_result']['success'] is False
results.append('protected failure draw object retains grade20 and real price, without relabeling failure as success')
children={}
container={'costLabel':{'x':300,'y':100},'getChildByName':lambda n:children.get(n,U),'addChild':lambda child:children.setdefault(child['name'],child)}
panel={'textContainer':container,'_preview':None};vm=VM(control,panel)
injection(vm,cp,32,267);assert not children['bpProtectionSummary']['visible']
panel['_preview']={'protection':{'fee':9007199254740000,'total_ep':9007199254740991}}
injection(vm,cp,32,267);field=children['bpProtectionSummary']
assert field['visible'] and '9,007,199,254,740,000' in field['text'] and '9,007,199,254,740,991' in field['text']
assert field['multiline'] and field['wordWrap'] and len(children)==1
panel['_preview']=None;injection(vm,cp,32,267);assert not field['visible']
results.append('preview native TextField reused/hidden correctly; protection fee and total display full Number-safe large integers without int truncation')
# Every old instruction and branch target survives exactly apart from inserted bytes.
for a,patch in [(control,cp),(popup,pp)]:
    for mid,row in patch.items():
        oldcode=bytes.fromhex(row['original']);newcode=bytes.fromhex(row['updated']);mapping={int(k):v for k,v in row['mapping'].items()}
        newins={at:(end,op,targets) for at,end,op,targets in instructions(newcode)}
        for at,end,op,targets in instructions(oldcode):
            actual=mapping[end]-(end-at);ne,no,nt=newins[actual];assert no==op
            if targets is not None:assert nt==[mapping[t] for t in targets]
            else:assert oldcode[at:end]==newcode[actual:ne]
results.append('all original opcode operands preserved; every branch/lookupswitch target relocated to its intended original boundary/injection')
report={'status':'PASS','scope':'candidate structural + deterministic contract replay; native AVM verifier/rendering and end-to-end game interaction PENDING','checks':results,'production_modified':False}
(OUT/'客户端契约回归.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=True))

