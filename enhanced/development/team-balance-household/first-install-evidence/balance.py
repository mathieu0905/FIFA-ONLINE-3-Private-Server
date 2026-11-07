"""Compare legal, identity-unique XIs using production positional and team-color rules."""
from pathlib import Path
from contextlib import closing
import ast
import copy
import functools
import hashlib
import json
import sqlite3
import sys
sys.dont_write_bytecode=True
import prepare

ROOT=Path(__file__).resolve().parent
S=prepare.SERVER
LEGENDS={93,30,27,71,51,61,89,48,55,49}
FORMATIONS={'442':[0,3,4,6,7,12,13,15,16,24,26],
            '433':[0,3,4,6,7,9,13,15,23,25,27],
            '4231':[0,3,4,6,7,10,11,12,18,16,25]}
CLUBS={11:'曼联',243:'皇马',241:'巴萨',5:'切尔西',47:'AC米兰',44:'国际米兰',9:'利物浦',1:'阿森纳',22:'多特蒙德',45:'尤文图斯'}


def functions(source,database,market):
    harness=(ROOT.parent/'team-bonus20/test.py').read_text('utf8')
    node=next(n for n in ast.parse(harness).body if isinstance(n,ast.FunctionDef) and n.name=='functions')
    temp=dict(ast=ast,functools=functools,closing=closing,Database=lambda:None)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'read-only-production-harness','exec'),temp)
    ns=temp['functions'](source,real=True)
    ns['_db']=lambda:sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True)
    ns['on_market']=lambda sid:sid in market
    ns['STAT_COLS']=sorted({k for weights in ns['ROLE_WEIGHTS'].values() for k in weights})
    ns['GRADE_BOOST']=(0,5)
    return ns


