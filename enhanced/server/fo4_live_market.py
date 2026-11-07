"""Append-only price seeds for newly imported seasons; never reprices existing cards."""
from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
import time


def packet(path):
    value=json.loads(Path(path).read_text('utf8'))
    assert value['schema']==1 and value['revision']=='fo4-live-25-26-upstream-ed08cf1'
    assert len(value['rows'])==688 and len({r[0] for r in value['rows']})==688
    assert all(type(s) is int and s//1000000 in (300,325) and type(p) is int and 1<=p<=5600000000000000 for s,p in value['rows'])
    assert hashlib.sha256(json.dumps(value['rows'],separators=(',',':')).encode()).hexdigest()==value['prices_sha256']
    return value


def verify(database,source):
    value=packet(source)
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as con:
        for sid,price in value['rows']:
            row=con.execute('select initial_price,model_sha256 from seeds where spid=?',(sid,)).fetchone()
            assert row==(price,value['model_sha256']), 'New-season immutable seed mismatch'
            event='season-import:'+value['revision']+':'+str(sid)
            row=con.execute('select spid,before_price,after_price,reason from price_events where event_id=?',(event,)).fetchone()
            assert row==(sid,0.,float(price),'new_season_import'), 'New-season import receipt differs'
            assert con.execute('select count(*) from prices where spid=? and basis_price>=1 and current_price>=1',(sid,)).fetchone()[0]==1
    return dict(status='FO4_LIVE_PRICE_EXTENSION_PASS',rows=688,model_sha256=value['model_sha256'],existing_prices_replaced=False)


def apply(database,source):
    value=packet(source)
    with closing(sqlite3.connect(database,timeout=30)) as con:
        con.execute('begin immediate')
        try:
            for sid,price in value['rows']:
                if con.execute('select 1 from seeds where spid=?',(sid,)).fetchone():
                    raise ValueError('New-season seed already exists; inspect before retry')
            stamp=time.time()
            for sid,price in value['rows']:
                event='season-import:'+value['revision']+':'+str(sid)
                evidence=json.dumps(dict(source_sha256=value['source_sha256'],model_sha256=value['model_sha256']),separators=(',',':'))
                con.execute('insert into seeds values(?,?,?,?)',(sid,price,value['model_sha256'],stamp))
                con.execute('insert into prices values(?,?,?,?,?)',(sid,float(price),price,stamp,event))
                con.execute('insert into price_events values(?,?,?,?,?,?,?)',(event,sid,0.,float(price),stamp,'new_season_import',evidence))
            con.commit()
        except BaseException:
            con.rollback();raise
    return verify(database,source)


def rollback(database,source):
    """Allowed only by the installer while services remain stopped."""
    value=packet(source)
    verify(database,source)
    with closing(sqlite3.connect(database,timeout=30)) as con,con:
        for sid,price in value['rows']:
            event='season-import:'+value['revision']+':'+str(sid)
            row=con.execute('select basis_price,current_price,last_event from prices where spid=?',(sid,)).fetchone()
            if row!=(float(price),price,event):raise RuntimeError('Later price progress retained; rollback refused')
            if con.execute('select count(*) from price_events where spid=?',(sid,)).fetchone()[0]!=1:raise RuntimeError('Later trade receipt retained; rollback refused')
        for sid,price in value['rows']:
            con.execute('delete from price_events where event_id=?',('season-import:'+value['revision']+':'+str(sid),))
            con.execute('delete from prices where spid=?',(sid,))
            con.execute('delete from seeds where spid=?',(sid,))
