"""Explicit current-generation state maintenance; no asset restoration."""
from pathlib import Path
import copy, datetime, hashlib, json, sqlite3, sys, time
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'all-custom-households'))
import install as tx
sys.path.insert(0,str(tx.S))
from fair_value_store import migrate_state

def validate(before,after,revision):
    assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'}
    b=before['market_simulation'];a=after['market_simulation']
    allowed={'fair_revision','fair_revision_history','identity_quotes','price_events'}
    assert {k:v for k,v in b.items() if k not in allowed}=={k:v for k,v in a.items() if k not in allowed}
    assert a['fair_revision']==revision and a['price_events']==[]
    assert set(a['identity_quotes'])==set(b['identity_quotes'])
    for key,q in b['identity_quotes'].items():
        new=a['identity_quotes'][key]
        assert {k:v for k,v in q.items() if k not in ('pending','historical_price_samples')}=={k:v for k,v in new.items() if k not in ('pending','historical_price_samples')}
        expected=copy.deepcopy(q.get('historical_price_samples',[]))
        if q.get('pending'):expected.append(dict(revision=b['fair_revision'],pending=q['pending']))
        assert new.get('historical_price_samples',[])==expected and new['pending']==[]
    assert migrate_state(after,revision)==after

def prepare(body):
    before=json.loads(body)
    with sqlite3.connect((tx.S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        revision=dict(db.execute('select key,value from metadata'))['fair_revision']
        committed={r[0] for r in db.execute('select event_id from price_events')}
    pending=before['market_simulation'].get('price_events',[])
    assert all(e['event_id'] in committed for e in pending),'Uncommitted old price events require explicit replay; refuse to discard'
    after=migrate_state(before,revision)
    after['market_simulation']['price_events']=[]
    validate(before,after,revision)
    return after,dict(before=before['market_simulation']['fair_revision'],after=revision,already_committed_events=len(pending),preserved_pending_samples=sum(len(q.get('pending',[])) for q in before['market_simulation']['identity_quotes'].values()),assets_equal=True,idempotent=True)

def main():
    tx.assert_idle()
    # Exercise the real migration and asset preservation on detached data first.
    prepare((tx.S/'gamedata/state.json').read_bytes())
    with tx.locks():
        tx.assert_idle()
        oldhot=tx.get('http://127.0.0.1:8088/api/hot_update_status')
        tx.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',tx.S/'stop-server.ps1'])
        deadline=time.monotonic()+15
        while tx.listening():
            if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no writes')
            time.sleep(.2)
        try:
            tx.assert_idle()
            state=tx.S/'gamedata/state.json';shop=tx.S/'gamedata/shop.json'
            body=state.read_bytes();shopbody=shop.read_bytes();after,proof=prepare(body)
            backup=tx.S/'backups'/('startup-market-migration-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
            backup.mkdir();(backup/'fresh-state.json').write_bytes(body);(backup/'fresh-shop.json').write_bytes(shopbody)
            tx.assert_idle()
            assert state.read_bytes()==body and shop.read_bytes()==shopbody
            tx.atomic(tx.encoded(after),state)
            validate(json.loads(body),json.loads(state.read_bytes()),proof['after'])
            assert shop.read_bytes()==shopbody
            proof.update(backup=str(backup),state_before_sha256=tx.digest(body),state_after_sha256=tx.current_hash(state),shop_sha256=tx.digest(shopbody),status='MIGRATED',GUI_used=False)
            (R/'market-migration.json').write_bytes(tx.encoded(proof))
        finally:
            if not tx.listening():tx.restart()
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        hot=tx.get('http://127.0.0.1:8088/api/hot_update_status')
        if hot.get('watcher_running') and hot.get('revision')==oldhot['revision'] and hot.get('error') is None:break
        time.sleep(.3)
    assert hot['routes']==oldhot['routes'] and hot['revision']==oldhot['revision'] and hot['watcher_running'] and hot['error'] is None
    proof.update(hot_update=hot,services_restored=True)
    (R/'market-migration.json').write_bytes(tx.encoded(proof));print(json.dumps(proof))

if __name__=='__main__':main()
