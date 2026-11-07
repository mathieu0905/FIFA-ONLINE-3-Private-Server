"""Build the batch page from the current native page, using a bound instance handler.

No anonymous newfunction or Function.call is used for quantity events or refreshes.
All screen fields are resolved directly against local0, the actual instance.
"""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
sys.path.insert(0,str(W))
import build_client as b
from avm_patch import ABC,Code,R,u30,instructions
OUT=Path(__file__).parent/'batch-bound-v1';OUT.mkdir(exist_ok=True)
old=Path('D:/FO3QA/experience30_release/plus-minus-preparation-v1/build_candidate.py').read_text('utf8')
# Reuse only the reviewed product calculation and patch generation functions.
defs=old[old.index('lex,owner,capsule,field='):old.index("g=b.bigdir.read(ORIGINAL")]
ns=dict(b=b,Path=Path,Code=Code,ABC=ABC)
exec(compile(defs,'<reviewed batch product logic>','exec'),ns)
def owner(c):return c.local(0)
def capsule(c):return owner(c).ownprop('_capsuleData')
def field(c,name):
    return owner(c).ownprop('guideText') if name=='fo3ExpSummary' else owner(c).string(name).call('getChildByName',1)
def refresh(c,mid):return c.local(0).op(0x20).call('fo3BatchRefresh',1).op(0x29)
for n,f in [('owner',owner),('capsule',capsule),('field',field),('emit_refresh',refresh)]:
    ns[n]=f;setattr(b,n,f)
# Listener closures use the same bound method trait as stock onPlayerClicked.
orig_op=Code.op
def bound_op(self,n,*args):
    if n==0x40 and args==(32,):
        return orig_op(self,0x62,0).op(0x66,self.a.name('fo3BatchRefresh'))
    return orig_op(self,n,*args)
Code.op=bound_op
original_add=ABC.add_method
def add_method(self,code,scope,local_count=2):
    assert len(self.A['meth'])==32
    return original_add(self,code,self.A['body_records'][5]['fields'][2],local_count)
ABC.add_method=add_method

source=Path('D:/FO3ID/32795/data/ui/TeamManagementExpCapsuleScreen.big')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8'
member='data/ui/TeamManagementExpCapsuleScreen.gfx'
g=b.bigdir.read(source,member);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:])
start=8+(5+4*(swf[8]>>3)+7)//8+4

def skip_traits(r):
    at=r.p;n=r.u30();entries=r.p
    for _ in range(n):
        r.u30();k=r.u8();kind=k&15
        if kind in (0,6):
            r.u30();r.u30();v=r.u30()
            if v:r.u8()
        elif kind in (1,2,3,4,5):r.u30();r.u30()
        else:raise ValueError(kind)
        if k&64:
            for _ in range(r.u30()):r.u30()
    return at,entries,n,r.p

def bind(data,mn):
    a=ABC(data);r=R(data,a.A['method_end'])
    for _ in range(r.u30()):
        r.u30()
        for _ in range(r.u30()*2):r.u30()
    nc=r.u30();hit=None
    for _ in range(nc):
        name=r.u30();r.u30();flags=r.u8()
        if flags&8:r.u30()
        for _ in range(r.u30()):r.u30()
        r.u30();rec=skip_traits(r)
        if a.A['mn'][name]=='ExpCapsuleSelectingPage':hit=rec
    assert hit
    cp,entries,n,end=hit
    trait=u30(mn)+b'\x01'+u30(0)+u30(32)
    return data[:cp]+u30(n+1)+data[entries:end]+trait+data[end:]

parts=[]
for kind,body,raw in b.tags(swf,start):
    if kind==82:
        pos=body.index(0,4)+1
        if swf.find(body)+pos==0x11186:
            a=ABC(body[pos:]);mn=a.name('fo3BatchRefresh');ids=b.capsule_patch(a)
            changed=bind(a.output(),mn);checked=ABC(changed)
            assert ('method','fo3BatchRefresh',32) in checked.A['cls'][0][3]
            for mid in (5,6,10,11,15,18,32):
                assert not any(op==0x40 and R(checked.A['body'][mid],at+1).u30()==32 for at,_,op,_ in instructions(checked.A['body'][mid]))
            (OUT/'methods.json').write_text(json.dumps({str(mid):'\n'.join(b.dis(checked.A,checked.A['body'][mid])) for mid in (5,6,10,11,15,18,32)},ensure_ascii=False,indent=2),'utf8')
            raw=b.tag(kind,body[:pos]+changed)
    parts.append(raw)
new=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
target=OUT/source.name;target.write_bytes(source.read_bytes())
b.ordered_big.replace_member(target,member,b'CFX'+new[3:8]+zlib.compress(new[8:],9),0)
assert zlib.decompress(b.bigdir.read(target,member)[8:])==new[8:]
(OUT/'page.swf').write_bytes(new)
print(json.dumps(dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),handler_fields=checked.A['body_records'][32]['fields'])))
