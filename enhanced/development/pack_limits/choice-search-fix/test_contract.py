from pathlib import Path
from unittest.mock import patch
import copy,json,os,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
sys.path[:0]=[str(S),r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels']
from avm_patch import ABC,R as Reader
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Contract regression cannot write formal files')
sys.addaudithook(audit)
old=ABC((R/'before.abc').read_bytes());new=ABC((R/'after.abc').read_bytes());checks=[]
def check(name,ok):
    assert ok,name
    checks.append(name)
def completion(a,args):
    if len(args)!=len(a.A['sig'][68]):raise TypeError('ArgumentError #1063')
    r=Reader(a.A['body'][68],0);stack=[];effects=[]
    while r.p<len(r.d):
        op=r.u8()
        if op==0x62:assert r.u30()==0;stack.append('this')
        elif op==0x30:stack.pop()
        elif op==0x5d:stack.append(a.A['mn'][r.u30()])
        elif op==0x26:stack.append(True)
        elif op==0x46:
            name=a.A['mn'][r.u30()];n=r.u30();argv=stack[-n:];del stack[-n:];owner=stack.pop()
            assert name==owner=='setSearchingComplete' and n==1;effects.append(argv);stack.append(None)
        elif op==0x29:stack.pop()
        elif op==0x47:assert not stack;return effects
        else:raise AssertionError(hex(op))
try:completion(old,[])
except TypeError as e:check('Original shipped callback deterministically reproduces zero-argument #1063',str(e)=='ArgumentError #1063')
else:raise AssertionError('Bad sample must fail')
check('Patched zero-argument completion runs original body and sets completion true exactly once',completion(new,[])==[[True]])
check('Response callback still requires its event and is byte-identical',new.A['sig'][69]==old.A['sig'][69] and len(new.A['sig'][69])==1 and new.A['body_records'][69]['raw']==old.A['body_records'][69]['raw'])
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.argv=['http_config.py']
import http_config as h
before=(S/'gamedata/state.json').read_bytes();seed=copy.deepcopy(h._state());c=h.my_coach(seed)
fn=next(fn for p,fn in h.ROUTES if p.pattern==r'/packchoice/(\d+)/search')
definitions={**h.product_packs['risk_packs'],**h.product_packs['strength_packs']}
selected={int(i):d for i,d in definitions.items() if d.get('mode')=='choice'}
for i,d in selected.items():
    c['items']=[x for x in c.get('items',[]) if x['itemid']!=i]+[dict(_id=f'memory-{i}',itemid=i,remains=1)]
with patch.object(h,'_state',side_effect=lambda:copy.deepcopy(seed)),patch.object(h,'_save',side_effect=AssertionError('Search must never write')):
    for i,d in selected.items():
        rows=json.loads(fn(str(i),'q=&league=-1&team=-1',b'')[1]);grade=next(g for g,w in enumerate(d['grades'],1) if w)
        assert {p['spid'] for p in rows}==set(d['tiers'][0]['pool']) and all(p['grade']==grade for p in rows)
        assert json.loads(fn(str(i),'q=NO_SUCH_PLAYER_709113&league=-1&team=-1',b'')[1])==[]
        assert json.loads(fn(str(i),'q=&league=invalid&team=-1',b'')[1])==[]
check('All current choice editions keep exact pool and +8/+11 grade, no-result and invalid-filter contracts',len(selected)>=13)
check('All searches complete without calling save; write audit confines evidence to this directory',True)
(R/'contract-results.json').write_text(json.dumps(dict(status='PASS',count=len(checks),checks=checks,choices=len(selected),native_verified=False,real_purchases=0,real_pack_uses=0,concurrent_real_state_changed=before!=(S/'gamedata/state.json').read_bytes()),indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',checks=len(checks),choices=len(selected))))
