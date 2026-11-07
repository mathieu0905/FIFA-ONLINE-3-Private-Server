"""Checked retirement install; preserve current assets and all historical release identities."""
from pathlib import Path
import contextlib, datetime, hashlib, importlib.util, json, shutil, sqlite3, sys, types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
SERVER=Path('D:/FO3ID/server'); CLIENT=Path('D:/FO3ID/32795')
OUT=ROOT/'releases/fc13-retire-ronaldinho-v2'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
tx=load('fc_transaction',ROOT/'install_bulk_seasons.py')
m=tx.read(OUT/'fc-retirement-release-manifest.json')
def test():
    market=load('fc_test_market',SERVER/'market_simulation.py')
    patch=load('fc_test_exclusion',OUT/'legend_moments_bulk_npc.py')
    db=lambda:sqlite3.connect((SERVER/'gamedata/fifadb.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    ids=frozenset([13028130,12028130,84028130,13158023])
    h=types.SimpleNamespace(HERE=str(OUT),player_value_price=lambda *a:1,MAX_GRADE=20,
        on_market=lambda s:True,closing=contextlib.closing,_db=db,market_spids=lambda:ids,
        card_ovrs=lambda rows:{s:90 for s in rows})
    h.market_engine=market.Market(h)
    # Registry filename in the candidate is also the runtime basename.
    sandbox=OUT/'test-runtime';(sandbox/'gamedata').mkdir(parents=True,exist_ok=True)
    shutil.copyfile(OUT/'custom_rosters.json',sandbox/'gamedata/custom_rosters.json');h.HERE=str(sandbox)
    engine=patch.install(h)
    assert set(engine.candidates())=={12028130,13158023}
    state={'market_simulation':{'books':{'13028130':{'epoch':1,'rows':[{'grade':1,'stock':1}]}}}}
    original=json.dumps(state,sort_keys=True)
    assert engine.book(state,13028130,1000)['rows']==[]
    assert json.dumps(state,sort_keys=True)==original
    assert engine.valid_card(13028130), 'Old pack compatibility must remain valid'
    assert engine.valid_card(12028130) and engine.valid_card(84028130)
    assert len(engine._legend_moments_bulk_npc_exclusion)==124
    assert patch.install(h) is engine
    for file in ('fc_retirement_preflight.py','legend_moments_bulk_npc.py'):
        compile((OUT/file).read_text('utf-8'),file,'exec')
    print('PASS: active roster, actual market candidates, stale NPC book exclusion, legacy validity, legend cards, idempotence',flush=True)
def install():
    tx.stopped()
    parent=load('fc_parent',SERVER/'patches/player_value_preflight.py');parent.preflight()
    backup=SERVER/'backups'/('fc13-retirement-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    entries=list(m['files'])
    receipt=dict(status='INSTALLED_FC13_RETIREMENT',release_id=m['release_id'],manifest_sha256=tx.sha(OUT/'fc-retirement-release-manifest.json'),backup=str(backup),retired_spid=13028130,active_fc_cards=257,legacy_pack_pools_unchanged=True,native_status='PENDING')
    tx.atomic_json(OUT/'fc-retirement-release-installed.json',receipt)
    for name in ('fc-retirement-release-manifest.json','fc-retirement-release-installed.json'):
        assert not (SERVER/'patches'/name).exists()
        entries.append(dict(root='server',relative='patches/'+name,source=str(OUT/name),sha256=tx.sha(OUT/name),parent_sha256=None))
    protected={n:tx.sha(SERVER/n) for n in ('gamedata/state.json','gamedata/shop.json','gamedata/pack_cadence.json','gamedata/pack_catalogue.json','gamedata/fifadb.sqlite')}
    roots={'server':SERVER,'client':CLIENT}
    result=tx.commit_transaction(roots,entries,backup,lambda:parent.preflight())
    try:
        check=load('fc_installed',SERVER/'patches/fc_retirement_preflight.py').preflight()
        assert all(tx.sha(SERVER/n)==digest for n,digest in protected.items())
    except BaseException:
        tx.restore_completed(roots,result,backup)
        raise
    result['status']='committed';tx.atomic_json(backup/'transaction.json',result)
    tx.atomic_json(OUT/'installation-PASS.json',dict(status='INSTALLED_PROTOCOL_PENDING',backup=str(backup),preflight=check,protected_hashes=protected))
    print(json.dumps({'status':'INSTALLED_FC13_RETIREMENT','backup':str(backup),'files_verified':check['files']},ensure_ascii=True))
if __name__=='__main__':
    test()
    if '--apply' in sys.argv:install()
