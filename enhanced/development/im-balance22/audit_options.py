"""Read-only review of IM hierarchy and the conflicting balance constraints."""
from pathlib import Path
import ast, collections, hashlib, json, sqlite3
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    scope={};tree=ast.parse((S/'http_config.py').read_text('utf8'))
    for name in ('ROLE_WEIGHTS','POS_ROLE'):
        n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
        exec(compile(ast.Module(body=[n],type_ignores=[]),'read-only-weights','exec'),scope)
    db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    allrows=[dict(p) for p in db.execute('SELECT * FROM players WHERE spid>=1000000')]
    refs={p['playerid']:p for p in allrows if p['spid']//1000000==12};names=dict(db.execute('SELECT playerid,short_eng FROM nameschi'))
    bypid=collections.defaultdict(list)
    for p in allrows:bypid[p['playerid']].append(p)
    rows=[]
    for p in allrows:
        if p['spid']//1000000!=84:continue
        ref=refs[p['playerid']];role=scope['POS_ROLE'][p['preferredposition1']];w=scope['ROLE_WEIGHTS'][role]
        score=lambda x:sum(x[k]*v for k,v in w.items())//100
        best=max((x for x in bypid[p['playerid']] if x['spid']//1000000!=84),key=lambda x:(score(x),x['spid']))
        other=score(best);tier=ref['overallrating'];desired=tier+25
        strict=min(other+24,max(other+20,desired))
        row=dict(spid=p['spid'],name=names[p['playerid']],role=role,current_plus30_primary=score(p),
            simple_plus22_primary=score(p)-8,reference_spid=ref['spid'],reference_overall=tier,other_best_spid=best['spid'],other_primary=other,
            strict_same_player=dict(target_primary=strict,im10_vs_other18=strict-other-19,im10_vs_other20=strict-other-25),
            hierarchy_first=dict(target_primary=desired,im10_vs_other18=desired-other-19,im10_vs_other20=desired-other-25))
        assert row['strict_same_player']['im10_vs_other18']>0 and row['strict_same_player']['im10_vs_other20']<0
        rows.append(row)
    conflicts=[]
    for a in rows:
        for b in rows:
            if a['role']==b['role'] and a['reference_overall']>b['reference_overall'] and a['other_primary']+24<b['other_primary']+20:
                conflicts.append(dict(higher_reference=a['name'],lower_reference=b['name'],role=a['role'],
                    higher_reference_max_allowed=a['other_primary']+24,lower_reference_min_allowed=b['other_primary']+20))
    cases=[]
    for x,y in ((84037576,84031432),(84001109,84201535),(84214100,84020289),(84190043,84054050),(84238380,84051539)):
        a=next(r for r in rows if r['spid']==x);b=next(r for r in rows if r['spid']==y)
        cases.append(dict(first=a,second=b))
    report=dict(status='OPTIONS_PREPARED_AWAITING_HIERARCHY_PRIORITY_NOT_INSTALLED',cards=len(rows),
        reference_policy='Existing local FC ICON season-12 overall ratings provide a common design reference, not an objective football ranking; targets here are proposals.',
        hard_constraint='Same level; IM10 full grade set +7 plus feature +5; other18 set +15, other20 set +17. Original club/nation/special differences excluded.',
        source_hashes={str(p):sha(p) for p in (S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'http_config.py')},
        strict_same_player_infeasible_reference_order_pairs=conflicts,examples=cases,rows=rows,
        formal_files_written=False,services_restarted=False,state_shop_written=False)
    (R/'review-options.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(cards=len(rows),unavoidable_reference_order_conflicts=conflicts,
        hierarchy_first_fails_same_player_win18=[r['name'] for r in rows if r['hierarchy_first']['im10_vs_other18']<=0],
        hierarchy_first_fails_same_player_lose20=[r['name'] for r in rows if r['hierarchy_first']['im10_vs_other20']>=0]),ensure_ascii=True))
if __name__=='__main__':main()
