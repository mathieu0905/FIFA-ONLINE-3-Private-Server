"""Check all IM roles, hierarchy, profile differences and rank-matched grade comparisons."""
import json,sqlite3,sys
from pathlib import Path
from build import R,S,FIELDS,constants,num,sha,save
def main():
    out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path']);report=json.loads((out/'report.json').read_text('utf8'))
    for name,value in report['outputs'].items():assert sha(out/name)==value
    rows=json.loads((out/'changes.json').read_text('utf8'));n=constants();groups={};cases=[]
    db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    target=sqlite3.connect((out/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True);target.row_factory=sqlite3.Row
    for row in rows:
        old,new,ref=row['before_row'],row['after_row'],row['reference_row'];sid=row['spid'];w=n['ROLE_WEIGHTS'][row['role']]
        assert dict(db.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==(new if '--installed' in sys.argv else old)
        assert dict(target.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==new
        assert dict(db.execute('SELECT * FROM players WHERE spid=?',(ref['spid'],)).fetchone())==ref
        assert all(old[k]==new[k] for k in old if k not in FIELDS)
        assert sid//1000000==84 and ref['spid']//1000000==12 and old['playerid']==ref['playerid']
        shifts={new[k]-ref[k] for k in FIELDS};assert shifts=={row['source_profile_shift']}
        for role in n['ROLE_WEIGHTS']:
            weights=n['ROLE_WEIGHTS'][role]
            assert num(new,weights)-num(ref,weights)==100*row['source_profile_shift']
        score=int(num(new,w)//100);peer=int(num(row['rank_peer_row'],w)//100)
        assert 21<=score-peer<=23
        assert 2<=score+24+7+5-(peer+40+15)<=4
        assert -4<=score+24+7+5-(peer+44+17)<=-2
        groups.setdefault(row['role'],[]).append(row)
        cases.append(dict(spid=sid,name=row['name'],role=row['role'],rank=row['role_rank'],rating=score,
            wins_peer18=score-peer-19,vs_peer20=score-peer-25,metadata_exact=True,source_profile_preserved=True))
    comparisons=0
    for role,group in groups.items():
        by_rank=sorted(group,key=lambda x:x['role_rank'])
        assert [x['primary_after'] for x in by_rank]==sorted((x['primary_after'] for x in group),reverse=True)
        for a in group:
            for b in group:
                if a['reference_overall']>b['reference_overall']:
                    assert a['primary_after']>=b['primary_after'],(a['name'],b['name']);comparisons+=1
    index={x['spid']:x for x in rows};pairs=[]
    for better,other in ((84037576,84031432),(84001109,84201535),(84214100,84020289),(84190043,84054050),(84238380,84051539)):
        a,b=index[better],index[other]
        assert a['primary_after']>b['primary_after'],(a['name'],b['name'])
        pairs.append(dict(first=a['name'],first_rating=a['primary_after'],second=b['name'],second_rating=b['primary_after']))
    assert len(rows)==db.execute('SELECT count(*) FROM players WHERE spid/1000000=84').fetchone()[0]
    result=dict(status='PASS',cards=len(rows),stat_checks=33*len(rows),position_checks=28*len(rows),hierarchy_pair_checks=comparisons,
        comparison_scope=report['comparison_scope'],rank_pairs=pairs,installed_checked='--installed' in sys.argv,
        builder_sha256=sha(R/'build.py'),outputs=report['outputs'],cases=cases,native_verified=False)
    save(R/('installed-tests.json' if '--installed' in sys.argv else 'tests.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}),flush=True)
if __name__=='__main__':main()
