"""Legal mixed-squad examples and an explicitly uninstalled ordinary-season incentive proposal."""
import json
from pathlib import Path
import sqlite3
import sys
sys.dont_write_bytecode=True
import balance
import prepare


def main():
    database=prepare.ROOT/'build-extended/fifadb.sqlite'
    report=json.loads((prepare.ROOT/'balance.json').read_text('utf8'))
    assert report['database_sha256']==prepare.sha(database)
    source=(prepare.SERVER/'http_config.py').read_text('utf8')
    with sqlite3.connect('file:'+database.as_posix()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        prices={int(k) for k in json.loads((prepare.SERVER/'gamedata/fa_prices.json').read_text('utf8'))}
        market={r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m ON m.spid=p.spid AND m.transferable=1 WHERE p.spid>=1000000 AND p.playerid IN (SELECT playerid FROM namesind)')}|prices
        rows={r['spid']:dict(r) for r in db.execute('SELECT * FROM players') if r['spid'] in market}
        names={r[0]:r[1] for r in db.execute('SELECT playerid,full_eng FROM namesind')}
        hist={}
        for pid,club in db.execute('SELECT playerid,teamid FROM playerhistory'):hist.setdefault(pid,set()).add(club)
    original='TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 2), (8, 9, 3), (10, 11, 4))'
    ns=balance.functions(source,database,market)
    variants={'current':source,
        'max6':source.replace(original,'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 4), (10, 10, 5), (11, 11, 6))'),
        'max8':source.replace(original,'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 5), (10, 10, 7), (11, 11, 8))')}
    contexts={k:balance.functions(v,database,market) for k,v in variants.items()}
    examples=[]
    for entry in report['results']:
        if not entry['pool'].endswith('_ordinary_only') or entry['status']!='PASS':continue
        club=int(entry['pool'].split('_')[0]);positions=balance.FORMATIONS[entry['formation']]
        selected=[rows[p['spid']] for p in entry['ratings']['current']['roster']]
        legends=[r for r in rows.values() if r['spid']//1000000 in balance.LEGENDS and club in ({r['teamid']}|hist.get(r['playerid'],set()))]
        def score(row,pos):return sum(row[k]*w for k,w in ns['ROLE_WEIGHTS'][ns['POS_ROLE'][pos]].items())//100
        # Start with an identity-unique ordinary XI. Make up to five positive
        # natural-position legend substitutions. This yields reviewable examples,
        # not a claim of globally optimal constrained squad selection.
        for _ in range(5):
            best=None
            for i,(old,pos) in enumerate(zip(selected,positions)):
                if old['spid']//1000000 in balance.LEGENDS:continue
                others={r['playerid'] for j,r in enumerate(selected) if i!=j}
                for legend in legends:
                    if legend['playerid'] in others:continue
                    roles={ns['POS_ROLE'][legend[k]] for k in ('preferredposition1','preferredposition2','preferredposition3','preferredposition4') if 0<=legend[k]<28}
                    if ns['POS_ROLE'][pos] not in roles:continue
                    delta=score(legend,pos)-score(old,pos)
                    if delta>0 and (best is None or delta>best[0]):best=(delta,i,legend)
            if best is None:break
            _,i,row=best;selected[i]=row
        assert len({r['playerid'] for r in selected})==11
        scores={k:balance.evaluate(context,selected,positions,names) for k,context in contexts.items()}
        ordinary=11-scores['current']['ordinary_legend_count']
        amount=4 if ordinary>=9 else 3 if ordinary>=7 else 2 if ordinary>=5 else 1 if ordinary>=3 else 0
        for key,value in scores.items():
            value['hypothetical_ordinary_support_mean']=round(value['base_and_colors_mean']+ordinary*amount/11,3)
        examples.append(dict(club=club,club_name=balance.CLUBS[club],formation=entry['formation'],ordinary_starters=ordinary,
            ordinary_legend_starters=11-ordinary,ordinary_support_per_eligible_player=amount,ratings=scores))
    summary=[]
    for club,name in balance.CLUBS.items():
        choices=[x for x in examples if x['club']==club]
        if not choices:continue
        best=max(choices,key=lambda x:x['ratings']['max8']['hypothetical_ordinary_support_mean'])
        summary.append(dict(club=name,formation=best['formation'],ordinary=best['ordinary_starters'],legend=best['ordinary_legend_starters'],
            current=best['ratings']['current']['base_and_colors_mean'],
            max6_with_ordinary_support=best['ratings']['max6']['hypothetical_ordinary_support_mean'],
            max8_with_ordinary_support=best['ratings']['max8']['hypothetical_ordinary_support_mean']))
    result=dict(status='PROPOSAL_CALCULATED_NOT_INSTALLED',database_sha256=prepare.sha(database),
        ordinary_legend_seasons=sorted(balance.LEGENDS),examples=examples,summary=summary,
        proposal=dict(club_tiers=[[4,5,1],[6,7,3],[8,9,5],[10,10,7],[11,11,8]],
            ordinary_season_support=[[3,4,1],[5,6,2],[7,8,3],[9,11,4]],
            eligibility='Only same-club non-legend ordinary season starters; separate identity count; bench excluded; no benefit to moments/future/ordinary legends',
            implementation_status='Numeric simulation only; not implemented, hot-loaded or native-match validated'),
        method='Base-optimal ordinary XI plus up to five positive natural-position legend substitutions; exact production current color math, with ordinary incentive added arithmetically for comparison',
        limitations=['Examples are legal but not globally optimal mixed XIs.','Attribute scores cannot establish match win rates.','Existing named-club outlier bonuses also require review before changing balance.'],
        formal_files_written=False)
    prepare.write(prepare.ROOT/'diversity-proposal.json',result)
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