def assign(weights):
    # Rectangular Hungarian assignment: every slot gets a different player identity.
    n,m=len(weights),len(weights[0])
    if n>m:return None
    u=[0]*(n+1);v=[0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;minv=[10**9]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=p[j0];delta=10**9;j1=0
            for j in range(1,m+1):
                if not used[j]:
                    cur=-weights[i0-1][j-1]-u[i0]-v[j]
                    if cur<minv[j]:minv[j]=cur;way[j]=j0
                    if minv[j]<delta:delta=minv[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minv[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    result=[None]*n
    for j in range(1,m+1):
        if p[j]:result[p[j]-1]=j-1
    if any(weights[i][j]<-10000 for i,j in enumerate(result)):return None
    return result


def select(ns,rows,positions):
    best={}
    for r in rows:
        roles={ns['POS_ROLE'][r[k]] for k in ('preferredposition1','preferredposition2','preferredposition3','preferredposition4') if 0<=r[k]<28}
        pid=r['playerid']
        for i,pos in enumerate(positions):
            role=ns['POS_ROLE'][pos]
            if role not in roles:continue
            score=sum(r[k]*w for k,w in ns['ROLE_WEIGHTS'][role].items())//100
            if score>best.get((i,pid),(-100000,None))[0]:best[i,pid]=(score,r)
    identities=sorted({pid for _,pid in best})
    if len(identities)<11:return None
    matrix=[[best.get((i,pid),(-100000,None))[0] for pid in identities] for i in range(11)]
    result=assign(matrix)
    return [best[i,identities[j]][1] for i,j in enumerate(result)] if result else None


def evaluate(ns,selected,positions,names):
    players=[dict(id=str(r['playerid']),spid=r['spid'],grade=1,levelinfo={'level':1,'exp':0}) for r in selected]
    team=dict(players=players,squad=dict(positions=[dict(id=p['id'],spid=p['spid'],pos=pos) for p,pos in zip(players,positions)]))
    stats={r['spid']:r for r in selected}
    ns['card_stats']=lambda ids:{sid:stats[sid] for sid in ids}
    team['teamcolors']=ns['active_teamcolors'](team)
    ratings=ns['xi_ratings'](team)
    members=[dict(playerid=r['playerid'],name=names.get(r['playerid']),spid=r['spid'],pos=pos,
                  role=ns['POS_ROLE'][pos],base=sum(r[k]*w for k,w in ns['ROLE_WEIGHTS'][ns['POS_ROLE'][pos]].items())//100,
                  base_and_colors=ratings[str(r['playerid'])]-5) for r,pos in zip(selected,positions)]
    return dict(base_mean=round(sum(r['base'] for r in members)/11,3),
                base_and_colors_mean=round(sum(r['base_and_colors'] for r in members)/11,3),
                minimum_player_base=min(r['base'] for r in members),
                ordinary_legend_count=sum(r['spid']//1000000 in LEGENDS for r in selected),
                roster=members,colors=team['teamcolors'])


def main():
    database=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'build/fifadb.sqlite'
    source=(S/'http_config.py').read_text('utf8')
    prices={int(k) for k in json.loads((S/'gamedata/fa_prices.json').read_text('utf8'))}
    with sqlite3.connect('file:'+database.as_posix()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        market={r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m ON m.spid=p.spid AND m.transferable=1 WHERE p.spid>=1000000 AND p.playerid IN (SELECT playerid FROM namesind)')}|prices
        rows=[dict(r) for r in db.execute('SELECT * FROM players') if r['spid'] in market and r['spid']>=1000000]
        names={r[0]:r[1] for r in db.execute('SELECT playerid,full_eng FROM namesind')}
        history={}
        for pid,club in db.execute('SELECT DISTINCT playerid,teamid FROM playerhistory'):history.setdefault(pid,set()).add(club)
    original='TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 2), (8, 9, 3), (10, 11, 4))'
    if source.count(original)!=1:raise RuntimeError('Fresh club tiers changed; re-review balance')
    candidates={'current':source,
        'max6':source.replace(original,'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 4), (10, 10, 5), (11, 11, 6))'),
        'max8':source.replace(original,'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 5), (10, 10, 7), (11, 11, 8))')}
    contexts={key:functions(text,database,market) for key,text in candidates.items()}
    ns=contexts['current']
    results=[]
    pools={'ordinary_legend_allstar':[r for r in rows if r['spid']//1000000 in LEGENDS],
           'moments_top_tier':[r for r in rows if r['spid']//1000000==84]}
    for club,name in CLUBS.items():
        eligible=[r for r in rows if r['spid']//1000000 not in (84,327) and club in ({r['teamid']}|history.get(r['playerid'],set()))]
        pools[f'{club}_mixed']=eligible
        pools[f'{club}_ordinary_only']=[r for r in eligible if r['spid']//1000000 not in LEGENDS]
    for pool,available in pools.items():
        for formation,positions in FORMATIONS.items():
            selected=select(ns,available,positions)
            if selected is None:
                results.append(dict(pool=pool,formation=formation,status='NATURAL_POSITION_XI_UNAVAILABLE'))
                continue
            ratings={key:evaluate(context,selected,positions,names) for key,context in contexts.items()}
            results.append(dict(pool=pool,formation=formation,status='PASS',ratings=ratings))
    report=dict(status='READ_ONLY_POSITIONAL_SQUAD_COMPARISON_COMPLETE',database=str(database),database_sha256=prepare.sha(database),
        source_sha256=hashlib.sha256(source.encode('utf8')).hexdigest(),club_names=CLUBS,
        method='Hungarian maximum base positional score; one card per identity; each slot must match one of four listed natural-position roles; then exact extracted production team-color/OVR functions',
        equal_grade=1,equal_level=1,reported_score='Base + actual team-color effects; common +1 intrinsic +5 removed',
        limitations=['Selection maximizes base position scores, not the combinatorial optimum of every special-color synergy.',
            'OVR is not a match-win probability; no native match, traits, animations or physical model advantage was measured.',
            'The moments benchmark remains separate and its attributes/feature/grade bonuses are unchanged.'],
        candidates={'current':[[4,5,1],[6,7,2],[8,9,3],[10,11,4]],'max6':[[4,5,1],[6,7,3],[8,9,4],[10,10,5],[11,11,6]],'max8':[[4,5,1],[6,7,3],[8,9,5],[10,10,7],[11,11,8]]},
        results=results,formal_files_written=False,real_assets_written=False)
    prepare.write(ROOT/'balance.json',report)
    summary=[]
    for pool in pools:
        possible=[r for r in results if r['pool']==pool and r['status']=='PASS']
        if possible:
            best=max(possible,key=lambda r:r['ratings']['current']['base_and_colors_mean'])
            summary.append(dict(pool=pool,formation=best['formation'],legend_count=best['ratings']['current']['ordinary_legend_count'],
                **{key:value['base_and_colors_mean'] for key,value in best['ratings'].items()}))
    prepare.write(ROOT/'balance-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
