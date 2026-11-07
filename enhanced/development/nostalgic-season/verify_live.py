"""Read-only checks of the installed season and live 8088/HTTPS integration."""
from pathlib import Path
import argparse,hashlib,json,sqlite3,ssl,sys,time,urllib.parse,urllib.request
sys.stdout.reconfigure(encoding='utf-8');R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def business():
 st=read(S/'gamedata/state.json');return {k:digest(v) for k,v in st.items() if k!='market_simulation'}
def req(path,admin=True,json_response=True):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1'
 with urllib.request.urlopen(base+path,context=ssl._create_unverified_context(),timeout=30) as r:
  b=r.read();assert r.status==200
  return json.loads(b) if json_response else b
def main(before=False):
 if before:
  result=dict(business=business(),shop_sha256=hashlib.sha256((S/'gamedata/shop.json').read_bytes()).hexdigest());(R/'before-install-assets.json').write_text(json.dumps(result,indent=2),'utf-8');print('Captured asset fingerprints without writing formal files');return
 spec=read(R/'build-v2/database/spec.json');wanted={19000000+c['base_playerid'] for c in spec['cards']}
 status=req('/api/database_status');assert status['count']==60766,status.get('count')
 assert 19 in status['seasons'] and '怀旧神兽' in status['season_labels']['19']
 found=[]
 for offset in (0,50):
  result=req('/api/database_search?season=19&offset='+str(offset));assert result['total']==88
  found.extend(result['rows'])
 assert {r['spid'] for r in found}==wanted
 detail_checks=[]
 for name in ('博格巴','博德梅尔','德罗巴','瓦拉内','罗霍','麦孔','诺伊尔'):
  c=next(c for c in spec['cards'] if c['name_zh']==name);spid=19000000+c['base_playerid'];detail=req('/api/database_detail?spid='+str(spid))
  assert all(detail['row'][k]==v for k,v in c['fo3_overrides'].items()),name
  detail_checks.append(dict(name=name,spid=spid,ovr=detail['ovr'],height=detail['row']['height'],weight=detail['row']['weight']))
 roster=req('/static/roster',admin=False);assert any(s['value']==[19] for s in roster['seasons'])
 registry=req('/api/roster_custom_cards');season=next(x for x in registry['seasons'] if x['id']==19);assert set(season['cards'])==wanted
 # CDN GETs are read-only; check every installed season-specific face.
 for spid in sorted(wanted):assert req('/cdn/externalAssets/players/p'+str(spid)+'.png',admin=False,json_response=False).startswith(b'\x89PNG')
 prior=read(R/'before-install-assets.json');after=business();assert after==prior['business'],'Business asset fingerprints differ'
 assert hashlib.sha256((S/'gamedata/shop.json').read_bytes()).hexdigest()==prior['shop_sha256']
 report=dict(status='LIVE_READ_ONLY_PASS',cards=88,total_database_cards=60766,season='19 · 怀旧神兽',details=detail_checks,all_88_faces_served=True,registry_and_roster=True,business_assets_unchanged=True,shop_unchanged=True,publish_readiness=status.get('publish_readiness'),native_verified=False,match_verified=False)
 (R/'live-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--before',action='store_true');a=p.parse_args();main(a.before)
