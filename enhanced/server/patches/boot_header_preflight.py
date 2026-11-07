"""Exact-file guard for the additive official club-career update."""
from pathlib import Path
import hashlib,json
MANIFEST='patches/boot-header-installed.json'
RECEIPT='patches/boot-header-receipt.json'
SELF='patches/boot_header_preflight.py'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf8'))
    r=json.loads((server/RECEIPT).read_text('utf8'))
    if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Invalid wonderkid scope')
    if r.get('status')!='INSTALLED_BOOT_HEADER' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m['revision']:raise RuntimeError('Native-Roster receipt mismatch')
    roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
    for g in m['guards']:
        if g.get('root') not in roots:raise RuntimeError('Unknown guard root')
        root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
        if not p.is_relative_to(root) or p==root or key in seen:raise RuntimeError('Invalid wonderkid guard')
        seen.add(key)
        if not p.is_file() or sha(p)!=g['sha256']:raise RuntimeError('Installed file differs: '+str(key))
    required={('client', '_cache/games/fo3id/externalassets/players/p18170369.png'), ('client', '_cache/games/fo3id/externalassets/players/p18212125.png'), ('client', '_cache/games/fo3id/externalassets/players/p18189681.png'), ('client', '_cache/cdn/externalassets/players/p18202515.png'), ('server', 'http_config.py'), ('client', '_cache/cdn/externalassets/players/p18194644.png'), ('client', '_cache/games/fo3id/externalassets/crests/small/s999918.png'), ('client', '_cache/games/fo3id/externalassets/players/p18136144.png'), ('client', '_cache/cdn/externalassets/players/p18162409.png'), ('client', 'data/data_0.big'), ('client', '_cache/cdn/externalassets/players/p18186197.png'), ('client', '_cache/games/fo3id/externalassets/players/p18179546.png'), ('client', '_cache/games/fo3id/externalassets/players/p18202515.png'), ('client', '_cache/games/fo3id/externalassets/players/p18208330.png'), ('server', 'docs/wonderkid-season-install.json'), ('client', '_cache/cdn/externalassets/players/p18202166.png'), ('client', '_cache/cdn/externalassets/players/p18181560.png'), ('client', '_cache/cdn/externalassets/players/p18189461.png'), ('client', '_cache/games/fo3id/externalassets/players/p18176993.png'), ('client', '_cache/cdn/externalassets/players/p18167963.png'), ('client', 'data/ui/libs/module.big'), ('client', '_cache/cdn/externalassets/players/p18186115.png'), ('client', '_cache/cdn/externalassets/players/p18179546.png'), ('client', '_cache/games/fo3id/externalassets/players/p18182168.png'), ('client', '_cache/games/fo3id/externalassets/players/p18162409.png'), ('client', '_cache/games/fo3id/externalassets/players/p18202166.png'), ('client', '_cache/games/fo3id/externalassets/players/p18007631.png'), ('client', '_cache/cdn/externalassets/players/p18189484.png'), ('client', '_cache/games/fo3id/externalassets/players/p18203042.png'), ('client', '_cache/cdn/externalassets/players/p18203038.png'), ('client', '_cache/cdn/externalassets/players/p18211300.png'), ('server', 'gamedata/player-import-validation.json'), ('client', 'data/ui/components/label.big'), ('server', 'patches/boot_header_preflight.py'), ('client', '_cache/games/fo3id/externalassets/players/p18189461.png'), ('client', '_cache/games/fo3id/externalassets/players/p18153296.png'), ('client', '_cache/games/fo3id/externalassets/players/p18167963.png'), ('client', '_cache/cdn/externalassets/players/p18180175.png'), ('client', '_cache/cdn/externalassets/players/p18212125.png'), ('client', '_cache/games/fo3id/externalassets/language_chi.big'), ('client', '_cache/cdn/externalassets/crests/large/l999918.png'), ('client', 'data/ui/localization/ind.big'), ('server', 'gamedata/custom_rosters.json'), ('client', '_cache/cdn/externalassets/players/p18136144.png'), ('client', 'data/ui/localization/vie.big'), ('client', '_cache/games/fo3id/externalassets/players/p18180175.png'), ('client', '_cache/games/fo3id/externalassets/players/p18186197.png'), ('client', '_cache/cdn/externalassets/players/p18170369.png'), ('client', '_cache/cdn/externalassets/players/p18163423.png'), ('client', '_cache/games/fo3id/externalassets/players/p18186627.png'), ('client', '_cache/cdn/externalassets/players/p18165239.png'), ('client', '_cache/games/fo3id/externalassets/players/p18160766.png'), ('client', '_cache/games/fo3id/externalassets/players/p18192620.png'), ('client', '_cache/cdn/externalassets/players/p18192620.png'), ('client', '_cache/cdn/externalassets/players/p18161648.png'), ('client', '_cache/cdn/externalassets/players/p18169721.png'), ('client', 'data/ui/localization/tha.big'), ('client', '_cache/cdn/externalassets/players/p18189680.png'), ('client', '_cache/cdn/externalassets/players/p18160766.png'), ('client', '_cache/cdn/externalassets/players/p18208330.png'), ('client', '_cache/games/fo3id/externalassets/players/p18183465.png'), ('server', 'patches/验证结果.json'), ('client', '_cache/cdn/externalassets/players/p18230767.png'), ('client', '_cache/games/fo3id/externalassets/crests/large/l999918.png'), ('client', '_cache/cdn/externalassets/crests/small/s999918.png'), ('client', '_cache/games/fo3id/externalassets/players/p18165239.png'), ('client', '_cache/cdn/externalassets/players/p18121933.png'), ('server', 'docs/wonderkid-portrait-sources.json'), ('client', '_cache/cdn/externalassets/players/p18007631.png'), ('client', '_cache/games/fo3id/externalassets/players/p18181560.png'), ('client', '_cache/cdn/externalassets/language_chi.big'), ('server', 'gamedata/fifadb.sqlite'), ('client', '_cache/games/fo3id/externalassets/players/p18189680.png'), ('client', '_cache/games/fo3id/externalassets/language_ind.big'), ('client', '_cache/games/fo3id/externalassets/players/p18194644.png'), ('client', '_cache/cdn/externalassets/players/p18183465.png'), ('client', '_cache/games/fo3id/externalassets/players/p18203038.png'), ('client', '_cache/cdn/externalassets/players/p18176993.png'), ('server', 'patches/label.big'), ('client', '_cache/games/fo3id/externalassets/players/p18121933.png'), ('server', 'gamedata/wonderkid_legacy_pools.json'), ('client', '_cache/games/fo3id/externalassets/players/p18211300.png'), ('client', '_cache/cdn/externalassets/players/p18181820.png'), ('client', '_cache/games/fo3id/externalassets/players/p18188154.png'), ('client', '_cache/games/fo3id/externalassets/players/p18163423.png'), ('client', '_cache/cdn/externalassets/players/p18182168.png'), ('client', '_cache/cdn/externalassets/players/p18189681.png'), ('client', '_cache/games/fo3id/externalassets/players/p18161648.png'), ('client', 'data/ui/localization/kor.big'), ('client', '_cache/games/fo3id/externalassets/players/p18181820.png'), ('client', '_cache/games/fo3id/externalassets/players/p18202477.png'), ('server', 'responses/static_roster.json'), ('client', '_cache/cdn/externalassets/language_ind.big'), ('client', '_cache/cdn/externalassets/players/p18153296.png'), ('client', '_cache/games/fo3id/externalassets/players/p18230767.png'), ('client', '_cache/cdn/externalassets/players/p18194957.png'), ('server', 'server_display_zh.json'), ('client', 'data/ui/localization/eng.big'), ('client', '_cache/cdn/externalassets/players/p18203042.png'), ('client', '_cache/cdn/externalassets/players/p18169416.png'), ('client', '_cache/games/fo3id/externalassets/players/p18169416.png'), ('server', 'wonderkid_runtime.py'), ('server', 'play-local.bat'), ('server', 'patches/language_chi.big'), ('client', 'data/ui/localization/chi.big'), ('client', '_cache/games/fo3id/externalassets/players/p18186115.png'), ('client', '_cache/cdn/externalassets/players/p18202477.png'), ('client', '_cache/cdn/externalassets/players/p18188154.png'), ('client', '_cache/games/fo3id/externalassets/players/p18169721.png'), ('client', '_cache/cdn/externalassets/players/p18186627.png'), ('client', '_cache/games/fo3id/externalassets/players/p18194957.png'), ('client', '_cache/games/fo3id/externalassets/players/p18189484.png'), ('server', 'gamedata/wonderkid_price_seeds.json')}
    if not required<=seen:raise RuntimeError('Incomplete wonderkid guards')
    for policy in m.get('composition',{}).get('receipt_policies',[]):
        if policy.get('root') not in roots:raise RuntimeError('Unknown receipt root')
        root=roots[policy['root']];p=(root/policy['relative']).resolve()
        if not p.is_relative_to(root) or p==root:raise RuntimeError('Receipt path escape')
        receipt=json.loads(p.read_text('utf-8-sig'))
        if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')
    import importlib.util
    spec=importlib.util.spec_from_file_location('_wonderkid_prices',server/'market_price_store.py');store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
    store.verify_seed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/npc-market-seed.json.gz')
    import sqlite3
    seed=json.loads((server/'gamedata/wonderkid_price_seeds.json').read_text('utf-8'))
    with sqlite3.connect((server/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        for spid,price in seed['rows']:
            assert db.execute('select initial_price,model_sha256 from seeds where spid=?',(spid,)).fetchone()==(price,seed['model_sha256'])
            assert db.execute('select basis_price from prices where spid=?',(spid,)).fetchone()[0]>0
    import sqlite3
    seed=json.loads((server/'gamedata/manutd-service-price-seeds.json').read_text('utf8'))
    with sqlite3.connect((server/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        for spid,price in seed['rows']:
            assert db.execute('select initial_price,model_sha256 from seeds where spid=?',(spid,)).fetchone()==(price,seed['model_sha256'])
            assert db.execute('select basis_price from prices where spid=?',(spid,)).fetchone()[0]>0
    return dict(status='BOOT_HEADER_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],native_status='PENDING',state_shop_touched=False)

def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf8'));c=dict(m.get('composition') or {})
    guards=list(m['guards'])
    for rel in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=rel,sha256=sha(server/rel)))
    c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards)
    c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[])
    return c

if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
