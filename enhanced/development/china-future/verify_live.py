"""Read-only verification; never grants cards or changes managers/inventory."""
from pathlib import Path
import json,sqlite3,ssl,urllib.request,urllib.parse
import install
R=install.R;S=install.S;C=install.C
def get(url):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
 with opener.open(url,timeout=15) as r:assert r.status==200;return json.load(r)
def main():
 h=install.load(S/install.SELF,'live_china_future_gate');proof=h.preflight(S,C)
 parent=install.load(S/'patches/startup_market_preflight.py','china_future_combined_verify');parent.verify_manifest(h.compose_manifest(S,C),S,C)
 roster=get('https://127.0.0.1/static/roster');assert any(327 in r['value'] and r['season']=='中国明日之星' for r in roster['seasons'])
 cards=json.loads((R/'input/cards.json').read_text('utf8'));found=[]
 for card in cards:
  data=get('http://127.0.0.1:8088/api/search?'+urllib.parse.urlencode({'q':card['name_zh']}))
  row=next(r for r in data['rows'] if r['spid']==card['fo3_spid'])
  assert row['market'] and row['price']>0 and row['ovr']+5==card['mapping_rule']['target_plus1_lv1']
  found.append(dict(name=card['name_zh'],spid=row['spid'],rating_plus1_lv1=row['ovr']+5,price=row['price']))
 colors=get('https://127.0.0.1/static/info/teamcolor')['teamColors']
 grade={c['grade']:c['boostgroups'][0] for c in colors if c['type']=='grade'}
 assert set(grade)=={5,9,12,16,20}
 for g,n in {5:3,9:5,12:7,16:9,20:12}.items():assert grade[g]==dict(count_min=6,count_max=11,boosts=[dict(type='ovr',amount=n)])
 feature=next(c for c in colors if c['teamcolorid']==60084)
 assert '中国明日之星' in feature['description']
 assert [(r['count_min'],r['count_max'],r['boosts'][0]['amount']) for r in feature['boostgroups']]==[(3,5,4),(6,8,6),(9,10,8),(11,11,10)]
 assert any(c['teamcolorid']==50327 for c in colors)
 hot=install.base.hot_status();expected=json.loads((R/'installed-handback.json').read_text('utf8'))['hot_update_status']
 assert hot==expected and hot['watcher_running'] and hot['error'] is None
 with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as con:
  assert con.execute('select count(*) from players where spid/1000000=327').fetchone()[0]==32
  assert con.execute('select count(*) from players where spid/1000000 in(300,325)').fetchone()[0]==688
 result=dict(status='LIVE_READ_ONLY_PASS',cards=found,preflight=proof,hot_update_status=hot,legend_feature=feature,
  preserved_grade_sets=grade,native_home_verified=False,native_match_verified=False,state_shop_written=False,
  top_preflight=str(S/install.SELF),composition_api='compose_manifest(server=None,client=None)',
  files={str(S/p):install.sha(S/p) for p in (install.SELF,install.MANIFEST,install.RECEIPT,'play-local.bat')})
 (R/'live-verification.json').write_bytes(install.encoded(result));print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
