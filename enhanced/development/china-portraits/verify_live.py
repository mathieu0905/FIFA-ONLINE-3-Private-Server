"""Read-only installed avatar and dual-cache verification; no game GUI."""
from pathlib import Path
import hashlib,io,json,ssl,sys,urllib.request
import install as m
sys.path.insert(0,str(m.R.parent/'upstream-review/deps'))
from PIL import Image
R=m.R;S=m.S;C=m.C
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def main():
 report=json.loads((R/'installed-handback.json').read_text('utf8'));manifest=json.loads((R/'portrait-manifest.json').read_text('utf8'))
 helper=m.d.load(S/m.SELF,'verify_real_portraits_gate');proof=helper.preflight(S,C)
 validator=m.d.load(S/'patches/startup_market_preflight.py','verify_real_portraits_composition');validator.verify_manifest(helper.compose_manifest(S,C),S,C)
 verified=[]
 for row in manifest['players']:
  name=f'p{row["spid"]}.png';expected=row['native_sha256']
  for directory in ['_cache/games/fo3id/externalAssets/players/','_cache/cdn/externalAssets/players/']:assert m.sha(C/directory/name)==expected
  with opener.open('https://127.0.0.1/cdn/externalAssets/players/'+name,timeout=10) as response:
   assert response.status==200;body=response.read()
  assert hashlib.sha256(body).hexdigest()==expected
  im=Image.open(io.BytesIO(body));assert im.size==(256,256) and im.format=='PNG'
  verified.append(dict(name=row['name'],spid=row['spid'],http_status=200,dual_cache_hash_pass=True))
 old=json.loads((R/'custom_rosters.json').read_text('utf8'));current=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));assert current==old
 cert=json.loads((S/m.CERT).read_text('utf8'));assert cert['status']=='PLAYER_IMPORT_FULL_PASS'
 for row in manifest['players']:
  for directory in ['_cache/games/fo3id/externalAssets/players/','_cache/cdn/externalAssets/players/']:
   p=C/directory/f'p{row["spid"]}.png';assert cert['portrait_hashes'][str(p)]==row['native_sha256']
 hot=m.d.base.hot_status();assert hot==report['hot_update_status'] and hot['watcher_running'] and hot['error'] is None
 report.update(status='REAL_PORTRAITS_INSTALLED_HTTP_VERIFIED_NATIVE_PENDING',photos_verified=verified,preflight=proof,full_player_import='PASS',certificate_binds_both_caches=True,native_gui_verified=False,services_restarted=False,regression_checks=42)
 (R/'live-verification.json').write_bytes(m.encoded(report));(R/'installed-handback.json').write_bytes(m.encoded(report))
 print(json.dumps({k:v for k,v in report.items() if k!='photos_verified'},ensure_ascii=True))
if __name__=='__main__':main()
