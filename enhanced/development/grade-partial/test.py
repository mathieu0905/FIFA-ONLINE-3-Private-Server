"""Exact isolated functions: five grade tiers, six starters and best-only eligibility."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
from prepare import R,S,transform
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('grade_color_isolated_harness',Path(r'D:\fifaol3\team-bonus20\test.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
TIERS=((5,3),(9,5),(12,7),(16,9),(20,12))
def ratings(ns,grades,moments=0):
    team=h.team(moments)
    for p,g in zip(team['players'],grades):p['grade']=g
    before=copy.deepcopy(team);values,active=h.rated(ns,team);assert team==before
    bare=ns['xi_ratings'](dict(team,teamcolors=[]))
    grade_ids={x[0] for x in ns['TC_GRADE']}
    grade_only=ns['xi_ratings'](dict(team,teamcolors=[x for x in active if x['teamcolorid'] in grade_ids]))
    return {k:grade_only[k]-bare[k] for k in bare},values,active
def expected(grades,index):return max((b for g,b in TIERS if sum(x>=g for x in grades)>=6 and grades[index]>=g),default=0)
def main():
    before=(S/'http_config.py').read_bytes().decode('utf8');after=transform(before)
    old,new=h.functions(before),h.functions(after);cases=[]
    assert [(g,gs) for _,g,_,gs in new['TC_GRADE']]==[(g,[dict(count_min=6,count_max=11,boosts=[dict(type='ovr',amount=b)])]) for g,b in TIERS]
    assert len({cid for cid,_,_,_ in new['TC_GRADE']})==5
    cases.append('Only five tiers +5/+9/+12/+16/+20 give +3/+5/+7/+9/+12; supersede old grade colors')
    for grade in range(1,21):
        for count in range(12):
            grades=[grade]*count+[1]*(11-count);bonus,_,active=ratings(new,grades)
            for i in range(11):assert bonus[str(i+1)]==expected(grades,i)
            for g,b in TIERS:assert any(c['teamcolorid']==10100+g for c in active)==(grade>=g and count>=6)
            cases.append(f'Grade{grade},count{count}: threshold, fit, fixed amount, highest-only')
    mix=[16,10,20,20,20,20,10,8,11,20,16]
    bonus,_,_=ratings(new,mix)
    assert [bonus[str(i+1)] for i in range(11)]==[9,5,9,9,9,9,5,3,5,9,9]
    cases.append('Actual mixed XI: seven >=16 give +9; five >=20 fail; +20 cards inherit qualifying +16 set')
    for g,b in TIERS:
        for count in range(6,12):
            v,_,_=ratings(new,[g]*count+[1]*(11-count));assert all(v[str(i+1)]==b for i in range(count))
    cases.append('6 through 11 eligible starters have identical fixed bonus')
    team=h.team(0)
    for i,p in enumerate(team['players']):p['grade']=20 if i<5 else 1
    team['players'].append(dict(id='12',spid=93000200,grade=20,levelinfo={'level':1,'exp':0}))
    team['squad']['positions'].append(dict(id='12',spid=93000200,pos=28))
    h.bind(new,team);assert not any(x['teamcolorid']==10120 for x in new['active_teamcolors'](team))
    cases.append('Bench sixth +20 excluded')
    for g in range(1,21):
        _,a,ao=ratings(old,[g]*11,11);_,b,an=ratings(new,[g]*11,11)
        assert [c for c in ao if c['teamcolorid'] not in {x[0] for x in old['TC_GRADE']}]==[c for c in an if c['teamcolorid'] not in {x[0] for x in new['TC_GRADE']}]
    cases.append('IM feature and all non-grade active colors unchanged')
    impact=dict(scope='Current rank-matched IM base advantage16..18, same level, full grade sets and IM feature10; exclude ordinary club/nation/special differences',
        im10_grade_bonus=5,other18_grade_bonus=9,other20_grade_bonus=12,
        im10_vs_peer18_range=[16+24+5+10-(40+9),18+24+5+10-(40+9)],
        im10_vs_peer20_range=[16+24+5+10-(44+12),18+24+5+10-(44+12)])
    report=dict(status='PASS',revision='grade-five-six-v2',case_count=len(cases),cases=cases,
        before_sha256=hashlib.sha256(before.encode()).hexdigest(),proposed_sha256=hashlib.sha256(after.encode()).hexdigest(),
        transformer_sha256=hashlib.sha256((R/'prepare.py').read_bytes()).hexdigest(),mixed_xi_grades=mix,mixed_xi_grade_bonuses=bonus,
        im_balance_impact=impact,formal_files_written=False,services_restarted=False,native_verified=False)
    (R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=True))
if __name__=='__main__':main()
