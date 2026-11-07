import hashlib,json,pathlib,sys,xml.etree.ElementTree as ET
sys.path[:0]=['D:/FO3ID/server/tools/re','D:/FO3ID/server/tools']
import bigdir,eadb,check_data0_layout
R=pathlib.Path(__file__).resolve().parent;O=R/'native-roster';C=pathlib.Path('D:/FO3ID/32795/data/data_0.big')
build=json.loads((O/'build.json').read_text('utf8'));installed=json.loads((R/'native-roster-installed.json').read_text('utf8'))
baseline=next(pathlib.Path(installed['backup']).glob('*-data_0.big'))
db=bigdir.read(C,build['member']);node=next(t for t in ET.fromstring((R/'current-ea-db-meta.xml').read_text('utf8')).iter('table') if t.get('name')=='players')
_,names,raws=eadb.db_tables(db);idx=names.index(node.get('shortname').encode());t=eadb.Table(raws[idx]);key=next(f.get('shortname') for f in node.iter('field') if f.get('name')=='playerid')
matches=[row for row in t.rows if t.get(row,key)==252371];assert len(matches)==1 and hashlib.sha256(matches[0]).hexdigest()==build['added'][0]['raw_sha256']
_,onames,oraws=eadb.db_tables((R/'current-ea-db.db').read_bytes());old=eadb.Table(oraws[idx]);assert t.rows[:len(old.rows)]==old.rows
assert all(a==b for i,(a,b) in enumerate(zip(raws,oraws)) if i!=idx)
layout=check_data0_layout.inspect(C,baseline,{build['member']},271);assert layout['status']=='PASS'
out=dict(status='INSTALLED_NATIVE_ROSTER_RESOURCE_PASS',engine_bellingham_rows=len(matches),original_player_rows_preserved=len(old.rows),engine_total_player_rows=len(t.rows),original_other_tables_preserved=True,layout=layout,native_verified=False,match_verified=False)
(O/'installed-verification.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in out.items() if k!='layout'}))
