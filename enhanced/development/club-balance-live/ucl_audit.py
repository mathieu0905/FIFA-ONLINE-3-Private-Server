"""Read-only official 25UCL feasibility, roster and career coverage audit."""
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime,gzip,hashlib,html,importlib.util,json,re,sqlite3,sys,time,urllib.request
sys.dont_write_bytecode=True
import prepare
R=prepare.ROOT;S=prepare.SERVER;C=prepare.CLIENT


def main():
    meta=json.loads((R.parent/'team-balance-household/sources/spid-current.json').read_text('utf8'))
    season=json.loads((R/'fc-seasonid.json').read_text('utf8'))
    pool=[p for p in meta if p['id']//1000000==856]
    names=defaultdict(list)
    for p in pool:names[p['name']].append(p['id'])
    initial=[]
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',(R/'ucl-initial.html').read_text('utf8'),re.S):
        cells=[html.unescape(re.sub('<[^>]+>','',v)).strip() for v in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S)]
        if len(cells)==7 and cells[0]=='25UCL':
            matches=names[cells[1]]
            initial.append(dict(name_ko=cells[1],role=cells[2],overall=int(cells[6]),
                source_spid=matches[0] if len(matches)==1 else None,ambiguous_ids=matches if len(matches)!=1 else []))
    assert len(initial)==342
    career_parser=prepare.load(R.parent/'club-history/collect.py','ucl_career_parser')
    out=R/'ucl-careers';out.mkdir(exist_ok=True)
    def one(item):
        pid=item['id']%1000000;dest=out/(str(pid)+'.json')
        if dest.exists():
            cached=json.loads(dest.read_text('utf8'))
            if cached['status']=='OK':return cached
        url='https://fconline.nexon.com/DataCenter/PlayerInfo?spid='+str(item['id'])
        try:
            body=urllib.request.urlopen(url,timeout=18).read()
            career=career_parser.parse(body.decode('utf-8-sig'))
            (out/(str(pid)+'.html.gz')).write_bytes(gzip.compress(body,mtime=0))
            result=dict(status='OK',playerid=pid,source_spid=item['id'],name_ko=item['name'],url=url,
                career=career,raw_sha256=hashlib.sha256(body).hexdigest(),fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        except Exception as exc:result=dict(status='UNAVAILABLE',playerid=pid,error=str(exc),url=url)
        prepare.write(dest,result);time.sleep(.1);return result
    careers=[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        for f in as_completed([executor.submit(one,p) for p in pool]):
            careers.append(f.result())
            if len(careers)%60==0:print('Career sources processed:',len(careers),flush=True)
    sys.path[:0]=[str(S/'tools/player_import'),str(S/'tools/re')]
    import bigdir,native_db
    raw=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db')
    xml=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8')
    _,_,_,_,table,fields=native_db.player_table(raw,xml)
    native={table.get(row,fields['playerid']['shortname']) for row in table.rows}
    with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        ui={p[0] for p in db.execute('select distinct playerid from players')}
        cards={p[0] for p in db.execute('select spid from players')}
    mapping=json.loads((R.parent/'club-history/club-map.json').read_text('utf8'))
    # Exact licensing aliases already verified in the installed household release.
    mapping={name:{131681:47,131682:44}.get(cid,cid) for name,cid in mapping.items()}
    labels=json.loads((S/'server_display_zh.json').read_text('utf8'))['names_by_id']['TEAMNAMES_CHI.json']
    bypid={p['playerid']:p for p in careers}
    byclub=defaultdict(list)
    details=[]
    for card in pool:
        pid=card['id']%1000000;career=bypid[pid]
        histories=career.get('career',[])
        # Career clubs are eligibility evidence, not an assertion about the card's 25/26 registration.
        clubs={mapping[h['club_ko']] for h in histories if h['club_ko'] in mapping}
        row=dict(card,playerid=pid,ui_identity=pid in ui,native_identity=pid in native,
                 exact_card_installed=card['id'] in cards,verified_career_clubs=sorted(clubs))
        details.append(row)
        for cid in clubs:byclub[cid].append(pid)
    targets=(1,5,9,10,11,13,18,21,22,32,44,45,47,48,66,69,73,240,241,243)
    summary=[]
    for cid in targets:
        ids=set(byclub[cid]);summary.append(dict(club=cid,name=labels.get(str(cid)),
            potential_25ucl_by_verified_career=len(ids),native_existing=len(ids&native),new_native=len(ids-native)))
    report=dict(status='OFFICIAL_SOURCE_READONLY_AUDIT',season_25ucl=next(x for x in season if x['seasonId']==856),
        season_26ucl_matches=[x for x in season if '26 UCL' in x.get('className','') or '26UCL' in x.get('className','')],
        metadata_cards=len(pool),initial_official_cards=len(initial),initial_ambiguous=sum(p['source_spid'] is None for p in initial),
        initial_roles=dict(Counter(p['role'] for p in initial)),source_ovr_range=[min(p['overall'] for p in initial),max(p['overall'] for p in initial)],
        existing_ui_identities=sum(p['ui_identity'] for p in details),existing_native_identities=sum(p['native_identity'] for p in details),
        already_installed_25ucl_cards=sum(p['exact_card_installed'] for p in details),career_outcomes=dict(Counter(c['status'] for c in careers)),
        club_eligibility_coverage=summary,details=details,initial_cards=initial,
        disclaimer='Coverage counts verified career households, not 25/26 registered squads; models/UI/native profiles not imported or certified.',
        formal_files_written=False,state_shop_written=False,attributes_imported=False)
    prepare.write(R/'ucl-audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('details','initial_cards')},ensure_ascii=True))


if __name__=='__main__':main()
