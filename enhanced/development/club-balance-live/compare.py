"""Recompute legal current-card XIs with the actual proposed reward functions."""
from pathlib import Path
import json,sqlite3,sys
sys.dont_write_bytecode=True
import prepare
import test


def main():
    balance=prepare.load(prepare.ROOT.parent/'team-balance-household/balance.py','club_balance_assignment')
    original=(prepare.SERVER/'http_config.py').read_text('utf8');proposed=prepare.transform(original)
    dbpath=prepare.SERVER/'gamedata/fifadb.sqlite'
    contexts={label:test.functions(source,dbpath) for label,source in [('current',original),('approved',proposed)]}
    ns=contexts['approved'];excluded=ns['ANALYSIS_EXCLUDED_SEASONS'];legends=excluded-{84,327}
    balance.LEGENDS=legends
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        prices={int(k) for k in json.loads((prepare.SERVER/'gamedata/fa_prices.json').read_text('utf8'))}
        market={r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m ON m.spid=p.spid AND m.transferable=1 WHERE p.spid>=1000000 AND p.playerid IN (SELECT playerid FROM namesind)')}|prices
        rows=[dict(r) for r in db.execute('SELECT * FROM players') if r['spid'] in market and r['spid']>=1000000]
        names={r[0]:r[1] for r in db.execute('SELECT playerid,full_eng FROM namesind')}
    cards,history=ns['tc_static']();labels=ns['analysis_club_names']()
    def evaluate(selected,positions):
        assert len({r['playerid'] for r in selected})==11
        return {k:balance.evaluate(c,selected,positions,names) for k,c in contexts.items()}
    def score(row,pos):return sum(row[k]*w for k,w in ns['ROLE_WEIGHTS'][ns['POS_ROLE'][pos]].items())//100
    clubs=(1,5,9,10,11,13,18,21,22,32,44,45,47,48,66,69,73,240,241,243)
    report=[]
    for club in clubs:
        eligible=[r for r in rows if r['spid']//1000000 not in (84,327) and club in ({r['teamid']}|history.get(r['playerid'],set()))]
        ordinary=[r for r in eligible if r['spid']//1000000 not in excluded]
        legend=[r for r in eligible if r['spid']//1000000 in legends]
        for formation,positions in balance.FORMATIONS.items():
            selected=balance.select(ns,ordinary,positions)
            if selected is None:
                report.append(dict(club=club,name=labels[str(club)],formation=formation,status='ORDINARY_NATURAL_XI_UNAVAILABLE'));continue
            pure=evaluate(selected,positions)
            for _ in range(5):
                best=None
                for i,(old,pos) in enumerate(zip(selected,positions)):
                    if old['spid']//1000000 in legends:continue
                    other={r['playerid'] for j,r in enumerate(selected) if j!=i}
                    for card in legend:
                        if card['playerid'] in other:continue
                        roles={ns['POS_ROLE'][card[k]] for k in ('preferredposition1','preferredposition2','preferredposition3','preferredposition4') if 0<=card[k]<28}
                        if ns['POS_ROLE'][pos] not in roles:continue
                        delta=score(card,pos)-score(old,pos)
                        if delta>0 and (best is None or delta>best[0]):best=(delta,i,card)
                if best is None:break
                _,i,card=best;selected[i]=card
            mixed=evaluate(selected,positions)
            report.append(dict(club=club,name=labels[str(club)],formation=formation,status='CALCULATED',
                ordinary_only=pure,mixed=mixed,ordinary_starters=sum(r['spid']//1000000 not in excluded for r in selected)))
        print('Compared club',club,flush=True)
    summary=[]
    for club in clubs:
        choices=[r for r in report if r['club']==club and r['status']=='CALCULATED']
        if not choices:continue
        best=max(choices,key=lambda r:r['mixed']['approved']['base_and_colors_mean'])
        p=max(choices,key=lambda r:r['ordinary_only']['approved']['base_and_colors_mean'])
        summary.append(dict(club=club,name=labels[str(club)],formation=best['formation'],ordinary=best['ordinary_starters'],
            mixed_before=best['mixed']['current']['base_and_colors_mean'],mixed_after=best['mixed']['approved']['base_and_colors_mean'],
            pure_before=p['ordinary_only']['current']['base_and_colors_mean'],pure_after=p['ordinary_only']['approved']['base_and_colors_mean'],
            weakest_ordinary_position=min(p['ordinary_only']['approved']['roster'],key=lambda r:r['base'])))
    result=dict(status='APPROVED_RULES_READONLY_COMPARISON',summary=summary,results=report,
        database_sha256=prepare.sha(dbpath),source_sha256=prepare.sha(prepare.SERVER/'http_config.py'),
        legend_seasons=sorted(legends),equal_grade=1,equal_level=1,common_intrinsic_boost_removed=5,
        method='Base-optimal identity-unique natural-role ordinary XI, then at most five positive legend substitutions; evaluate both versions with actual extracted functions.',
        limitations=['Not a global optimum over every color synergy.','Scores do not establish match performance.'],
        formal_files_written=False,native_verified=False,match_verified=False)
    prepare.write(prepare.ROOT/'comparison.json',result)
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
