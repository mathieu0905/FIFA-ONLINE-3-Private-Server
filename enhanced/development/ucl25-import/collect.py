"""Freeze exact public-source bios/portraits and native routes, never live writes."""
import collections,datetime,html,re,sqlite3,time,urllib.request,concurrent.futures
from common import *
import bigdir,native_db


def main():
    raw=read(SOURCE/'25ucl-current-official.json');assert raw['ok']==raw['card_count']==361
    careers=SOURCE/'ucl-careers';portraits=R/'portraits';portraits.mkdir(exist_ok=True)
    db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    old={}
    for row in db.execute('select * from players'):old.setdefault(row['playerid'],[]).append(dict(row))
    names={r['playerid']:dict(r) for r in db.execute('select * from namesind')}
    teams={}
    for tid,lid in db.execute('select teamid,leagueid from players where leagueid not in (78,2028,9998,9999)'):
        teams.setdefault(tid,collections.Counter())[lid]+=1
    nations={}
    for nat,tid in db.execute('select nationality,nationalteamid from players where nationalteamid>0'):
        nations.setdefault(nat,collections.Counter())[tid]+=1
    db.close()
    native=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');xml=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8')
    _,_,_,_,table,fields=native_db.player_table(native,xml);key=fields['playerid']['shortname']
    native_rows={table.get(row,key):row for row in table.rows}
    def semantic(row,name):return table.get(row,fields[name]['shortname'])+int(fields[name]['rangelow'])
    heads={n for n,*_ in bigdir.entries(C/'data/data_4.big')}
    generic=None
    for pid,rows in old.items():
        if pid not in native_rows:continue
        n=native_rows[pid]
        a={k:semantic(n,k) for k in ('headtypecode','headclasscode','headassetid','skintonecode')}
        if a['headclasscode']!=1 or a['headtypecode']>=30001:continue
        if f"data/sceneassets/heads/head_{a['headtypecode']}_{a['headclasscode']}.rx3" not in heads:continue
        template=next((r for r in rows if all(r[k]==a[k] for k in ('headtypecode','headclasscode','skintonecode'))),None)
        if template:
            generic=dict(playerid=pid,source_spid=template['spid'],appearance=a);break
    if generic is None:raise ValueError('No verified built-in generic head template')
    mapping=read(R.parent/'club-history/club-map.json');mapping={n:CLUB_ALIASES.get(t,t) for n,t in mapping.items()}
    rows=[];conflicts=[];unmapped=collections.Counter()
    for card in raw['cards']:
        sid,pid=card['source_spid'],card['playerid'];path=SOURCE/'ucl-final-source'/f'{sid}.html';text=path.read_text('utf8')
        def etc(name):
            m=re.search(r'<span class="etc '+name+r'">(.*?)</span>',text,re.S)
            if not m:raise ValueError('Missing '+name+' '+str(sid))
            return html.unescape(re.sub('<[^>]+>','',m[1])).strip()
        birth=datetime.datetime.strptime(etc('birth'),'%Y.%m.%d').date()
        height=int(etc('height').removesuffix('cm'));weight=int(etc('weight').removesuffix('kg'))
        stars=re.search(r'<span class="etc skill">\s*<span>([★]+)</span>',text)
        if not stars:raise ValueError('Missing explicit source skill stars')
        skill=len(stars[1]);skillcode=native_db.stars_to_code(skill)
        footblock=re.search(r'<span class="etc foot">(.*?)</span>',text,re.S)[1]
        feet={k:int(v) for k,v in re.findall(r'([LR])([1-5])',footblock)}
        dominant=re.search(r'<strong>([LR])[1-5]</strong>',footblock)[1]
        assert set(feet)=={'L','R'} and feet[dominant]==5
        country=int(re.search(r'countries/smallflags/(\d+)\.png',text)[1])
        tid=int(re.search(r'class="etc team">.*?crests/light/small/l(\d+)\.png',text,re.S)[1]);tid=CLUB_ALIASES.get(tid,tid)
        lid=teams[tid].most_common(1)[0][0] if tid in teams else int(re.search(r'class="league">.*?/ca/d(\d+)\.png',text,re.S)[1])
        club_name=html.unescape(re.search(r'class="etc team">.*?<span class="txt">(.*?)</span>',text,re.S)[1]).strip()
        pos=[card['role']]+re.findall(r'<span class="position [a-z]+">\s*<span class="txt">([A-Z]+)</span>',text)
        pos=list(dict.fromkeys(pos));assert len(pos)<=4
        traits=[dict(id=int(i),name=html.unescape(n)) for i,n in re.findall(r'traits/trait_icon_(\d+)\.png" alt="([^"]+)"',text)]
        traits=list({t['id']:t for t in traits}.values())
        portrait=html.unescape(re.search(r'name="hidPlayerCustImg" value="([^"]+)"',text)[1])
        if not portrait.startswith('https://fco.dn.nexoncdn.co.kr/'):raise ValueError('Unexpected portrait host')
        hist=read(careers/f'{pid}.json');assert hist['status']=='OK' and hist['playerid']==pid
        verified=[]
        for h in hist['career']:
            if h['club_ko'] in mapping:
                verified.append(dict(teamid=mapping[h['club_ko']],joinedyear=h['joinedyear'],endyear=h['endyear'],loan=h['loan']))
            else:unmapped[h['club_ko']]+=1
        if pid in old:
            prior={datetime.datetime.strptime(r['birthdate'].split(' ')[0],'%m/%d/%Y').date() for r in old[pid]}
            if prior!={birth}:conflicts.append(dict(playerid=pid,name=names.get(pid,{}).get('full_eng'),source_birth=birth.isoformat(),
                existing_births=sorted(str(x) for x in prior),policy='Source birth is used only on new card; old rows/native identity preserved; same named person reviewed.'))
        if pid not in native_rows and pid in old:raise ValueError('Existing UI identity lacks native support; repair before new card '+str(pid))
        row=dict(source_spid=sid,playerid=pid,name_ko=card['name_ko'],name_existing=names.get(pid),
            source_attributes=card['attributes'],source_overall=card['overall'],source_birth=birth.isoformat(),
            birthdate=f'{birth.month}/{birth.day}/{birth.year} 12:00:00 AM',height=height,weight=weight,
            source_skill_stars=skill,skillmoves=skillcode,preferredfoot=2 if dominant=='L' else 1,
            weakfootabilitytypecode=feet['R' if dominant=='L' else 'L'],nationality=country,
            nationalteamid=nations[country].most_common(1)[0][0] if country in nations else 0,
            teamid=tid,leagueid=lid,club_source_name=club_name,source_positions=pos,source_body=etc('physical'),
            source_traits=traits,trait1=sum(1<<t['id'] for t in traits if t['id']<30),trait2=0,
            unsupported_source_traits=[t for t in traits if t['id']>=30],career=verified,
            native_existing=pid in native_rows,appearance_route='existing_identity' if pid in native_rows else 'fo3_builtin_generic',
            portrait_url=portrait,source_sha256=sha(path),career_source_sha256=sha(careers/f'{pid}.json'))
        rows.append(row)
    def image(row):
        path=portraits/f"p{row['source_spid']}.png"
        if not path.exists():
            for attempt in range(3):
                try:
                    body=urllib.request.urlopen(row['portrait_url'],timeout=20).read()
                    if body[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Not PNG')
                    path.write_bytes(body);break
                except Exception:
                    if attempt==2:raise
                    time.sleep(.3)
        return str(row['source_spid']),sha(path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:images=dict(ex.map(image,rows))
    assert len(rows)==len(images)==361
    report=dict(status='EXACT_SOURCE_BIOS_PORTRAITS_READY',season=SID,multiplier=MULTIPLIER,cards=rows,
        generic_template=generic,native_existing=sum(p['native_existing'] for p in rows),
        new_native=sum(not p['native_existing'] for p in rows),portrait_sha256=images,birth_conflicts=conflicts,
        unmapped_historical_clubs=dict(unmapped),policy='Unmapped historical clubs remain explicit; exact current source team IDs retained. No guessed parent club for youth/B teams.',
        source_file_sha256=sha(SOURCE/'25ucl-current-official.json'),formal_files_written=False,GUI_used=False)
    write(R/'source-ready.json',report)
    print('SOURCE_READY',len(rows),'native_existing',report['native_existing'],'new_generic',report['new_native'],'birth_variants',len(conflicts))


if __name__=='__main__':main()
