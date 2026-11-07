"""Read-only audit of every custom roster identity and modern visual route."""
import hashlib,json,pathlib,sqlite3,sys,xml.etree.ElementTree as ET
R=pathlib.Path(__file__).resolve().parent
S=pathlib.Path('D:/FO3ID/server');C=pathlib.Path('D:/FO3ID/32795')
sys.path[:0]=[str(S/'tools/re')]
import bigdir,eadb
def main():
    registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'))
    db=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8');node=next(n for n in ET.fromstring(meta).iter('table') if n.get('name')=='players')
    fields={f.get('name'):f.attrib for f in node.iter('field')};_,names,raws=eadb.db_tables(db);t=eadb.Table(raws[names.index(node.get('shortname').encode())]);pidkey=fields['playerid']['shortname']
    native={t.get(r,pidkey):r for r in t.rows};con=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
    missing=[];invalid=[]
    for card in registry['cards']:
        pid=card.get('base_playerid');spid=card.get('fo3_spid');source=con.execute('SELECT * FROM players WHERE spid=?',(spid,)).fetchone()
        if source is None or source['playerid']!=pid:invalid.append(dict(playerid=pid,spid=spid,name=card.get('name_zh')))
        if pid not in native:missing.append(dict(playerid=pid,spid=spid,name=card.get('name_zh')))
    catalog=json.loads(pathlib.Path('D:/FO3QA/modern_player_integration_v2/model19-v4/model_catalog24.json').read_text('utf8'))
    visual=[]
    for p in catalog['players']:
        pid=p['playerid'];source=dict(con.execute('SELECT * FROM players WHERE spid=?',(p['local_spid'],)).fetchone());out_of_range=[]
        for name,f in fields.items():
            if name not in source or f['type']!='DBOFIELDTYPE_INTEGER':continue
            v=source[name];low=int(f['rangelow']);high=int(f['rangehigh'])
            if not low<=v<=high:out_of_range.append(dict(field=name,value=v,low=low,high=high))
        visual.append(dict(playerid=pid,spid=p['local_spid'],name=p['name_zh'],native_present=pid in native,selector=p.get('reserved_head_selector'),existing_db_rows=p.get('existing_db_rows'),source_out_of_native_range=out_of_range,catalog_keys=list(p)))
    result=dict(custom_cards=len(registry['cards']),custom_identities=len({p['base_playerid'] for p in registry['cards']}),native_rows=len(t.rows),native_unique_ids=len(native),missing_native=missing,invalid_registry=invalid,modern_players=visual,formal_written=False)
    (R/'current-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=True,indent=2))
if __name__=='__main__':main()
