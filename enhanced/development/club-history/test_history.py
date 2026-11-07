"""Exercise the actual production team-colour functions without loading service hooks."""
from pathlib import Path
from contextlib import closing
import ast,functools,json,sqlite3,sys,tempfile
sys.dont_write_bytecode=True
import build

def run(database):
    results=[]
    old=[(11,2003,2009,0),(243,2009,-1,0)]
    incoming=[(11,2003,2009,0),(243,2009,2018,0),(45,2018,2021,0),(11,2021,2022,0),(112139,2023,-1,0)]
    merged=build.merge(old,incoming)
    assert (243,2009,-1,0) not in merged and (243,2009,2018,0) in merged
    assert sum(x[0]==11 for x in merged)==2
    assert build.merge(merged,incoming)==merged
    assert set(old[:1])<=set(merged)
    assert (99,1998,1999,0) in build.merge([(99,1998,1999,0)],incoming)
    results+=['Repeated club spells preserved','Stale ongoing year corrected','Import is idempotent','Source omission does not remove an old club']
    loan=build.merge([],[(47,2010,2011,1),(47,2011,2012,0)])
    assert len(loan)==2 and loan[0][-1]==1 and loan[1][-1]==0
    results.append('Loan spell and permanent spell stay distinct')
    tree=ast.parse((build.SERVER/'http_config.py').read_text('utf8'))
    names={'_tc_groups','tc_static','_tc_tier','active_teamcolors'}
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    env=dict(functools=functools,closing=closing,TC_CLUB=17,TC_NATION=131,POS_SUB=28,
             TC_GRADE=(),tc_special_sets=lambda:{},tc_colors=lambda:[],iid=lambda p:p['id'],grade_of=lambda p:p.get('grade',1))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'production-http-teamcolor','exec'),env)
    env['TC_CLUB_GROUPS']=env['_tc_groups']((4,5,1),(6,7,2),(8,9,3),(10,11,4))
    env['TC_GROUPS']=env['_tc_groups']((5,6,1),(7,8,2),(9,11,3))
    env['_db']=lambda:sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True)
    cards,hist=env['tc_static']()
    for pid,expected in [(20801,{237,11,243,45,112139}),(158023,{241,73}),(41236,{11,47,44,45,241,73})]:
        assert expected<=hist.get(pid,set()),(pid,hist.get(pid))
        for spid,row in cards.items():
            if row[0]==pid: assert expected<=({row[1]}|hist[pid])
    results.append('Ronaldo, Messi and Ibrahimovic histories apply to every existing season card')
    # Pick four distinct players whose card club is elsewhere, but whose new
    # historical club is Manchester United. The unchanged production function
    # must now activate that club colour without changing any card's teamid.
    selected={}
    for spid,(pid,club,nation) in cards.items():
        if 11 in hist.get(pid,set()) and club not in (0,11):selected.setdefault(pid,spid)
        if len(selected)==4:break
    assert len(selected)==4
    positions=[dict(id=str(i),spid=s,pos=i+1) for i,s in enumerate(selected.values())]
    team=dict(players=[dict(id=p['id'],spid=p['spid'],grade=1) for p in positions],squad=dict(positions=positions))
    output=env['active_teamcolors'](team)
    assert dict(teamcolorid=17,boostindex=0,teamid=11) in output
    # Duplicate season cards of one person must not satisfy the four-player tier.
    pid=next(iter(selected));spids=[s for s,r in cards.items() if r[0]==pid][:4]
    repeated=[dict(id=str(i),spid=s,pos=i+1) for i,s in enumerate(spids)]
    team=dict(players=[dict(id=p['id'],spid=p['spid'],grade=1) for p in repeated],squad=dict(positions=repeated))
    assert not any(x['teamcolorid']==17 for x in env['active_teamcolors'](team))
    results+=['Four former Manchester United players activate the real production club tier','Duplicate seasons of one person do not inflate club counts']
    out=dict(status='PASS',checks=results,state_shop_written=False,native_status='PENDING')
    build.write(build.HERE/'history-test-results.json',out)
    print(json.dumps(out,ensure_ascii=True))
    return out

if __name__=='__main__':run(Path(sys.argv[1]) if len(sys.argv)>1 else build.HERE/'build/fifadb.sqlite')
