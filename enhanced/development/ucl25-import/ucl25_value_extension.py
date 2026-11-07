"""Atomic additive price generation; never rewrites any existing trade/price row."""
from contextlib import closing
from pathlib import Path
import gzip,hashlib,json,sqlite3,time


def packet(path):
    with gzip.open(path,'rt',encoding='utf8') as stream:value=json.load(stream)
    if value.get('schema')!=1 or value.get('season')!=856 or value.get('cards')!=360:
        raise ValueError('Invalid 25UCL market extension')
    return value


def apply(database,catalogue_path,model_path,source_database,runtime_source=None):
    from fair_value_model import canonical,verify_profiles
    model=json.loads(Path(model_path).read_text('utf8'));cat=packet(catalogue_path)
    verify_profiles(source_database,cat,model)
    expected={r['spid']:r for r in cat['rows']};newids=set(cat['new_spids'])
    if len(newids)!=360 or any(s//1000000!=856 or s%1000000==231747 for s in newids):raise ValueError('Invalid new card set')
    if hashlib.sha256(canonical(model)).hexdigest()!=cat['model_sha256']:raise ValueError('Model hash differs')
    with closing(sqlite3.connect(database,timeout=30)) as db:
        db.execute('begin immediate')
        try:
            meta=dict(db.execute('select key,value from metadata'))
            if meta.get('fair_revision')!=cat['expected_previous_revision'] or meta.get('fair_model_sha256')!=cat['expected_previous_model_sha256']:
                raise ValueError('Current price generation advanced; rebuild against current parent')
            old=list(db.execute('select spid,playerid,economic_value,strict_floor,effective_score,profile_sha256 from fair_values'))
            if set(expected)!={r[0] for r in old}|newids:raise ValueError('Catalogue is not the exact old-plus-new generation')
            for sid,pid,economic,floor,score,profile in old:
                r=expected[sid]
                if (pid,economic,floor,score,profile)!=(r['playerid'],r['economic_value'],r['strict_floor_ep'],r['effective_score'],r['profile_sha256']):
                    raise ValueError('Existing card would be repriced '+str(sid))
            if any(db.execute('select 1 from seeds where spid=?',(sid,)).fetchone() for sid in newids):raise ValueError('New card seed already exists')
            if db.execute('select 1 from fair_generation_history where revision=?',(meta['fair_revision'],)).fetchone():
                raise ValueError('Current generation already archived; inspect revision reuse')
            db.execute('insert into fair_generation_history values(?,?,?,?)',(meta['fair_revision'],meta['fair_model_sha256'],meta['fair_profile_sha256'],meta['fair_model_json']))
            db.executemany('insert into fair_value_history values(?,?,?,?,?,?,?)',[(meta['fair_revision'],*row) for row in old])
            factors=dict(db.execute('select playerid,factor from player_market_factors'));stamp=time.time()
            for sid in sorted(newids):
                row=expected[sid];pid=row['playerid'];factor=factors.get(pid,1.)
                if pid not in factors:
                    db.execute('insert into player_market_factors values(?,?,?,?)',(pid,1.,stamp,'season_import_25ucl'));factors[pid]=1.
                current=round(row['economic_value']*factor)+row['strict_floor_ep'];initial=row['fair_price_ep']
                event='season-import:'+cat['revision']+':'+str(sid)
                db.execute('insert into seeds values(?,?,?,?)',(sid,initial,cat['model_sha256'],stamp))
                db.execute('insert into prices values(?,?,?,?,?)',(sid,float(current),current,stamp,event))
                db.execute('insert into price_events values(?,?,?,?,?,?,?)',(event,sid,0.,float(current),stamp,'new_season_import',
                    json.dumps(dict(model_sha256=cat['model_sha256'],source_sha256=cat['source_sha256']),separators=(',',':'))))
                db.execute('insert into fair_values values(?,?,?,?,?,?)',(sid,pid,row['economic_value'],row['strict_floor_ep'],row['effective_score'],row['profile_sha256']))
            updates=dict(fair_revision=cat['revision'],fair_model_sha256=cat['model_sha256'],fair_profile_sha256=cat['profile_sha256'],
                fair_model_json=json.dumps(model,separators=(',',':')),fair_source_database=str(Path(runtime_source or source_database).resolve()))
            db.executemany('insert or replace into metadata values(?,?)',updates.items());db.commit()
        except BaseException:db.rollback();raise
    return verify(database,catalogue_path,model_path,source_database)


def verify(database,catalogue_path,model_path,source_database):
    from fair_value_store import verify_installed
    cat=packet(catalogue_path)
    proof=verify_installed(database,catalogue_path,model_path,source_database)
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        for sid in cat['new_spids']:
            if not db.execute('select 1 from seeds where spid=? and model_sha256=?',(sid,cat['model_sha256'])).fetchone():raise ValueError('New seed receipt missing')
            event='season-import:'+cat['revision']+':'+str(sid)
            if not db.execute('select 1 from price_events where event_id=? and spid=? and reason=?',(event,sid,'new_season_import')).fetchone():raise ValueError('New price event missing')
    return dict(status='25UCL_PRICE_GENERATION_PASS',cards=360,old_prices_replaced=False,**dict(fair_generation=proof))
