"""Exact operand/scope stack-height dataflow. Does not replace the native typed verifier."""
from pathlib import Path
import json,sys
sys.dont_write_bytecode=True
from avm_patch import ABC,R,instructions
ROOT=Path(r'D:\fifaol3\enhancement-progression')

def check(a,mid):
    code=a.A['body'][mid];ins={at:(end,op,targets) for at,end,op,targets in instructions(code)}
    maxstack,locals_count,initial,maxscope=a.A['body_records'][mid]['fields']
    queue=[(0,0,initial)];seen={};peak=0
    while queue:
        at,height,scope=queue.pop()
        if at in seen:
            assert seen[at]==(height,scope),(mid,at,'join',seen[at],(height,scope));continue
        seen[at]=(height,scope);end,op,targets=ins[at];r=R(code,at+1);pops=pushes=0;scope_delta=0
        def operand():return r.u30()
        def runtime_name(index):
            kind=a.values[6][index][0]
            return 2 if kind in (0x11,0x12) else 1 if kind in (0xf,0x10,0x1b,0x1c) else 0
        if op in (0x20,0x21,0x24,0x25,0x26,0x27,0x28,0x2c,0x2d,0x40,0x57,0x62,0x65,0xd0,0xd1,0xd2,0xd3):pushes=1
        elif op==0x2a:pops=1;pushes=2
        elif op==0x29:pops=1
        elif op in (0x63,0xd4,0xd5,0xd6,0xd7):pops=1
        elif op==0x30:pops=1;scope_delta=1
        elif op==0x1d:scope_delta=-1
        elif op in (0x5d,0x5e,0x60):pops=runtime_name(operand());pushes=1
        elif op==0x66:pops=1+runtime_name(operand());pushes=1
        elif op in (0x61,0x68):pops=2+runtime_name(operand())
        elif op==0x6c:pops=1;pushes=1
        elif op==0x6d:pops=2
        elif op in (0x46,0x4a,0x4f):
            mn=operand();n=operand();pops=1+n+runtime_name(mn);pushes=0 if op==0x4f else 1
        elif op==0x55:pops=operand()*2;pushes=1
        elif op in (0x73,0x76,0x80,0x82,0x85,0x90,0x96):pops=1;pushes=1
        elif op in (0xa0,0xa1,0xa3,0xa9,0xab,0xaf,0xb0):pops=2;pushes=1
        elif op in (0x11,0x12):pops=1
        elif 0xc<=op<=0x1a and op!=0x10:pops=2
        elif op==0x1b:pops=1
        elif op==0x48:pops=1
        elif op not in (0x08,0x09,0x10,0x47,0xef,0xf0,0xf1):raise AssertionError(('Unhandled stack opcode',hex(op)))
        assert height>=pops,(mid,at,'underflow',height,pops)
        height+=pushes-pops;scope+=scope_delta;peak=max(peak,height)
        assert 0<=height<=maxstack and initial<=scope<=maxscope,(mid,at,height,scope,maxstack,maxscope)
        if op in (0x47,0x48):continue
        successors=targets if op in (0x10,0x1b) else ([end]+(targets or []))
        for target in successors:
            assert target in ins,(mid,at,target)
            queue.append((target,height,scope))
    return dict(reachable_instructions=len(seen),maximum_stack_observed=peak,declared_stack=maxstack)

results={}
for name,offset in [('TeamManagementPlayerEnhancementTabPage',0x246ff),('TeamManagementPlayerEnhancingPopupScreen',0x929ae)]:
    a=ABC((ROOT/(name+'.swf')).read_bytes()[offset:]);patch=json.loads((ROOT/(name+'-ABC.patch.json')).read_text())
    original=ABC((ROOT/(name+'-before.abc')).read_bytes())
    mids=sorted(set(map(int,patch))|set(range(len(original.A['meth']),len(a.A['meth']))))
    results[name]={str(mid):check(a,mid) for mid in mids}
report=dict(status='PASS',scope='operand/scope stack heights and branch joins only; native type verifier pending',methods=results)
(ROOT/'栈与分支回归.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True))
