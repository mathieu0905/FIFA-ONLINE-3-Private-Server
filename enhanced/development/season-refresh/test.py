"""Actual handler/legacy-inventory tests using temporary data only, no game/server."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,shutil,sys,tempfile,types
from unittest.mock import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;B=R/'build-v7';S=Path('D:/FO3ID/server')
T=Path(tempfile.mkdtemp(prefix='data-test-',dir=R));(T/'gamedata').mkdir()
for p in S.glob('*.json'):shutil.copyfile(p,T/p.name)
for p in (S/'gamedata').glob('*.json'):shutil.copyfile(p,T/'gamedata'/p.name)
shutil.copyfile(B/'custom_rosters.json',T/'gamedata/custom_rosters.json')
shutil.copyfile(B/'season_refresh_products.json',T/'gamedata/season_refresh_products.json')
shutil.copyfile(B/'all_item_icon_manifest.json',T/'gamedata/all_item_icon_manifest.json')
os.link(B/'fifadb.sqlite',T/'gamedata/fifadb.sqlite')
shutil.copytree(S/'responses',T/'responses');shutil.copyfile(B/'static_roster.json',T/'responses/static_roster.json')
def audit(event,args):
    if event=='open':
        path,mode,flags=args
        if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Test attempted non-temporary write')
sys.addaudithook(audit)
os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path[:0]=[str(S),str(B)];sys.argv=['http_config.py']
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
load(B/'product_packs.py','product_packs')
load(B/'season_retirement.py','season_retirement')
load(B/'npc_exchange.py','npc_exchange')
source=(B/'http_config.py').read_text('utf-8');source=source.replace('import gen_teams','import gen_teams\ngen_teams.DB='+repr(str(B/'fifadb.sqlite')),1)
h=types.ModuleType('http_config');h.__file__=str(T/'http_config.py');sys.modules['http_config']=h;exec(compile(source,h.__file__,'exec'),h.__dict__)
checks=[]
def check(label,ok):assert ok,label;checks.append(label);print(label,flush=True)
decode=lambda x:json.loads(x[1])
modern={c['fo3_spid'] for c in json.loads((B/'custom_rosters.json').read_text('utf-8'))['cards'] if c['fo3_spid']//1000000==13}
vals={s:v+5 for s,v in h.card_ovrs(modern).items()}
check('257 modern cards have native +1 rating84..92',len(vals)==257 and min(vals.values())==84 and max(vals.values())==92)
check('No retired season12 SPID is market eligible',not any(s//1000000==12 for s in h.market_spids()))
check('Market query cannot buy season12 or mint NPC book rows',not h.market_engine.valid_card(12037576) and not h.market_engine.book(h._state(),12037576,0)['rows'])
check('Season12 absent from native roster dropdown',all(12 not in x.get('value',[]) for x in decode(h.from_file('/static/roster'))['seasons']))
check('Custom registry contains no active season12',not any(x['id']==12 for x in json.loads((B/'custom_rosters.json').read_text('utf-8'))['seasons']))
check('Legacy adventure exact frozen pool and odds still available',any(s//1000000==12 for s,w in h.pack_pool(97300012)))
for itemid in [97310011,97310012,97950008,97950009,97950010,97950011,97950111]:
    if itemid in h.PACKS:assert not any(s//1000000==12 for s,w in h.pack_pool(itemid))
check('New sale packs exclude the retired season',True)
import admin
admin.hc=h
check('Admin picker no longer offers retired season12',all(x['code']!=12 for x in admin.API['shop']({})['seasons']))
check('Admin text search filters retired cards',all(x['spid']//1000000!=12 for x in admin.API['search']({'q':'Ronaldo'})['rows']))
try:admin.API['player_add']({'spid':12037576})
except admin.AdminError:pass
else:raise AssertionError('Retired admin grant allowed')
check('Direct new admin season12 grant rejected',True)
visible=h.shop_list(h._state());assert any(r['shopid']==71360501 for r in visible) and not any(r['shopid']==71250501 for r in visible)
check('Replacement native-legend chain visible; duplicate-legend chain retired',True)
assert {s//1000000 for s,w in h.pack_pool(98500020)} <= {27,30,93}
check('Replacement +13 choice contains only original native legends',h.pack_grades(98500020)[-1]==(13,100))
h.market_engine.tick()
check('NPC market background tick tolerates legacy retired-season history',True)
st=h._state();coach=h.my_coach(st);legacy=next((x for x in coach.get('items',[]) if x['itemid']==97300012 and x['remains']>0),None)
assert legacy is not None
before_count=legacy['remains'];before_players=len(st['teams'][str(h._default_slot(st))]['players'])
token=next(x['_id'] for x in h.coach_items(st,h._default_slot(st)) if x['itemid']==97300012)
data=h.product_packs['risk_packs']['97300012'];tier=next(t for t in data['tiers'] if any(s//1000000==12 for s in t['pool']));spid=next(s for s in tier['pool'] if s//1000000==12)
def draw(pop,weights):return [tier] if isinstance(pop[0],dict) else [next(g for g,w in zip(pop,weights) if w)]
with patch.object(h.random,'choices',side_effect=draw),patch.object(h.random,'choice',return_value=spid):
    opened=decode(h.ep_item_use(token,'',b'{}'))
assert opened['result'] and opened['player']['spid']==spid
after=h._state();assert len(after['teams'][str(h._default_slot(after))]['players'])==before_players+1
check('Existing legacy pack can still redeem its original season12 outcome in temporary state',True)
again=decode(h.ep_item_use(token,'',b'{}'));assert again['result'] and len(h._state()['teams'][str(h._default_slot(after))]['players'])==before_players+1
check('Legacy opening replay cannot duplicate a card',True)
st=h._state();h.my_coach(st)['cash']=10**9;h._save(st)
for i in (71360501,71360502):
    out=decode(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,shopid=71360501,bunch=0)).encode()))
    assert out['result']
check('Replacement native chain first two stages can actually be purchased in temporary state',True)
fn=next(fn for p,fn in h.ROUTES if p.pattern==r'/packchoice/(\d+)/search')
rows=decode(fn('98500020','',b''));assert len(rows)==10 and {r['grade'] for r in rows}=={13} and all(r['spid']//1000000!=12 for r in rows)
check('Replacement native choice exposes ten +13 candidates',True)
report=dict(status='PASS',checks=checks,temporary_data=str(T),production_written=False,private_service_started=False,native_verified=False)
(R/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(dict(status='PASS',checks=len(checks))))
