from pathlib import Path
import copy,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'upstream-review/deps'))
from PIL import Image
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=json.loads((R/'portrait-manifest.json').read_text('utf8'))['players'];cases=[]
assert len(rows)==32 and len({r['spid'] for r in rows})==32 and len({r['playerid'] for r in rows})==32
assert len({r['native_sha256'] for r in rows})==32
cases.append('32 unique named photos and identities; no repeated/default avatar')
for r in rows:
 p=R/'native'/f'p{r["spid"]}.png';im=Image.open(p);im.load()
 assert im.format=='PNG' and im.mode=='RGBA' and im.size==(256,256) and im.getextrema()[3][1]>0
 assert sha(p)==r['native_sha256'] and r['caption'] and r['page_url'].startswith('https://')
 assert r['source_sha256'] and r['source_photograph_unchanged_in_content']
 cases.append(r['name']+' sourced PNG, bounds, hash and nonempty image')
old=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));new=json.loads((R/'custom_rosters.json').read_text('utf8'))
assert old.keys()==new.keys() and len(old['cards'])==len(new['cards'])
for k in old:
 if k!='cards':assert old[k]==new[k]
portrait_fields={'portrait_kind','portrait_source_url','portrait_image_url','portrait_source_sha256','portrait_native_sha256'}
for a,b in zip(old['cards'],new['cards']):
 if a['fo3_spid']//1000000!=327:assert a==b
 else:assert {k:v for k,v in a.items() if k not in portrait_fields}=={k:v for k,v in b.items() if k not in portrait_fields}
cases.append('Every prior season/identity/model/rating/physical field unchanged; only 32 portrait annotations differ')
baseline=json.loads((R/'baseline.json').read_text('utf8'))
for p in [S/'gamedata/fifadb.sqlite',S/'gamedata/player-imports.json',Path(r'D:\FO3ID\32795\data\data_0.big')]:assert sha(p)==baseline[str(p)]
cases.append('UI/native DB, body parameters and model/import policy files unchanged')
cert=json.loads((R/'staged-validation.json').read_text('utf8'));assert cert['status']=='PLAYER_IMPORT_FULL_PASS' and cert['input_hashes']['registry']==sha(R/'custom_rosters.json')
cases.append('Full strict import check uses prepared registry and original native resources')
assert all(cert['portrait_hashes'][str(R/'native'/f'p{r["spid"]}.png')]==r['native_sha256'] for r in rows)
cases.append('Full checker binds all 32 real-photo assets')
report=dict(status='PASS',case_count=len(cases),cases=cases,formal_files_written=False,native_gui_verified=False)
(R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(dict(status='PASS',cases=len(cases))))
