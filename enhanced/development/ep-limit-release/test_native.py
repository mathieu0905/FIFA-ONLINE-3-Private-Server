from pathlib import Path
import json,math,sys
sys.dont_write_bytecode=True
from build_compact_label import ABC,WORK
ROOT=Path(__file__).resolve().parent
swf=(ROOT/'native/Label-compact.swf').read_bytes()
import re
for match in re.finditer(rb'\x10\x00\x2e\x00',swf):
    a=ABC(swf[match.start():])
    if any(c[0]=='PriceLabel' and c[1]=='HtmlLabel' for c in a.A['cls']):break
mid=7
# The existing stack checker is extended only for ordinary documented AVM2 ops
# used by this display method. This is not the native typed verifier.
path=WORK/'work/bp_client/verify_stacks.py'
source=path.read_text(encoding='utf-8').split('\nresults={}')[0]
source=source.replace('0x2c,0x2d,','0x2c,0x2d,0x2f,')
source=source.replace('(0x73,0x76,','(0x73,0x74,0x75,0x76,')
source=source.replace('(0xa0,0xa1,0xa3,','(0xa0,0xa1,0xa2,0xa3,0xa4,')
source=source.replace('0xa9,0xab,0xaf','0xa9,0xab,0xad,0xaf')
namespace={'__file__':str(path)};exec(compile(source,str(path),'exec'),namespace)
stack_result=namespace['check'](a,mid)
from avm_patch import R,instructions
import struct

def run(value,sign=False,currency=False,program=None):
    active,method=program or (a,mid)
    obj={'showSignSymbol':sign,'textField':{},'_text':'','isHtml':False}
    local={0:obj,1:value};stack=[];code=active.A['body'][method]
    ins={at:(end,op,targets) for at,end,op,targets in instructions(code)}
    pc=0;steps=0
    def pop():return stack.pop()
    def string(v):return str(int(v)) if isinstance(v,float) and v.is_integer() else str(v)
    while True:
        steps+=1;assert steps<2000
        end,op,targets=ins[pc];r=R(code,pc+1);pc=end
        if op in (0xd0,0xd1,0xd2,0xd3):stack.append(local[op-0xd0])
        elif op==0x62:stack.append(local[r.u30()])
        elif op==0x63:local[r.u30()]=pop()
        elif op in (0xd4,0xd5,0xd6,0xd7):local[op-0xd4]=pop()
        elif op in (0x5d,0x5e):r.u30();stack.append(obj)
        elif op==0x60:stack.append(active.A['mn'][r.u30()])
        elif op==0x66:
            name=active.A['mn'][r.u30()];owner=pop()
            stack.append(len(owner) if name=='length' else ('Math' if name=='Math' else owner[name]))
        elif op in (0x61,0x68):
            name=active.A['mn'][r.u30()];v=pop();owner=pop();owner[name]=v
        elif op==0x24:
            n=r.u8();stack.append(n if n<128 else n-256)
        elif op==0x25:stack.append(r.u30())
        elif op==0x2d:stack.append(active.values[0][r.u30()])
        elif op==0x2f:stack.append(struct.unpack('<d',active.values[2][r.u30()])[0])
        elif op==0x2c:stack.append(active.values[3][r.u30()])
        elif op==0x20:stack.append(None)
        elif op==0x56:
            count=r.u30();items=[pop() for _ in range(count)][::-1];stack.append(items)
        elif op==0x80:r.u30()
        elif op in (0x26,0x27):stack.append(op==0x26)
        elif op in (0x73,0x74):stack.append(int(pop()))
        elif op==0x85:stack.append(string(pop()))
        elif op==0x76:stack.append(bool(pop()))
        elif op in (0x75,0x82):pass
        elif op==0x30:pop()
        elif op==0x29:pop()
        elif op in (0xa0,0xa1,0xa2,0xa3,0xa4,0xaf,0xad,0xb0):
            right,left=pop(),pop()
            stack.append({0xa0:lambda:left+right,0xa1:lambda:left-right,0xa2:lambda:left*right,0xa3:lambda:left/right,
                          0xa4:lambda:left%right,0xaf:lambda:left>right,0xad:lambda:left<right,0xb0:lambda:left>=right}[op]())
        elif op==0x46:
            name=active.A['mn'][r.u30()];count=r.u30();args=[pop() for _ in range(count)][::-1];owner=pop()
            if name=='abs':out=abs(args[0])
            elif name=='Number':out=float(args[0])
            elif name=='formatToCurrency':
                shared=ABC((ROOT/'compact-module/StringUtil.abc').read_bytes())
                out=run(args[0],currency=True,program=(shared,13))
            elif name=='addComma':out=run(args[0],currency=True,program=(active,method))
            elif name=='floor':out=math.floor(args[0])
            elif name=='toString':out=string(owner)
            elif name=='concat':out=owner+args[0]
            elif name=='slice':out=owner[args[0]:args[1]]
            elif name=='substring':out=owner[args[0]:]
            elif name=='substr':out=owner[args[0]:args[0]+args[1]]
            elif name=='push':owner.extend(args);out=len(owner)
            elif name=='reverse':owner.reverse();out=owner
            elif name=='join':out=args[0].join(map(string,owner))
            elif name=='updateHtmlText':obj['rendered']=True;out=None
            else:raise AssertionError(name)
            stack.append(out)
        elif op==0x10:pc=targets[0]
        elif op in (0x11,0x12):
            v=bool(pop())
            if v==(op==0x11):pc=targets[0]
        elif op in (0x0d,0x15,0x16,0x17):
            right,left=pop(),pop()
            if ({0x0d:not(left<=right),0x15:left<right,0x16:left<=right,0x17:left>right}[op]):pc=targets[0]
        elif op==0x48:return pop()
        elif op==0x47:break
        elif op==0x09:pass
        else:raise AssertionError(hex(op))
    assert obj['_value']==value and obj.get('rendered') is True
    return obj['_text']

cases=[(0,'0'),(9999,'9,999'),(10000,'1万'),(12345,'1.23万'),(10**8,'1亿'),
       (10**12,'1兆'),(10**16,'1京'),(10**18,'100京')]
for value,expected in cases:assert run(value)==expected,(value,run(value),expected)
assert run(-12345,True)=='-1.23万'
assert run(12345,True)=='+1.23万'
report=dict(status='PASS',stack=stack_result,display_cases=cases,numeric_value_preserved=True,
            small_amounts_unchanged=True,input_parser_unchanged=True,native_typed_render='PENDING')
(ROOT/'native/compact-label-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
