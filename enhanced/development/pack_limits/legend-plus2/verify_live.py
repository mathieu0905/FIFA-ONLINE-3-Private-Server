from pathlib import Path
import hashlib,json,ssl,urllib.request
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
with op.open('https://127.0.0.1/static/info/teamcolor',timeout=15) as response:data=json.load(response)
rule=next(c for c in data['teamColors'] if c['teamcolorid']==20043)
assert [(g['count_min'],g['count_max']) for g in rule['boostgroups']]==[(5,6),(7,8),(9,11)]
assert all(g['boosts']==[dict(type='ovr',amount=2)] for g in rule['boostgroups'])
installation=json.loads((R/'installed-result.json').read_text(encoding='utf8'))
before=json.loads((Path(installation['backup'])/'evidence/gamedata/state.json').read_text(encoding='utf8'))
after=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
assert before['coaches']==after['coaches'] and before['teams']==after['teams']
c=next(c for c in after['coaches'] if c['_id']==after['defaultcoachid'])
owned={int(p['spid']) for p in after['teams'][str(c['slot'])]['players']}
old=set(json.loads((R/'before-teamcolor-sets.json').read_text(encoding='utf8'))['20043'])
assert set(data['teamColorSpecials']['20043'])=={s for s in owned if s in old or s//1000000==19}
names=['patches/legend_plus2_preflight.py','patches/legend-plus2-release-manifest.json','patches/legend-plus2-release-installed.json','http_config.py','play-local.bat']
report=dict(status='INSTALLED_LIVE_FLAT_PLUS2_PASS_NATIVE_RELOGIN_PENDING',top_preflight=str(S/names[0]),top_manifest=str(S/names[1]),top_receipt=str(S/names[2]),files={n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in names},tiers=[5,7,9],ovr_boosts=[2,2,2],nostalgia_cards=88,assets_equal_fresh_install_snapshot=True,state_shop_restored=False,installation=str(R/'installed-result.json'),rule_tests=str(R/'rule-results.json'),native_status='PENDING_RELOGIN')
(R/'installed-handback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status=report['status'],tiers=report['tiers'],boosts=report['ovr_boosts'])))
