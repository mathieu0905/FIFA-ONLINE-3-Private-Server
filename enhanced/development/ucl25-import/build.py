"""Prepare one additive roster/resource delta against fresh formal inputs."""
from contextlib import closing
import copy,datetime,gzip,shutil,sqlite3,subprocess
from common import *
import bigdir,ordered_big,native_db,extract_fifadb as codec
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
import display

POSITIONS=dict(GK=0,RWB=2,RB=3,CB=4,LB=7,LWB=8,CDM=10,RM=12,CM=13,LM=16,CAM=18,CF=21,SS=21,RW=23,ST=25,LW=27)
PERMISSIONS=('permid','permcn','permkr','permth','permvn','permsg')

def encrypt(data):
    encoder=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor()
    return codec.swap32(encoder.update(codec.swap32(data))+encoder.finalize())


def insert(db,table,row):
    keys=list(row)
    db.execute('insert into "'+table+'"('+','.join('"'+k+'"' for k in keys)+') values('+','.join('?' for _ in keys)+')',[row[k] for k in keys])


def name_row(pid,name):
    return dict(playerid=pid,full=name,short=name,full_eng=name,short_eng=name,jersey=name.rsplit(' ',1)[-1])


def main():
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out=R/('build-'+stamp);out.mkdir()
    baseline={str(p):sha(p) for p in source_paths()};write(out/'source-baseline-initial.json',baseline)
    initial_http=(S/'http_config.py').read_text('utf8')
    source=read(R/'source-ready.json');cards=imported_cards();assert len(cards)==360
    assert all(p['official_latin_name'] for p in cards)
    assert not any(p['playerid'] in BLOCKED_PIDS for p in cards)
    original=S/'gamedata/fifadb.sqlite';database=out/'fifadb.sqlite';shutil.copyfile(original,database)
    registry=read(S/'gamedata/custom_rosters.json');policy=read(S/'gamedata/player-imports.json')
    assert not any(s['id']==SID for s in registry['seasons'])
    model_by_pid={p['playerid']:p for p in policy.get('models',[])}
    prior_prepare=sys.modules.get('prepare')
    try:
        sys.modules['prepare']=load(R.parent/'club-balance-live/prepare.py','ucl_analysis_prepare')
        rating_harness=load(R.parent/'club-balance-live/test.py','ucl_build_rating_harness')
        ns=rating_harness.functions(initial_http,original)
    finally:
        if prior_prepare is None:sys.modules.pop('prepare',None)
        else:sys.modules['prepare']=prior_prepare
    assert 'TC_ORDINARY_CLUB_BASE' not in (S/'http_config.py').read_text('utf8')
    db=sqlite3.connect(database);db.row_factory=sqlite3.Row
    templates={}
    for row in db.execute('select * from players order by spid'):templates.setdefault(row['playerid'],[]).append(dict(row))
    generic=source['generic_template'];generic_row=next(p for p in templates[generic['playerid']] if p['spid']==generic['source_spid'])
    fields=set(generic_row);stats=[p for p in cards[0]['source_attributes'] if p!='composure'];assert len(stats)==33
    registered=[];generic_players=[];new_names=[];added_history=0;teams={}
    current_names={p[0] for p in db.execute('select playerid from namesind')}
    main_name_tables={p[0] for p in db.execute("select name from sqlite_master where type='table' and name like 'names%'")}
    for p in cards:
        pid,sid=p['playerid'],p['source_spid'];assert sid==SID*1000000+pid
        assert not db.execute('select 1 from players where spid=?',(sid,)).fetchone()
        options=templates.get(pid,[])
        if p['native_existing']:
            if not options:raise ValueError('Native identity has no usable UI appearance '+str(pid))
            model=model_by_pid.get(pid)
            if model:
                template=next(row for row in options if row['headclasscode']==1 and row['headtypecode']==model['reserved_selector'])
            else:template=next((row for row in options if row['spid']==pid),options[-1])
        else:template=generic_row
        row=copy.deepcopy(template)
        row.update(spid=sid,playerid=pid,birthdate=p['birthdate'],height=p['height'],weight=p['weight'],
            preferredfoot=p['preferredfoot'],weakfootabilitytypecode=p['weakfootabilitytypecode'],skillmoves=p['skillmoves'],
            nationality=p['nationality'],nationalteamid=p['nationalteamid'],teamid=p['teamid'],leagueid=p['leagueid'],
            trait1=p['trait1'],trait2=0,badges=0,historyopen=1)
        for i,k in enumerate(('preferredposition1','preferredposition2','preferredposition3','preferredposition4')):
            row[k]=POSITIONS[p['source_positions'][i]] if i<len(p['source_positions']) else -1
        for k in stats:row[k]=int(p['source_attributes'][k]*MULTIPLIER+.5)
        role=ns['POS_ROLE'][row['preferredposition1']]
        base=sum(row[k]*v for k,v in ns['ROLE_WEIGHTS'][role].items())//100
        row['overallrating']=base+5;row['potential']=base+5
        assert set(row)==fields and row['skillmoves']==native_db.stars_to_code(p['source_skill_stars'])
        assert all(1<=row[k]<=99 for k in stats)
        insert(db,'players',row)
        for table in PERMISSIONS:
            if db.execute('select 1 from sqlite_master where name=?',(table,)).fetchone():insert(db,table,dict(spid=sid,licensed=1,transferable=1))
        if pid not in current_names:
            insert(db,'namesind',name_row(pid,p['official_latin_name']));current_names.add(pid);new_names.append(pid)
        for lang in LANGS:
            table='names'+lang
            if table in main_name_tables and not db.execute('select 1 from "'+table+'" where playerid=?',(pid,)).fetchone():
                insert(db,table,name_row(pid,p['name_ko'] if lang=='kor' else p['official_latin_name']))
        prior={tuple(r) for r in db.execute('select teamid,joinedyear,endyear,loan from playerhistory where playerid=?',(pid,))}
        order=db.execute('select coalesce(max(ordernum),-1) from playerhistory where playerid=?',(pid,)).fetchone()[0]
        for h in p['career']:
            key=tuple(h[k] for k in ('teamid','joinedyear','endyear','loan'))
            if key in prior:continue
            order+=1;insert(db,'playerhistory',dict(playerid=pid,ordernum=order,**h));prior.add(key);added_history+=1
        teams[p['teamid']]=(p['club_source_name'],p['leagueid'])
        registered.append(dict(fo3_spid=sid,base_playerid=pid,fc_spid=p['official_source_spid'],season_id=SID,season='25UCL',
            name_en=p['official_latin_name'],name_zh=(p['name_existing'] or {}).get('full') or p['official_latin_name'],
            source_url='https://fconline.nexon.com/DataCenter/PlayerInfo?spid='+str(p['official_source_spid']),source_sha256=p['source_sha256'],
            source_final_performance=True,ability_multiplier=MULTIPLIER,rounding='half-up',source_skill_stars=p['source_skill_stars'],
            native_plus1_ovr=base+5,base_position_rating=base,model_mode=p['appearance_route'],
            unsupported_source_traits=p['unsupported_source_traits'],import_version='25ucl-final-072-20261107'))
        if not p['native_existing']:
            generic_players.append(dict(playerid=pid,spid=sid,template_playerid=generic['playerid'],appearance_route='fo3_builtin_generic',
                native_spid_mode='identity',skill_input='fo3-code',source_sha256=p['source_sha256']))
    assert len(generic_players)==sum(not p['native_existing'] for p in cards)==87
    db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    db.execute('attach database ? as old',(original.as_posix(),))
    for (table,) in db.execute("select name from main.sqlite_master where type='table'").fetchall():
        assert not db.execute('select * from old."'+table+'" except select * from main."'+table+'" limit 1').fetchone(),table
    assert not db.execute('select 1 from players where playerid=231747').fetchone()
    db.close()
    registry['seasons'].append(dict(id=SID,label='25UCL',source='Nexon official final live-performance snapshot 2026-11-07',
        cards=[p['fo3_spid'] for p in registered],ability_multiplier=MULTIPLIER,excluded_playerids=sorted(BLOCKED_PIDS)))
    registry['cards'].extend(registered);write(out/'custom_rosters.json',registry);write(out/'cards.json',registered)
    write(out/'native-spec.json',dict(schema=1,generic_players=generic_players))
    archive=C/'data/data_0.big';changes={}
    old=bytes(codec.decrypt(bigdir.read(archive,'data/db2/fifadb.db.db2')))
    assert b'SQLite format 3\0'+old[16:]==original.read_bytes()
    encrypted=encrypt(old[:16]+database.read_bytes()[16:]);changes['data/db2/fifadb.db.db2']=(refpack(encrypted),len(encrypted))
    for lang in LANGS:
        member=f'data/db2/{lang}.db.db2';raw=bytes(codec.decrypt(bigdir.read(archive,member)))
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;db.deserialize(b'SQLite format 3\0'+raw[16:])
        for p in cards:
            if not db.execute('select 1 from names where playerid=?',(p['playerid'],)).fetchone():
                insert(db,'names',name_row(p['playerid'],p['name_ko'] if lang=='kor' else p['official_latin_name']))
        for tid,(name,lid) in teams.items():
            if not db.execute('select 1 from team where teamid=?',(tid,)).fetchone():insert(db,'team',dict(teamid=tid,teamname=name,leagueid=lid))
        db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok';plain=db.serialize();db.close()
        encrypted=encrypt(raw[:16]+plain[16:]);changes[member]=(refpack(encrypted),len(encrypted))
    ordered_big.rebuild(archive,out/'data_0.big',changes)
    # A distinct label key, no fake affiliation team and no season/ordinary bonus.
    locations=[(C/f'data/ui/localization/{lang}.big',f'localization/{lang}.big') for lang in LANGS]
    locations += [(C/f'_cache/{prefix}/externalAssets/language_{lang}.big',f'languages/{prefix}/language_{lang}.big') for prefix in ('games/fo3id','cdn') for lang in LANGS]
    locations += [(S/'patches/language_chi.big','language_chi.big')]
    display_names=read(S/'server_display_zh.json');new_team_labels={str(tid):name for tid,(name,lid) in teams.items() if str(tid) not in display_names['names_by_id']['TEAMNAMES_CHI.json']}
    for path,relative in locations:
        if not path.exists():continue
        target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);replacements={}
        for member,*_ in bigdir.entries(path):
            if 'LANGUAGESTRING' in member:
                values=__import__('json').loads(bigdir.read(path,member));assert display.KEY not in values
                values[display.KEY]='25UCL';replacements[member]=( __import__('json').dumps(values,ensure_ascii=False,separators=(',',':')).encode(),0)
            elif 'TEAMNAMES_' in member and new_team_labels:
                values=__import__('json').loads(bigdir.read(path,member));values.update({k:v for k,v in new_team_labels.items() if k not in values})
                replacements[member]=(__import__('json').dumps(values,ensure_ascii=False,separators=(',',':')).encode(),0)
        ordered_big.rebuild(path,target,replacements)
    central=out/'language_chi.big';check=read(S/'patches/验证结果.json')
    member=next(n for n,*_ in bigdir.entries(central) if 'LANGUAGESTRING' in n)
    check.update(sha256=sha(central),package_bytes=central.stat().st_size,result_keys=len(__import__('json').loads(bigdir.read(central,member))))
    write(out/'language-check.json',check)
    display_names['names_by_id']['TEAMNAMES_CHI.json'].update(new_team_labels);write(out/'server_display_zh.json',display_names)
    dropdown=read(S/'responses/static_roster.json');assert not any(SID in s.get('value',[]) for s in dropdown['seasons'])
    dropdown['seasons'].insert(0,dict(season='$'+display.KEY,value=[SID],open='2013-01-01T00:00:00.000Z',close='2099-12-31T00:00:00.000Z'))
    write(out/'static_roster.json',dropdown)
    display.build(out/'display')
    rebased=[]
    for path,digest in list(baseline.items()):
        actual=sha(path)
        if actual==digest:continue
        if Path(path)==S/'http_config.py':
            current_http=(S/'http_config.py').read_text('utf8');fresh=rating_harness.functions(current_http,original)
            assert fresh['ROLE_WEIGHTS']==ns['ROLE_WEIGHTS'] and fresh['POS_ROLE']==ns['POS_ROLE'],'Rating implementation changed; rebuild'
            assert 'TC_ORDINARY_CLUB_BASE' not in current_http
            rebased.append(dict(path=path,before=digest,after=actual,proof='UI/raw/native inputs unchanged; positional role weights identical; final HTTP delta will be prepared from this newer source.'))
            baseline[path]=actual
        else:raise ValueError('Fresh formal source changed; rebuild '+path)
    write(out/'source-baseline.json',baseline)
    if rebased:write(out/'source-rebase.json',dict(initial_observation='source-baseline-initial.json',changes=rebased))
    report=dict(status='UI_RESOURCES_BUILT_FOR_DIRECT_IMPORT',season=SID,cards=360,new_native=len(generic_players),new_names=len(new_names),
        new_history_rows=added_history,excluded_playerids=sorted(BLOCKED_PIDS),multiplier=MULTIPLIER,
        ordinary_extra_reward=0,season_exclusive_bonus=0,changed_data0_members=sorted(changes),
        input_hashes=baseline,database_sha256=sha(database),UI_archive_sha256=sha(out/'data_0.big'),
        native_full_validation='PENDING',formal_files_written=False,native_verified=False,match_verified=False)
    write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)))
    print('UI_BUILD_PASS',out,'cards=360; next: official native prepare and full validation')


if __name__=='__main__':main()
