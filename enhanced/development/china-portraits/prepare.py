"""Bound real-photo assets to the native card texture size; no synthetic faces."""
from pathlib import Path
import copy,hashlib,io,json,sys,urllib.parse
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(R.parent/'upstream-review/deps'))
from PIL import Image
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 source=json.loads((R/'source-manifest.json').read_text('utf8'));assert len(source['players'])==32 and all(r['status']=='VERIFIED_NAMED_SOURCE_PHOTO' for r in source['players'])
 registry=S/'gamedata/custom_rosters.json';original=json.loads(registry.read_text('utf8'));new=copy.deepcopy(original)
 baseline={str(p):sha(p) for p in [registry,S/'gamedata/fifadb.sqlite',S/'gamedata/player-imports.json',S/'gamedata/player-import-validation.json',C/'data/data_0.big']}
 output=R/'native';output.mkdir(exist_ok=True);rows=[]
 for row in source['players']:
  row=copy.deepcopy(row);spid=row['spid'];path=R/'portraits'/f'p{spid}.png'
  if row['name']=='李昊炎':
   path=R/'damm-li.jpg';row.update(page_url='https://www.cfdamm.cat/ca/equip/persona/haoyan-li',resolved_image_url='https://www.cfdamm.cat/sites/default/files/styles/gallery_vertical_xxxs/public/content/person/528.JPG?h=3253cce3&itok=5iG7IiyJ',caption='Haoyan Li; official CF Damm player profile; 28 January 2012',source_sha256=sha(path),source_format='JPEG')
  image=Image.open(path).convert('RGBA');original_size=image.size
  # Standard texture import: preserve full image and aspect ratio, bound decoded
  # memory, use transparent padding. No cropping, face inference or retouching.
  image.thumbnail((256,256),Image.Resampling.LANCZOS)
  canvas=Image.new('RGBA',(256,256));canvas.paste(image,((256-image.width)//2,(256-image.height)//2),image)
  p=output/f'p{spid}.png';canvas.save(p)
  row.update(native_sha256=sha(p),native_size=[256,256],original_size=list(original_size),source_photograph_unchanged_in_content=True,texture_import='aspect-preserving downsample and transparent letterbox only; no crop, retouch, background removal or synthetic face')
  rows.append(row)
  card=next(c for c in new['cards'] if c['fo3_spid']==spid)
  assert card['base_playerid']==row['playerid'] and card['name_zh']==row['name']
  card.update(portrait_kind='verified_real_player_photo',portrait_source_url=row['page_url'],portrait_image_url=row['resolved_image_url'],portrait_source_sha256=row['source_sha256'],portrait_native_sha256=row['native_sha256'])
 assert len({r['native_sha256'] for r in rows})==32
 assert all(a==b for a,b in zip(original['cards'],new['cards']) if a['fo3_spid']//1000000!=327)
 assert original['seasons']==new['seasons']
 write(R/'custom_rosters.json',new);write(R/'portrait-manifest.json',dict(schema=1,edition='china-future-real-portraits-v1',players=rows,native_scene_verified=False))
 for row in rows:
  for directory in ['_cache/games/fo3id/externalAssets/players/','_cache/cdn/externalAssets/players/']:
   p=C/directory/f'p{row["spid"]}.png'
   baseline[str(p)]=sha(p) if p.exists() else None
 write(R/'baseline.json',baseline)
 print(json.dumps(dict(status='PHOTO_ASSETS_READY_NOT_INSTALLED',photos=32,native_texture='256x256',database_changed=False,models_changed=False)))
if __name__=='__main__':main()
