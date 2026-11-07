"""Read-only live API verification; never buys, upgrades or grants assets."""
from pathlib import Path
import datetime,hashlib,importlib.util,itertools,json,re,ssl,subprocess,sys,urllib.request
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,admin=False):
    with opener.open(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,timeout=15) as response:return json.load(response)
spec=importlib.util.spec_from_file_location('capped_live_model',S/'enhancement_progression.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
installed=read(R/'installed-handback.json')
rules=get('/info/enhancement/progression/rules');assert rules['version']=='progression20-capped-v3'
expected={str(g):round(p.RATES[g]*100,8) for g in range(1,20)}
assert rules['active_probabilities']==expected
settings=get('/api/enhancement',True);assert settings['rates']==expected and settings['semantics']=='equal_material_ceiling'
protection=get('/info/enhancement/protection/rules');assert protection['fraction_percent']==40 and protection['independent_checkbox'] and not protection['boost_item_exclusive']
st=read(S/'gamedata/state.json');coach=next((c for c in st['coaches'] if c['_id']==st['defaultcoachid']),st['coaches'][0]);team=st['teams'][str(coach['slot'])]
sample=next((v['spid'] for v in team['players'] if int(v.get('grade',1))>0),93192181)
values={}
for grade in (1,2,3,8,9,10,13,19,20):
    data=get(f'/api/market_price_store?spid={sample}&grade={grade}',True)
    want=p.expected_curve(data['current_price'],tuple(p.RATES))[0][grade]
    assert data['value']==want,(grade,data,want)
    values[str(grade)]={'base':data['current_price'],'value':data['value']}
previews=[]
pairs=sorted(itertools.permutations(team['players'],2),key=lambda pair:(abs(int(pair[0].get('grade',1))-9),abs(int(pair[1].get('grade',1))-8)))
for a,b in pairs:
    grade=int(a.get('grade',1));material=int(b.get('grade',1))
    if a['spid']!=b['spid'] or not 1<=grade<=19 or material<=0:continue
    if a.get('locked') or b.get('locked') or a.get('lock') or b.get('lock'):continue
    ai=str(a.get('_id') or a['spid']);bi=str(b.get('_id') or b['spid'])
    if len(previews)>=4:break
    for points in (0,1):
        reply=get(f'/player/{ai}/enhance2.5/{bi}/preview/{points}/-1/1001')
        chance=min(p.RATES[grade],p.RATES[grade]*p.material_factor(grade,material)*(1+.10*points))
        assert reply['result'] and reply['probability']==round(chance*100,3),(reply,chance)
        previews.append(dict(main_grade=grade,material_grade=material,points=points,probability=reply['probability']))
hot=get('/api/hot_update_status',True)
assert hot['revision']==installed['hot_revision'] and hot['watcher_running'] and hot['error'] is None
play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
actual=matches[0].decode().replace('\\','/')
spec=importlib.util.spec_from_file_location('capped_live_preflight',S/actual);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
proof=guard.preflight(S,C)
snapshot=read(R/'fresh-stop-snapshot'/installed['revision']/'state.json');now=read(S/'gamedata/state.json')
for key in ('coaches','teams','defaultcoachid'):assert snapshot[key]==now[key],('Business assets changed',key)
assert sha(S/'gamedata/shop.json')==installed['protected'][str(S/'gamedata/shop.json')]
result=dict(status='PASS_RUNTIME_ACTIVE_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),
    rules=rules,settings=settings,protection=protection,live_value_samples=values,actual_card_previews=previews,
    assets_preserved=True,shop_preserved=True,hot_status=hot,preflight=proof,
    top_preflight=str(S/actual),top_manifest=str(S/guard.MANIFEST),top_receipt=str(S/guard.RECEIPT),composition_api='compose_manifest(server=None,client=None)',
    hashes={str(path):sha(path) for path in (S/actual,S/guard.MANIFEST,S/guard.RECEIPT,S/'play-local.bat')},
    native_verified=False,match_verified=False,formal_test_transactions=False)
(R/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
installed.update(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',runtime_active=True,live_verification=str(R/'live-verification.json'),assets_preserved=True,hot_status=hot)
(R/'installed-handback.json').write_text(json.dumps(installed,ensure_ascii=False,indent=2),encoding='utf8')
# The live entry is re-read above; do not publish an earlier top over later releases.
sys.path.insert(0,str(S))
import hot_update_release as release
with release.locks(S,'enhancement-capped-verification'):
    descriptor=read(R.parent/'root-current-top.json')
    if Path(descriptor['top_preflight'])==S/actual and (S/'play-local.bat').read_bytes()==play:
        descriptor.update(status=installed['status'],runtime_active=True,verification=str(R/'live-verification.json'),hot_status=hot,assets_preserved=True,native_verified=False,match_verified=False)
        release.atomic(R.parent/'root-current-top.json',release.body(descriptor))
print(json.dumps({k:result[k] for k in ('status','actual_card_previews','live_value_samples','assets_preserved','hot_status')},ensure_ascii=True))
