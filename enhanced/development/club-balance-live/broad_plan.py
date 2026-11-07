"""Concrete gap-directed ordinary-season expansion, without importing cards."""
import json,sqlite3,sys
sys.dont_write_bytecode=True
import prepare
import test


def main():
    r=prepare.ROOT
    comparison=json.loads((r/'comparison.json').read_text('utf8'))
    ucl=json.loads((r/'ucl-audit.json').read_text('utf8'))
    details={p['id']:p for p in ucl['details']}
    with sqlite3.connect((prepare.SERVER/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        names={p[0]:p[1] for p in db.execute('SELECT playerid,full_eng FROM namesind')}
        prices={int(k) for k in json.loads((prepare.SERVER/'gamedata/fa_prices.json').read_text('utf8'))}
        market={p[0] for p in db.execute('SELECT spid FROM permid WHERE transferable=1')}|prices
        rows=[dict(p) for p in db.execute('SELECT * FROM players') if p['spid']>=1000000 and p['spid'] in market and p['playerid'] in names]
    balance=prepare.load(r.parent/'team-balance-household/balance.py','club_plan_assignment')
    original=(prepare.SERVER/'http_config.py').read_text('utf8');proposed=prepare.transform(original)
    contexts={k:test.functions(s,prepare.SERVER/'gamedata/fifadb.sqlite') for k,s in [('current',original),('approved',proposed)]}
    legend_codes=contexts['approved']['ANALYSIS_EXCLUDED_SEASONS']-{84,327}
    balance.LEGENDS=legend_codes
    benchmarks=[]
    for label,codes in [('ordinary_legend_allstar',legend_codes),('moments_separate_top_tier',{84})]:
        available=[p for p in rows if p['spid']//1000000 in codes]
        for formation,positions in balance.FORMATIONS.items():
            selected=balance.select(contexts['current'],available,positions)
            if selected:
                benchmarks.append(dict(pool=label,formation=formation,ratings={k:balance.evaluate(ns,selected,positions,names) for k,ns in contexts.items()}))
    benchmark_summary=[]
    for label in ('ordinary_legend_allstar','moments_separate_top_tier'):
        best=max((b for b in benchmarks if b['pool']==label),key=lambda b:b['ratings']['current']['base_and_colors_mean'])
        benchmark_summary.append(dict(pool=label,formation=best['formation'],before=best['ratings']['current']['base_and_colors_mean'],after=best['ratings']['approved']['base_and_colors_mean']))
    roles={'FB':{'RB','LB','LWB','RWB'},'CB':{'CB'},'GK':{'GK'},'CM':{'CM','CDM','CAM'},'WM':{'LW','RW','LM','RM'},'ST':{'ST','SS'}}
    plans=[]
    for s in sorted(comparison['summary'],key=lambda c:c['mixed_after']):
        weak=s['weakest_ordinary_position']['role'];club=s['club'];candidates=[]
        for p in ucl['initial_cards']:
            if p['source_spid'] is None or p['role'] not in roles[weak]:continue
            d=details[p['source_spid']]
            if club not in d['verified_career_clubs']:continue
            candidates.append(dict(source_spid=p['source_spid'],playerid=d['playerid'],name=names.get(d['playerid'],p['name_ko']),
                role=p['role'],source_overall=p['overall'],native_identity_exists=d['native_identity'],
                other_real_11_243_households=[c for c in (11,243) if c in d['verified_career_clubs'] and c!=club]))
        candidates.sort(key=lambda p:(not p['native_identity_exists'],bool(p['other_real_11_243_households']),-p['source_overall']))
        plans.append(dict(club=club,name=s['name'],mixed_after=s['mixed_after'],priority=s['mixed_after']<94,
            weakest_role=weak,weakest_current_base=s['weakest_ordinary_position']['base'],
            ordinary_25ucl_role_candidates=candidates[:4],
            insufficient_25ucl_native_candidates=sum(p['native_identity_exists'] for p in candidates)<2))
    result=dict(status='READ_ONLY_CONTENT_EXPANSION_PLAN_NOT_IMPORTED',benchmarks=benchmark_summary,benchmark_details=benchmarks,
        clubs=plans,first_wave='Prioritize weakest natural positions of clubs below 94 in this same-grade comparison. Reuse verified native identities where useful; add new identities only through full import pipeline.',
        target='Calibrate added ordinary cards against the ordinary-legend-allstar benchmark after team rewards; preserve moments top-tier individual profiles.',
        conversion='Do not copy FC 102-120 OVR directly. Map positional/stat distributions into existing FO3 ordinary-card scale, then recompute all eligible old-club lineups.',
        coverage='25UCL as primary source; use 24UCL or current domestic ordinary cards where exact verified rosters fill uncovered roles. No fictitious 26UCL.',
        access='A later approved import must include obtainable ordinary team packs and actual pricing based on minimum guaranteed enhancement, without charging for surprise high enhancements.',
        prerequisites=['Audit native card-frame/season-code compatibility; existing generic builder only audits 12/13 and cannot simply whitelist 856.',
            'Preserve identity across seasons, verify current and historical club mapping including licensing aliases, and keep legitimate older-club household eligibility.',
            'Source exact-ID attributes/traits, map FO3 stars/codes, validate native identity, selectors, required resources and player_import full certificate.',
            'Perform static/native home/match checks with their scopes recorded separately; no live synthetic assets.'],
        formal_files_written=False,cards_imported=0,season_26ucl_available=False,native_verified=False,match_verified=False)
    prepare.write(r/'broad-club-plan.json',result)
    print(json.dumps(dict(benchmarks=benchmark_summary,priority_clubs=[p['name'] for p in plans if p['priority']],native_shortlist=[dict(club=p['name'],role=p['weakest_role'],candidates=p['ordinary_25ucl_role_candidates'][:2]) for p in plans if p['priority']]),ensure_ascii=True))


if __name__=='__main__':main()
