"""Verify exact current-5, hierarchy preservation and all feature population boundaries."""
import ast,json,sqlite3,sys
from pathlib import Path
from build import R,S,FIELDS,constants,num,sha,save,patched_http
def groups(source):
    tree=ast.parse(source);scope={}
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_tc_groups')
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TC_MOMENTS_GROUPS' for t in n.targets))
    exec(compile(ast.Module(body=[fn,assignment],type_ignores=[]),'exact-feature-constant','exec'),scope)
    return scope['TC_MOMENTS_GROUPS']
def main():
    out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path']);report=json.loads((out/'report.json').read_text('utf8'))
    for name,value in report['outputs'].items():assert sha(out/name)==value
    before_http=(out/'http_config.before.py').read_text('utf8');after_http=(out/'http_config.py').read_text('utf8')
    assert patched_http(before_http)==after_http
    assert (S/'http_config.py').read_text('utf8')==(after_http if '--installed' in sys.argv else before_http)
    # No other source change may accompany the group values and one description.
    before_ast=ast.parse(before_http);after_ast=ast.parse(after_http)
    for before,after in zip(before_ast.body,after_ast.body):
        if ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False):continue
        assert (isinstance(before,ast.FunctionDef) and before.name=='tc_colors') or (isinstance(before,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TC_MOMENTS_GROUPS' for t in before.targets))
    assert len(before_ast.body)==len(after_ast.body)
    oldgroups,newgroups=groups(before_http),groups(after_http)
    assert [(g['count_min'],g['count_max'],g['boosts'][0]['amount']) for g in newgroups]==[(3,5,4),(6,8,6),(9,10,8),(11,11,10)]
    effect=[]
    for count in range(12):
        bonus=lambda gs:next((g['boosts'][0]['amount'] for g in gs if g['count_min']<=count<=g['count_max']),0)
        delta=-5+bonus(newgroups)-bonus(oldgroups)
        expected=-5 if count<3 else -3 if count<=5 else -2 if count<=8 else -1 if count<=10 else 0
        assert delta==expected
        effect.append(dict(im_starters=count,old_feature=bonus(oldgroups),new_feature=bonus(newgroups),net_stat_change=delta))
    rows=json.loads((out/'changes.json').read_text('utf8'));n=constants();role_groups={};cases=[]
    db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    target=sqlite3.connect((out/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True);target.row_factory=sqlite3.Row
    for row in rows:
        old,new,ref=row['before_row'],row['after_row'],row['reference_row'];sid=row['spid'];w=n['ROLE_WEIGHTS'][row['role']]
        assert dict(db.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==(new if '--installed' in sys.argv else old)
        assert dict(target.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==new
        assert all(old[k]==new[k] for k in old if k not in FIELDS)
        assert all(new[k]==old[k]-5 for k in FIELDS)
        for weights in n['ROLE_WEIGHTS'].values():assert num(new,weights)==num(old,weights)-500
        score=int(num(new,w)//100);peer=int(num(row['rank_peer_row'],w)//100)
        assert 16<=score-peer<=18
        assert 2<=score+24+7+10-(peer+40+15)<=4
        assert -4<=score+24+7+10-(peer+44+17)<=-2
        assert score+10==int(num(old,w)//100)+5
        role_groups.setdefault(row['role'],[]).append(row)
        cases.append(dict(spid=sid,name=row['name'],role=row['role'],rating=score,old_rating=int(num(old,w)//100),exact_minus5=True,metadata_exact=True,full_set_total_preserved=True))
    comparisons=0
    for role,group in role_groups.items():
        for a in group:
            for b in group:
                if a['reference_overall']>b['reference_overall']:
                    assert a['primary_after']>=b['primary_after'];comparisons+=1
    index={x['spid']:x for x in rows};pairs=[]
    for first,second in ((84037576,84031432),(84001109,84201535),(84214100,84020289),(84190043,84054050),(84238380,84051539)):
        a,b=index[first],index[second];assert a['primary_after']>b['primary_after']
        pairs.append(dict(first=a['name'],first_rating=a['primary_after'],second=b['name'],second_rating=b['primary_after']))
    assert len(rows)==db.execute('SELECT count(*) FROM players WHERE spid/1000000=84').fetchone()[0]
    result=dict(status='PASS',cards=len(rows),stat_checks=33*len(rows),position_checks=28*len(rows),hierarchy_pair_checks=comparisons,
        population_boundaries=effect,rank_pairs=pairs,installed_checked='--installed' in sys.argv,builder_sha256=sha(R/'build.py'),outputs=report['outputs'],cases=cases,native_verified=False)
    save(R/('installed-tests.json' if '--installed' in sys.argv else 'tests.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}),flush=True)
if __name__=='__main__':main()
