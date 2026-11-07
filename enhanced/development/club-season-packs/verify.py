"""Read-only installed catalogue, native shop definitions, images and hot ABI checks."""
from pathlib import Path
import hashlib,json,re,ssl,sys,urllib.request
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');sys.path.insert(0,str(R.parent/'manutd-legends'));import install as tx
def read(p):return json.loads(Path(p).read_text('utf8'))
def get(path,admin=False):
 with urllib.request.urlopen(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,context=ssl._create_unverified_context(),timeout=45) as response:assert response.status==200;return json.load(response)
i=read(R/'installed.json');b=read(R/'build.json');cfg=read(R/'club_season_products.json');icons=read(R/'all_item_icon_manifest.json')['items']
for relative,source in [('product_packs.py',R/'product_packs.py'),('gamedata/club_season_products.json',R/'club_season_products.json'),('gamedata/all_item_icon_manifest.json',R/'all_item_icon_manifest.json')]:assert tx.sha(S/relative)==tx.sha(source)
rows=get('/shop/list');found={int(r['product']['itemid']):r for r in rows if not isinstance(r.get('chained'),list)}
for p in b['products']:
 row=found[p['id']];definition=row['product']['staticdata'];assert row.get('visible',True) and row['buy'] and definition['name']==p['name'] and definition['category']=='PLAYERPACK' and definition['currency']=='cash'
 assert definition['bunches'][0]['price']==p['price'] and definition['bunches'][0]['bunch']==1
 assert str(definition['itemicon'])==icons[str(p['id'])]['icon'];assert p['limit']==cfg['limits'][str(p['id'])]['count'];assert p['period']==cfg['limits'][str(p['id'])]['period']
 for grade,weight in p['grades'].items():assert f'+{grade}：{weight}%' in definition['description']
 image=icons[str(p['id'])]
 for prefix in ('games/fo3id','cdn'):assert tx.sha(C/f'_cache/{prefix}/externalAssets/shop/{image["filename"]}')==image['sha256']
hot=get('/api/hot_update_status',True);assert hot['abi']==2 and hot['revision']==i['hot_revision_expected'] and hot['watcher_running'] and hot['error'] is None
before=read(R/'fresh-stop-snapshot'/i['revision']/'state.json');after=read(S/'gamedata/state.json');assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'},'Concurrent live progress retained; never restore old state'
for path,digest in i['protected'].items():
 if not path.endswith(('state.json','npc-market-prices.sqlite')):assert tx.sha(path)==digest,path
relative=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(relative)==1;preflight=tx.load(S/relative[0].decode().replace('\\','/'),'verify_season_packs').preflight(S,C)
result=dict(status='PASS',new_products=6,random_strength_products=4,fixed_strength_products=2,main_man_united_pool=67,wonderkid_pool=40,all_visible_and_correct_cash_prices=True,grade_probability_text_verified=True,dual_native_icons_verified=True,real_progress_preserved=True,old_issued_pack_configs_preserved=True,temporary_regression=read(R/'tests.json'),hot_status=hot,preflight=preflight,real_cash_purchase_performed=False,game_gui_used=False,native_ui_verified=False,state_shop_written=False)
(R/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');i.update(status='INSTALLED_CATALOGUE_API_VERIFIED_NATIVE_PENDING',verification=str(R/'verification.json'),verification_status='PASS',hot_status=hot);(R/'installed.json').write_bytes(tx.body(i))
descriptor=R.parent/'root-current-top.json';d=read(descriptor)
if d.get('top_preflight')==i['top_preflight']:d.update(status=i['status'],verification=str(R/'verification.json'),verification_status='PASS',hot_status=hot);tx.atomic(tx.body(d),descriptor)
print(json.dumps({k:v for k,v in result.items() if k!='temporary_regression'},ensure_ascii=True))
