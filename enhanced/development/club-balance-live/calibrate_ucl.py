"""Read-only 25UCL attribute-scale comparison. No database or asset writes."""
from pathlib import Path
import collections,copy,hashlib,html,json,re,sqlite3,sys,time
sys.dont_write_bytecode=True
import prepare
import test

SOURCE_FIELDS=('acceleration aggression agility balance ballcontrol composure crossing curve dribbling finishing freekickaccuracy '
    'gkdiving gkhandling gkkicking gkpositioning gkreflexes headingaccuracy jumping longpassing longshots marking penalties '
    'positioning reactions shortpassing shotpower slidingtackle sprintspeed stamina standingtackle strength interceptions vision volleys').split()
POSITIONS=dict(GK=0,RB=3,CB=4,LB=7,RWB=2,LWB=8,CDM=10,CM=13,CAM=18,RM=12,LM=16,RW=23,LW=27,ST=25,SS=21)


def mapped_stat(value,slope):
    # Keep naturally tiny goalkeeper/outfield weaknesses, compress premium range.
    return value if value<=30 else int(30+(value-30)*slope+.5)


def main():
    r=prepare.ROOT;s=prepare.SERVER;dbpath=s/'gamedata/fifadb.sqlite'
    audit=json.loads((r/'ucl-audit.json').read_text('utf8'))
    detail={p['id']:p for p in audit['details']}
    table=[]
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',(r/'ucl-initial.html').read_text('utf8'),re.S):
        cells=[html.unescape(re.sub('<[^>]+>','',v)).strip() for v in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S)]
        table.append(cells)
    basic=[v for v in table if len(v)==7 and v[0]=='25UCL']
    stats=[v for v in table if len(v)==36 and all(v.isdecimal() for v in v[2:])]
    assert len(basic)==len(stats)==len(audit['initial_cards'])==342
    source=[]
    for b,v,identity in zip(basic,stats,audit['initial_cards']):
        assert b[1]==identity['name_ko'] and b[2]==identity['role'] and int(b[6])==identity['overall']
        sid=identity['source_spid']
        if sid is None:continue
        source.append(dict(spid=sid,playerid=sid%1000000,name_ko=b[1],role=b[2],source_overall=int(b[6]),
            attributes=dict(zip(SOURCE_FIELDS,map(int,v[2:]))),**{k:detail[sid][k] for k in ('native_identity','verified_career_clubs')}))
    assert len({p['spid'] for p in source})==len(source)
    # Exact name->metadata joins only. Ambiguous/renamed identities are withheld.
    assert len(source)==310
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        allrows=[dict(p) for p in db.execute('select * from players')]
        names={p[0]:p[1] for p in db.execute('select playerid,full_eng from namesind')}
        market={p[0] for p in db.execute('select spid from permid where transferable=1')}
        market|={int(k) for k in json.loads((s/'gamedata/fa_prices.json').read_text('utf8'))}
    templates={}
    for p in allrows:templates.setdefault(p['playerid'],p)
    existing=[p for p in allrows if p['spid']>=1000000 and p['spid'] in market and p['playerid'] in names]
    balance=prepare.load(r.parent/'team-balance-household/balance.py','ucl_calibration_assignment')
    original=(s/'http_config.py').read_text('utf8')
    proposed=original if 'TC_ORDINARY_CLUB_BASE' in original else prepare.transform(original)
    baseline=test.functions(proposed,dbpath)
    cards,hist=baseline['tc_static']();excluded=baseline['ANALYSIS_EXCLUDED_SEASONS']
    balance.LEGENDS=excluded-{84,327}
    labels=baseline['analysis_club_names']()
    clubs=(1,5,9,10,11,13,18,21,22,32,44,45,47,48,66,69,73,240,241,243)
    results=[];profiles={};checks=[]
    slopes=(0.0,) if '--baseline' in sys.argv else (.64,) if '--middle' in sys.argv else (.58,.62,.66)
    for slope in slopes:
        converted=[]
        for p in source:
            # Temporary row only: do not assert absent identities have native resources.
            row=copy.deepcopy(templates.get(p['playerid'],allrows[0]))
            row.update(spid=p['spid'],playerid=p['playerid'],teamid=0,
                preferredposition1=POSITIONS[p['role']],preferredposition2=-1,preferredposition3=-1,preferredposition4=-1)
            if not p['native_identity']:row.update(nationality=-p['playerid'],nationalteamid=-p['playerid'])
            for field,value in p['attributes'].items():
                if field!='composure':row[field]=mapped_stat(value,slope)
            assert all(1<=row[f]<=99 for f in SOURCE_FIELDS if f!='composure')
            converted.append(row)
        key=str(slope);profiles[key]=[]
        for p,row in zip(source,converted):
            role=baseline['POS_ROLE'][row['preferredposition1']]
            weighted=sum(row[f]*w for f,w in baseline['ROLE_WEIGHTS'][role].items())//100
            profiles[key].append(dict(source_spid=p['spid'],name=names.get(p['playerid'],p['name_ko']),source_role=p['role'],
                source_overall=p['source_overall'],primary_position_base=weighted,native_identity_exists=p['native_identity'],
                converted_attributes={f:row[f] for f in SOURCE_FIELDS if f!='composure'}))
        assert all(mapped_stat(x,slope)<=mapped_stat(x+1,slope) for x in range(1,139))
        checks.append('Monotonic, 33 attributes in FO3 1..99 range, slope='+key)
        for scope in ('existing_native_subset','all_unambiguous_source_subset'):
            scoped=[p for p in converted if scope!='existing_native_subset' or detail[p['spid']]['native_identity']]
            added=[] if '--baseline' in sys.argv else scoped
            ns=test.functions(proposed,dbpath)
            combined_cards=dict(cards);combined_history={pid:set(teams) for pid,teams in hist.items()}
            for p in added:
                combined_cards[p['spid']]=(p['playerid'],p['teamid'],p['nationality'])
            for p in scoped:
                combined_history.setdefault(p['playerid'],set()).update(detail[p['spid']]['verified_career_clubs'])
            ns['tc_static']=lambda:(combined_cards,combined_history)
            # Build function caches before reusing the closure for another scenario.
            ns['tc_colors']();ns['tc_special_sets']()
            for club in clubs:
                eligible=[p for p in existing+added if p['spid']//1000000 not in (84,327) and
                    club in ({p['teamid']}|combined_history.get(p['playerid'],set()))]
                ordinary=[p for p in eligible if p['spid']//1000000 not in excluded]
                legends=[p for p in eligible if p['spid']//1000000 in balance.LEGENDS]
                choices=[]
                for formation,positions in balance.FORMATIONS.items():
                    mixed=balance.select(ns,eligible,positions)
                    if mixed is not None:
                        value=balance.evaluate(ns,mixed,positions,names)
                        choices.append(dict(formation=formation,legend_substitutions=sum(p['spid']//1000000 in balance.LEGENDS for p in mixed),
                            score=value['base_and_colors_mean'],new_25ucl=sum(p['spid']//1000000==856 for p in mixed),details=value))
                    selected=balance.select(ns,ordinary,positions)
                    if selected is None:continue
                    for swaps in range(6):
                        value=balance.evaluate(ns,selected,positions,names)
                        choices.append(dict(formation=formation,legend_substitutions=swaps,score=value['base_and_colors_mean'],
                            new_25ucl=sum(p['spid']//1000000==856 for p in selected),details=value))
                        if swaps==5:break
                        best=None
                        for i,(old,pos) in enumerate(zip(selected,positions)):
                            if old['spid']//1000000 in balance.LEGENDS:continue
                            other={p['playerid'] for j,p in enumerate(selected) if i!=j}
                            role=ns['POS_ROLE'][pos]
                            score=lambda p:sum(p[f]*w for f,w in ns['ROLE_WEIGHTS'][role].items())//100
                            for legend in legends:
                                if legend['playerid'] in other:continue
                                roles={ns['POS_ROLE'][legend[k]] for k in ('preferredposition1','preferredposition2','preferredposition3','preferredposition4') if 0<=legend[k]<28}
                                if role not in roles:continue
                                delta=score(legend)-score(old)
                                if delta>0 and (best is None or delta>best[0]):best=(delta,i,legend)
                        if best is None:break
                        _,i,row=best;selected[i]=row
                if choices:
                    best=max(choices,key=lambda c:c['score'])
                    results.append(dict(slope=slope,scope=scope,club=club,name=labels[str(club)],**best))
            print('Completed mapping',slope,scope,flush=True)
    summary=[]
    for club in clubs:
        row=dict(club=club,name=labels[str(club)])
        for slope in slopes:
            for scope,tag in [('existing_native_subset','native'),('all_unambiguous_source_subset','all')]:
                found=next((p for p in results if p['club']==club and p['slope']==slope and p['scope']==scope),None)
                if found:row[str(slope)+'_'+tag]=dict(score=found['score'],new_25ucl=found['new_25ucl'])
        summary.append(row)
    result=dict(status='READ_ONLY_ATTRIBUTE_CALIBRATION_NOT_IMPORTED',created=datetime_now(),summary=summary,results=results,
        profiles=profiles,checks=checks,source_cards_calibrated=len(source),native_existing_in_calibrated=sum(p['native_identity'] for p in source),
        withheld_initial_identity_joins=32,metadata_cards_not_in_initial_release=19,
        source_file_sha256=prepare.sha(r/'ucl-initial.html'),database_sha256=prepare.sha(dbpath),server_source_sha256=prepare.sha(s/'http_config.py'),
        mapping='x<=30 unchanged; otherwise round-half-up(30+(x-30)*slope); composure has no copied FO3 field.',
        common_grade=1,common_level=1,reported_score='Position-weighted base + actual colors; common intrinsic +5 removed.',
        limitations=['Initial-release stats, not a claim about latest live-performance revisions.',
            '310 unambiguous exact-ID matches only, not a full 361-card import.',
            'Primary natural role only for new cards; secondary positions/traits/foot/physical profiles need exact-ID source validation.',
            'New identities lack native resource certification; full-pool scenario is theoretical.',
            'New-card national colors omitted where nationality is unknown; verified career clubs used as eligibility, not 25/26 registration.',
            'Compare unrestricted base-optimal mixed XIs and ordinary XIs with positive legend substitutions across three formations; not global special-color optimization or match-win evidence.',
            'Displayed card overallrating is not assigned here; actual position-weighted attributes determine the comparison.'],
        formal_files_written=False,state_shop_written=False,cards_imported=0,native_verified=False,match_verified=False)
    result.update(status='RECALCULATED_NO_ORDINARY_REWARD_NOT_APPROVED',ordinary_card_extra_reward=0,base_club_tiers_only=True)
    if '--baseline' in sys.argv:
        assert all(p['new_25ucl']==0 for p in results)
        result['profiles']={}
        result['scenario']='Approved squad rewards and same verified careers, no 25UCL cards added.'
    filename='25ucl-baseline-calibration.json' if '--baseline' in sys.argv else '25ucl-middle-calibration.json' if '--middle' in sys.argv else '25ucl-calibration.json'
    prepare.write(r/filename,result)
    print(json.dumps(dict(summary=summary,source_cards_calibrated=310,native_existing=result['native_existing_in_calibrated']),ensure_ascii=True))


def datetime_now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


if __name__=='__main__':main()
