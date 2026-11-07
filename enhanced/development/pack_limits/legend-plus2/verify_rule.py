from pathlib import Path
import copy,hashlib,json,os,sys,types
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.dont_write_bytecode=True
sys.path.insert(0,str(S));os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Rule verification cannot write outside its evidence directory')
sys.addaudithook(audit)
prepared='--prepared' in sys.argv
# argv is deliberately reset for http_config's port parser; choose via environment.
prepared=os.environ.get('FO3_VERIFY_PREPARED')=='1'
if prepared:
    h=types.ModuleType('http_config');h.__file__=str(S/'http_config.py');sys.modules['http_config']=h
    exec(compile((R/'http_config.py').read_bytes(),h.__file__,'exec'),h.__dict__)
else:
    import http_config as h
before=json.loads((R/'before-teamcolor-sets.json').read_text(encoding='utf8'))
now=h.tc_special_sets();cards,_=h.tc_static();nostalgia={s for s in cards if s//1000000==19};checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
check('All 88 nostalgia cards join the original legend membership',len(nostalgia)==88 and now[20043][0]==frozenset(before['20043'])|nostalgia)
check('Every other team-color membership is unchanged',set(map(str,now))==set(before) and all(sorted(value[0])==before[str(cid)] for cid,value in now.items() if cid!=20043))
color=next(c for c in h.tc_colors() if c['teamcolorid']==20043)
check('Original 5/7/9 tiers all give +2, with native string teamid',[(g['count_min'],g['count_max'],g['boosts']) for g in color['boostgroups']]==[(5,6,[dict(type='ovr',amount=2)]),(7,8,[dict(type='ovr',amount=2)]),(9,11,[dict(type='ovr',amount=2)])] and color['teamid']=='20043')
def unique(pool):
    out=[];seen=set()
    for s in sorted(pool):
        if cards[s][0] not in seen:out.append(s);seen.add(cards[s][0])
    return out
new=unique(nostalgia);old=unique(now[20043][0]-nostalgia)
def team(spids):
    players=[dict(_id=f'memory-{i}',spid=s,grade=1) for i,s in enumerate(spids)]
    return dict(players=players,squad=dict(positions=[dict(id=p['_id'],spid=p['spid'],pos=i) for i,p in enumerate(players)]))
for count,tier,boost in [(4,None,0),(5,0,2),(7,1,2),(9,2,2)]:
    for label,pool in [('nostalgia',new[:count]),('mixed',old[:2]+new[:count-2])]:
        t=team(pool);active=[c for c in h.active_teamcolors(t) if c['teamcolorid']==20043]
        check(f'{label} XI count {count} uses original tier',active==([] if tier is None else [dict(teamcolorid=20043,boostindex=tier,teamid='20043')]))
        t['teamcolors']=active;boosted=h.xi_ratings(t);bare=h.xi_ratings(dict(t,teamcolors=[]))
        check(f'{label} XI count {count} receives exact OVR +{boost}',all(boosted[i]-bare[i]==boost for i in bare))
t=team(new[:4]+new[:1]);check('Duplicate player identity does not reach five',not any(c['teamcolorid']==20043 for c in h.active_teamcolors(t)))
t=team(new[:5]);t['squad']['positions'][-1]['pos']=h.POS_SUB
check('Bench player does not count toward legend XI',not any(c['teamcolorid']==20043 for c in h.active_teamcolors(t)))
report=dict(status='PASS',mode='prepared_source_no_service' if prepared else 'formal_source',checks=checks,count=len(checks),nostalgia_cards=len(nostalgia),legend_members=len(now[20043][0]),formal_state_written=False)
(R/('prepared-rule-results.json' if prepared else 'rule-results.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',count=len(checks),nostalgia_cards=len(nostalgia))))
