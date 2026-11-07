"""Build/check appended valuations using a read-only live market snapshot."""
import gzip,hashlib,shutil,sqlite3,json,datetime
from contextlib import closing
from common import *
import fair_value_model as value
import ucl25_value_extension as extension


def main():
    out=Path(read(R/'latest-build.json')['path']);dbpath=out/'fifadb.sqlite'
    # Keep removal's historical verification sidecar; never put retired rows back in gameplay.
    archive=S/'gamedata/removed-player-profiles.json'
    if archive.exists():shutil.copyfile(archive,out/archive.name)
    price_db=out/('market-regression-'+datetime.datetime.now().strftime('%H%M%S%f')+'.sqlite')
    if price_db.exists():raise ValueError('Regression snapshot exists; do not overwrite it')
    with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(price_db)) as target:source.backup(target)
    with closing(sqlite3.connect(price_db)) as db:
        meta=dict(db.execute('select key,value from metadata'))
        oldvalues={p[0]:tuple(p[1:]) for p in db.execute('select * from fair_values')}
        oldprices=list(db.execute('select * from prices order by spid'));oldseeds=list(db.execute('select * from seeds order by spid'))
        oldevents=list(db.execute('select * from price_events order by event_id'));oldfactors=list(db.execute('select * from player_market_factors order by playerid'))
    model=json.loads(meta['fair_model_json']);model['revision']='25ucl-final-072-v16-20261107'
    rows=value.verified_catalogue_rows(dbpath,model)
    details=[dict(spid=p['spid'],**value.explain(p,model)) for p in rows]
    newids=sorted(p['source_spid'] for p in imported_cards())
    cat=dict(schema=1,season=SID,cards=360,revision=model['revision'],expected_previous_revision=meta['fair_revision'],
        expected_previous_model_sha256=meta['fair_model_sha256'],model_sha256=hashlib.sha256(value.canonical(model)).hexdigest(),
        profile_sha256=value.profile_digest(rows,model),rows=details,new_spids=newids,source_sha256=sha(R/'source-ready.json'))
    expected={p['spid']:(p['playerid'],p['economic_value'],p['strict_floor_ep'],p['effective_score'],p['profile_sha256']) for p in details}
    assert {k:v for k,v in expected.items() if k in oldvalues}==oldvalues
    assert set(expected)-oldvalues.keys()==set(newids)
    write(out/'25ucl-value-model.json',model)
    (out/'25ucl-value-catalogue.json.gz').write_bytes(gzip.compress(json.dumps(cat,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    # Real-file hashes/values below are retained only as evidence, not deployed as a DB snapshot.
    proof=extension.apply(price_db,out/'25ucl-value-catalogue.json.gz',out/'25ucl-value-model.json',dbpath,runtime_source=dbpath)
    with closing(sqlite3.connect(price_db)) as db:
        def retained(table,key,prior):
            identities={r[0] for r in prior}
            return [p for p in db.execute('select * from '+table+' order by '+key) if p[0] in identities]==prior
        assert retained('prices','spid',oldprices)
        assert retained('seeds','spid',oldseeds)
        assert retained('price_events','event_id',oldevents)
        assert retained('player_market_factors','playerid',oldfactors)
    # Replay refuses before doing a second credit/seed insertion.
    try:extension.apply(price_db,out/'25ucl-value-catalogue.json.gz',out/'25ucl-value-model.json',dbpath)
    except ValueError as error:assert 'advanced' in str(error)
    else:raise AssertionError('Duplicate generation applied')
    result=dict(status='ADDITIVE_PRICE_REGRESSION_PASS',proof=proof,cards=360,existing_price_rows=len(oldprices),
        existing_prices_seeds_events_factors_identical=True,duplicate_apply_refused=True,
        model_sha256=sha(out/'25ucl-value-model.json'),catalogue_sha256=sha(out/'25ucl-value-catalogue.json.gz'),
        database_sha256=sha(dbpath),formal_files_written=False,state_shop_written=False)
    write(out/'price-tests.json',result);print('PRICE_REGRESSION_PASS: 360 appended; existing prices/seeds/events/factors preserved exactly.')


if __name__=='__main__':main()
