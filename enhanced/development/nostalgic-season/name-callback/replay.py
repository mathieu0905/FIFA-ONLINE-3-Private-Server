"""Bounded interpreter of actual old/new callback bytecode, with localization fixtures."""
from pathlib import Path
import argparse, json, re, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_levels')
from avm_patch import ABC,R,dis
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,default=ROOT/'callback-v1');args=p.parse_args();candidate=args.candidate.resolve();assert candidate.is_relative_to(ROOT)
OLD=ABC((candidate/'old.abc').read_bytes()); NEW=ABC((candidate/'new.abc').read_bytes())
init=dis(OLD.A,OLD.A['body'][OLD.A['cls'][0][4]])
CONSTANTS={}
for i,line in enumerate(init):
    if 'initproperty ' in line and i:
        match=re.search(r'push(?:byte|int) (-?\d+)',init[i-1])
        if match:CONSTANTS[line.split('initproperty ')[1]]=int(match[1])
LABELS={'FC_CUSTOM_SEASON_12':'FC传奇精选·ICON','FC_CUSTOM_SEASON_13':'现役精选','FO3_CUSTOM_SEASON_84':'传奇时刻','FC_CUSTOM_SEASON_19':'怀旧神兽'}

def run(a,method,season,name='测试球员'):
    code=a.A['body'][method]; r=R(code,0); stack=[]; loc={0:'self',1:name if method==12 else season}; captured=[];maxstack=0
    def invoke(receiver,key,args):
        if key=='getSeason':return season
        if key=='getSeasonString':return run(a,14,args[0])[0]
        if key=='callback':captured.append(args[0]);return None
        if key=='getLocalizedString':return LABELS.get(args[0],'loc:'+args[0])
        if key=='getLocalizedStringWithArgs':
            assert len(args)==3 and args[0] in ('COMMON_SEASON_PLUS_NAME_TEXT','COMMON_SEASON_PLUS_NAME_TEXT_OTHER')
            return str(args[1])+' '+str(args[2])
        if key=='slice':return receiver[args[0]:]
        raise AssertionError(('call',key,args))
    for step in range(1500):
        op=r.u8()
        if op==0x24:
            n=r.u8();stack.append(n-256 if n>=128 else n)
        elif op==0x25:stack.append(r.u30())
        elif op==0x2d:stack.append(a.A['ints'][r.u30()])
        elif op==0x2c:stack.append(a.A['str'][r.u30()])
        elif op==0x20:stack.append(None)
        elif op==0x27:stack.append(False)
        elif op==0x29:stack.pop()
        elif op==0x09:pass
        elif op==0x08:loc.pop(r.u30(),None)
        elif op in (0x62,0x63):
            index=r.u30()
            if op==0x62:stack.append(loc[index])
            else:loc[index]=stack.pop()
        elif 0xd0<=op<=0xd3:stack.append(loc[op-0xd0])
        elif 0xd4<=op<=0xd7:loc[op-0xd4]=stack.pop()
        elif op in (0x73,0x85):
            v=stack.pop();stack.append((int(v or 0) if op==0x73 else (str(v) if v is not None else None)))
        elif op==0xa0:
            b=stack.pop();x=stack.pop();stack.append(str(x)+str(b) if isinstance(x,str) or isinstance(b,str) else x+b)
        elif op in (0x5d,0x60):
            key=a.A['mn'][r.u30()];stack.append('localization' if op==0x60 and key=='Localization' else 'scope')
        elif op==0x66:
            key=a.A['mn'][r.u30()];stack.pop();stack.append('localization' if key=='Localization' else (season*1000000+37576 if key=='spid' else CONSTANTS[key]))
        elif op in (0x46,0x4c):
            key=a.A['mn'][r.u30()];n=r.u30();args=[stack.pop() for _ in range(n)][::-1];recv=stack.pop();stack.append(invoke(recv,key,args))
        elif op==0x10:
            offset=r.s24();r.p+=offset
        elif op in (0x12,0x13,0x14,0x1a):
            offset=r.s24()
            if op==0x12:condition=not stack.pop()
            else:
                b=stack.pop();x=stack.pop();condition=x==b if op==0x13 else x!=b
            if condition:r.p+=offset
        elif op==0x1b:
            base=r.p-1;default=r.s24();n=r.u30();targets=[r.s24() for _ in range(n+1)];index=stack.pop();r.p=base+(targets[index] if 0<=index<=n else default)
        elif op==0x47:
            assert not stack and len(captured)==1;return captured[0],maxstack
        elif op==0x48:
            result=stack.pop();assert not stack;return result,maxstack
        elif op==0x30:stack.pop() # pushscope for method14
        else:raise AssertionError(('unsupported opcode',hex(op),r.p-1))
        maxstack=max(maxstack,len(stack))
    raise AssertionError('Exceeded step limit')

rows=[]
for season in range(128):
    old,_=run(OLD,12,season);new,depth=run(NEW,12,season)
    if season in (19,):
        wanted=LABELS['FO3_CUSTOM_SEASON_84' if season==84 else 'FC_CUSTOM_SEASON_'+str(season)]+' 测试球员'
        assert new==wanted and old==f'{season} 测试球员'
    else:assert old==new,(season,old,new)
    assert depth<=OLD.A['body_records'][12]['fields'][0]
    rows.append(dict(season=season,before=old,after=new,maxstack=depth))
report=dict(status='ACTUAL_CALLBACK_BYTECODE_REPLAY_PASS',cases=len(rows),changed_seasons=[x['season'] for x in rows if x['before']!=x['after']],rows=rows,native_verified=False)
(candidate/'replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
