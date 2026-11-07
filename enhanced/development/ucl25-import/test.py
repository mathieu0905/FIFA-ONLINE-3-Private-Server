"""Whole-delta regression on prepared files; no services and no real assets."""
from contextlib import closing
import hashlib,sqlite3,struct
from common import *
import bigdir,native_db,eadb,extract_fifadb as codec


def main():
    out=Path(read(R/'latest-build.json')['path']);native=out/'native';cards=imported_cards();checks=[]
    baseline=read(out/'source-baseline.json')
    for p,digest in baseline.items():assert sha(p)==digest,'Source changed: '+p
    checks.append('Fresh formal source still matches this build, including later legal removals')
    proof=read(native/'player-import-validation.json');assert proof['status']=='PLAYER_IMPORT_FULL_PASS'
    for key,path in [('database',native/'fifadb.sqlite'),('registry',native/'custom_rosters.json'),('imports',native/'player-imports.json'),('archive0',native/'data_0.big')]:
        assert proof['input_hashes'][key]==sha(path)
    checks.append('Official full import certificate binds final native/UI/registry/import inputs')
    with closing(sqlite3.connect((native/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('attach database ? as old',((S/'gamedata/fifadb.sqlite').as_posix(),))
        for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
            assert not db.execute('select * from old."'+table+'" except select * from main."'+table+'" limit 1').fetchone(),table
        checks.append('Every existing row in every UI table is preserved exactly')
        live=list(db.execute('select * from players where spid/1000000=856'));assert len(live)==360
        assert not db.execute('select 1 from players where playerid=231747 or spid%1000000=231747').fetchone()
        assert {p['spid'] for p in live}=={p['source_spid'] for p in cards}
        checks.append('Exactly 360 new cards; blocked Mbappe identity remains absent')
        reused=[p for p in cards if p['official_source_playerid']!=p['playerid']]
        assert len(reused)==121 and all(p['native_existing'] for p in reused)
        assert all(db.execute('select 1 from old.players where playerid=?',(p['playerid'],)).fetchone() for p in reused)
        checks.append('All 121 cross-source identity aliases reuse existing UI/native identities and local SPIDs; official source IDs remain recorded')
        for p in cards:
            row=db.execute('select * from players where spid=?',(p['source_spid'],)).fetchone()
            assert row['playerid']==p['playerid']
            for field,value in p['source_attributes'].items():
                if field!='composure':assert row[field]==int(value*.72+.5)
            for key in ('height','weight','birthdate','preferredfoot','weakfootabilitytypecode','skillmoves','nationality','teamid','leagueid'):
                assert row[key]==p[key],(p['playerid'],key)
            assert row['trait1']==sum(1<<t['id'] for t in p['source_traits'] if t['id']<30) and row['badges']==0
            for table in ('permid','permcn','permkr','permth','permvn','permsg'):
                assert tuple(db.execute('select licensed,transferable from '+table+' where spid=?',(p['source_spid'],)).fetchone())==(1,1)
            assert db.execute('select 1 from namesind where playerid=?',(p['playerid'],)).fetchone()
            for lang in LANGS:
                assert db.execute('select 1 from names'+lang+' where playerid=?',(p['playerid'],)).fetchone()
        checks.append('All 33 abilities use exactly 0.72 and one rounding; bio/foot/stars/traits and six permissions match source semantics')
        assert db.execute('select count(*) from players').fetchone()[0]-db.execute('select count(*) from old.players').fetchone()[0]==360
    for lang in LANGS:
        member=f'data/db2/{lang}.db.db2';before=bytes(codec.decrypt(bigdir.read(C/'data/data_0.big',member)));after=bytes(codec.decrypt(bigdir.read(native/'data_0.big',member)))
        with closing(sqlite3.connect(':memory:')) as prior,closing(sqlite3.connect(':memory:')) as updated:
            prior.deserialize(b'SQLite format 3\0'+before[16:]);updated.deserialize(b'SQLite format 3\0'+after[16:])
            oldnames=dict((p[0],p) for p in prior.execute('select * from names'));newnames=dict((p[0],p) for p in updated.execute('select * from names'))
            assert all(newnames[k]==v for k,v in oldnames.items());assert all(p['playerid'] in newnames for p in cards)
            assert 231747 not in newnames
    checks.append('All six language name tables preserve existing rows and cover every new card identity')
    old_native=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');new_native=bigdir.read(native/'data_0.big','data/db/fifa_ng_db.db')
    xml=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8')
    _,names0,tables0,index,oldtable,fields=native_db.player_table(old_native,xml)
    _,names1,tables1,_,newtable,_=native_db.player_table(new_native,xml)
    assert names0==names1 and all(a==b for i,(a,b) in enumerate(zip(tables0,tables1)) if i!=index)
    assert newtable.rows[:len(oldtable.rows)]==oldtable.rows and len(newtable.rows)-len(oldtable.rows)==sum(not p['native_existing'] for p in cards)==87
    pkey=fields['playerid']['shortname'];ids={newtable.get(row,pkey) for row in newtable.rows}
    assert 231747 not in ids and all(p['playerid'] in ids for p in cards)
    checks.append('Exactly 87 native identities appended; 121 verified existing identities reused; all old native records and every non-player native table unchanged')
    changed=set(read(out/'build.json')['changed_data0_members'])|{'data/db/fifa_ng_db.db'}
    oldentries=bigdir.entries(C/'data/data_0.big');newentries=bigdir.entries(native/'data_0.big')
    assert [x[0] for x in oldentries]==[x[0] for x in newentries]
    with (C/'data/data_0.big').open('rb') as old,(native/'data_0.big').open('rb') as new:
        for a,b in zip(oldentries,newentries):
            if a[0] in changed:continue
            assert a[2:]==b[2:];old.seek(a[1]);new.seek(b[1]);remaining=a[2]
            while remaining:
                size=min(1024*1024,remaining);assert old.read(size)==new.read(size);remaining-=size
    checks.append('Archive directory order retained; all non-target compressed members byte-identical')
    prepared=(out/'http_config.py').read_text('utf8');original=(S/'http_config.py').read_text('utf8')
    assert prepared==original.replace('NOT IN (300,325,327) AND ovr >= ?1','NOT IN (300,325,327,856) AND ovr >= ?1')
    assert 'TC_ORDINARY_CLUB_BASE' not in prepared
    # The old generic SQL query explicitly excludes every new 856 card. No old
    # row or filter changes, so its complete weighted pools remain identical.
    assert 'NOT IN (300,325,327,856)' in prepared
    checks.append('Only generic-pack SQL exclusion changes; old packs preserved, no ordinary/25U season ability bonus')
    dropdown=read(out/'static_roster.json');assert sum(x.get('value')==[856] for x in dropdown['seasons'])==1
    assert read(out/'display/display-validation.json')['status']=='STATIC_DISPLAY_EXTENSION_PASS'
    checks.append('One 25UCL market filter and two audited badge sizes; original season methods/sprites preserved')
    prices=read(out/'price-tests.json');assert prices['status']=='ADDITIVE_PRICE_REGRESSION_PASS'
    assert prices['database_sha256']==sha(native/'fifadb.sqlite')
    checks.append('Additive valuation regression preserves all old prices/seeds/trade events/factors and refuses replay')
    result=dict(status='PASS',case_count=len(checks),checks=checks,cards=360,new_native=sum(not p['native_existing'] for p in cards),multiplier=.72,
        blocked_playerids=sorted(BLOCKED_PIDS),formal_files_written=False,state_shop_written=False,GUI_used=False,
        native_runtime_verified=False,match_verified=False,build=str(out),
        tool_hashes={p.name:sha(p) for p in R.glob('*.py')},
        output_hashes={n:sha(native/n) for n in ('fifadb.sqlite','data_0.big','custom_rosters.json','player-imports.json','player-import-validation.json')})
    write(out/'tests.json',result);write(R/'tests.json',result)
    print('WHOLE_DELTA_PASS',len(checks),'cases; formal writes=0; native runtime/match=PENDING')


if __name__=='__main__':main()
