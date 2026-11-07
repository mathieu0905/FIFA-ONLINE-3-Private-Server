"""Regression checks on an explicit private copy; never write installed data."""
from pathlib import Path
from contextlib import closing
import json,shutil,sqlite3,sys,time
sys.dont_write_bytecode=True
import player_database as p
import publish_database as publish

root=p.HERE/'tests'/time.strftime('%Y%m%d-%H%M%S')
server=root/'server';client=root/'client';work=root/'work'
formal=Path('D:/FO3ID/server');game=Path('D:/FO3ID/32795')
protected={str(f):p.sha(f) for f in (formal/'gamedata/fifadb.sqlite',game/'data/data_0.big')}
for rel in ('http_config.py','extract_fifadb.py','tools/re/bigdir.py','tools/re/refpack.py','tools/check_data0_layout.py','gamedata/fifadb.sqlite'):
    dst=server/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(formal/rel,dst)
(client/'data').mkdir(parents=True);shutil.copyfile(game/'data/data_0.big',client/'data/data_0.big')
for name in ('state.json','shop.json'):(server/'gamedata'/name).write_text(json.dumps(dict(private_fixture=name)))
(server/'play-local.bat').write_bytes(b'python patches\\player_database_preflight.py\r\n')
(server/'patches').mkdir();shutil.copyfile(p.HERE/'database_preflight.py',server/'patches/player_database_preflight.py')
rows=[dict(root=r,relative=rel,sha256=p.sha(base/rel)) for r,base,rels in [('server',server,['http_config.py','gamedata/fifadb.sqlite','play-local.bat','patches/player_database_preflight.py']),('client',client,['data/data_0.big'])] for rel in rels]
p.write(server/'patches/player-database-installed.json',dict(schema=1,guards=rows,revision='PRIVATE_FIXTURE',client=str(client.resolve()),state_shop_replaced=False))
d=p.Database(server,client,work);checks=[]
def check(name,fn):
    fn();checks.append(name);print('PASS',name,flush=True)
def expect_error(fn):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('Expected rejection')
info=d.detail({'spid':93192181})
assert d.search({'q':'Basten'})['total']>=6
check('global search without owned cards',lambda:None)
check('unknown field rejected',lambda:expect_error(lambda:d.stage(dict(spid=93192181,row_hash=info['row_hash'],revision=0,changes={'spid':1}))))
check('fractional stat rejected',lambda:expect_error(lambda:d.stage(dict(spid=93192181,row_hash=info['row_hash'],revision=0,changes={'height':188.5}))))
check('out of range rejected',lambda:expect_error(lambda:d.stage(dict(spid=93192181,row_hash=info['row_hash'],revision=0,changes={'height':999}))))
result=d.stage(dict(spid=93192181,row_hash=info['row_hash'],revision=0,changes={'height':189,'sprintspeed':90},all_seasons=True))
assert len(result['draft']['cards'])==len(info['seasons'])>=6
check('same identity across seasons staged',lambda:None)
check('stale draft revision rejected',lambda:expect_error(lambda:d.stage(dict(spid=93192181,row_hash=info['row_hash'],revision=0,changes={'height':190}))))
assert p.sha(server/'gamedata/fifadb.sqlite')==protected[str(formal/'gamedata/fifadb.sqlite')]
check('draft never changes source database',lambda:None)
print('Building private dual-end database',flush=True)
out=work/'builds/private';manifest=d.build(d.draft(),out)
assert len(manifest['changes'])>=6 and p.read(out/'layout-report.json')['status']=='PASS'
check('full dual-end build, roundtrip, all tables and 270 non-target payloads',lambda:None)
check('wrong candidate digest rejected',lambda:expect_error(lambda:publish.apply(out,'0'*64)))
asset_hashes={n:p.sha(server/'gamedata'/n) for n in ('state.json','shop.json')}
# No live processes are controlled by the fixture publisher.
publish.game_closed=lambda:None
publish.listening=lambda port:False
installed=publish.apply(out,p.sha(out/'manifest.json'))
assert installed['status']=='installed'
with closing(sqlite3.connect(server/'gamedata/fifadb.sqlite')) as c:
    for spid in info['seasons']:assert c.execute('SELECT height,sprintspeed FROM players WHERE spid=?',(spid,)).fetchone()==(189,90)
assert all(p.sha(server/'gamedata'/n)==v for n,v in asset_hashes.items())
check('private publish synchronizes full DB and preserves state/shop',lambda:None)
check('stale candidate rejected after publication',lambda:expect_error(lambda:publish.apply(out,p.sha(out/'manifest.json'))))
for fail in range(1,6):
    fixture=root/('fault-'+str(fail));fixture.mkdir();pairs=[]
    for i in range(5):
        src=fixture/('source'+str(i));dst=fixture/('target'+str(i));src.write_bytes(b'new');dst.write_bytes(b'old');pairs.append((src,dst))
    expect_error(lambda:publish.transaction(pairs,fixture/'backup',lambda:None,fail_after=fail))
    assert all(dst.read_bytes()==b'old' for _,dst in pairs)
check('rollback at all five replacement boundaries',lambda:None)
assert all(p.sha(Path(f))==v for f,v in protected.items())
check('formal database and client unchanged',lambda:None)
p.write(root/'result.json',dict(status='PASS',checks=checks,formal_data_written=False,native_status='PENDING',candidate=str(out.resolve())))
print(json.dumps(dict(status='PASS',checks=len(checks),report=str((root/'result.json').resolve()))),flush=True)
