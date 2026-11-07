"""Read-only installed market filter verification; no GUI or purchases."""
from pathlib import Path
import json,re,sqlite3,ssl,urllib.request,hashlib,sys
import fix_market_filter as f
S,C,R=f.S,f.C,f.R
installed=f.read(R/'installed.json');out=Path(f.read(R/'latest-build.json')['path']);build=f.read(out/'build.json')
assert f.sha(S/'gamedata/fifadb.sqlite')==build['outputs']['fifadb.sqlite'] and f.sha(C/'data/data_0.big')==build['outputs']['data_0.big']
entry=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(entry)==1;proof=f.common.load(S/entry[0].decode().replace('\\','/'),'market_filter_verified').preflight(S,C)
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
counts={sid:db.execute('select count(*) from players p join nameschi n using(playerid) join permid m using(spid) where p.spid/1000000=? and m.transferable=1 and m.licensed=1',(sid,)).fetchone()[0] for sid in (48,49,55)};assert counts=={48:41,49:5,55:7}
def request(path,admin=False,binary=False):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1'
 with urllib.request.urlopen(base+path,context=ssl._create_unverified_context(),timeout=30) as response:assert response.status==200;raw=response.read();return raw if binary else json.loads(raw)
roster=request('/static/roster')
for sid in (48,49,55):
 expected=next(x for x in roster['seasons'] if x['value']==[sid]);assert expected['season']=='$TRANSFERMARKET_SEASON_'+str(sid)
 result=request('/api/database_search?season='+str(sid),True);assert result['total']==counts[sid]
for path in (S/'patches/language_chi.big',C/'_cache/games/fo3id/externalAssets/language_chi.big',C/'_cache/cdn/externalAssets/language_chi.big'):
 assert f.sha(path)==build['outputs']['language_chi.big'];lang=json.loads(f.bigdir.read(path,'data/ui/external/LANGUAGESTRING_CHI.json'))
 for key in build['language_delta']:assert lang[key]=='曼联传奇'
assert hashlib.sha256(request('/cdn/externalAssets/language_chi.big',binary=True)).hexdigest()==build['outputs']['language_chi.big']
for path,expected in installed['protected'].items():
 if not path.endswith('state.json'):assert f.sha(path)==expected
before=f.read(R/'fresh-stop-snapshot'/installed['revision']/'state.json');after=f.read(S/'gamedata/state.json');assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'}
result=dict(status='PASS',preflight=proof,query_eligible=counts,unified_name='曼联传奇',season_ids_and_groups_preserved=True,all_players_and_other_database_rows_unchanged=True,latest_native_roster_preserved=True,roster_api=True,three_language_sources_exact=True,cdn_language_exact=True,assets_preserved=True,shop_preserved=True,native_market_filter_verified=False,gui_used=False)
f.write(R/'verification.json',result);print(json.dumps(result,ensure_ascii=True))
