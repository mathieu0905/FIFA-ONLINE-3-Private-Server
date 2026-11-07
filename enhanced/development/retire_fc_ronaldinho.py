"""Retire the active FC entry while preserving already-issued pack contracts."""
from pathlib import Path
import datetime, hashlib, importlib.util, json, shutil, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
OUT = ROOT / 'releases/fc13-retire-ronaldinho-v2'
SPID = 13028130
def read(p): return json.loads(p.read_text('utf-8-sig'))
def write(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2), 'utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    OUT.mkdir(parents=True, exist_ok=False)
    registry = read(SERVER/'gamedata/custom_rosters.json')
    retired = next(r for r in registry['cards'] if r['fo3_spid'] == SPID)
    registry['cards'] = [r for r in registry['cards'] if r['fo3_spid'] != SPID]
    for season in registry['seasons']:
        season['cards'] = [s for s in season['cards'] if s != SPID]
        if season['id'] == 13: season['label'] = '现役精选'
    registry.setdefault('retired_cards', []).append(dict(retired,
        retirement_reason='退役球员移出现役赛季；保留已发行旧包兼容', npc_excluded=True))
    assert len(registry['cards']) == 503
    assert len(next(s for s in registry['seasons'] if s['id'] == 13)['cards']) == 257
    assert {12028130, 84028130} <= {r['fo3_spid'] for r in registry['cards']}
    write(OUT/'custom_rosters.json', registry)
    code = (SERVER/'legend_moments_bulk_npc.py').read_text('utf-8')
    before = "    if not excluded or any(not engine.valid_card(spid, 1) for spid in excluded):"
    after = "    excluded |= frozenset(int(r['fo3_spid']) for r in registry.get('retired_cards', []) if r.get('npc_excluded'))\n" + before
    assert code.count(before) == 1
    (OUT/'legend_moments_bulk_npc.py').write_text(code.replace(before, after), 'utf-8')
    launcher = (SERVER/'play-local.bat').read_bytes()
    assert launcher.count(b'patches\\player_value_preflight.py') == 1
    (OUT/'play-local.bat').write_bytes(launcher.replace(b'patches\\player_value_preflight.py', b'patches\\fc_retirement_preflight.py'))
    helper = '''"""Read-only FC retirement layer over the exact current installed parent."""
from pathlib import Path
import hashlib, importlib.util, json
MANIFEST='patches/fc-retirement-release-manifest.json'
RECEIPT='patches/fc-retirement-release-installed.json'
SELF='patches/fc_retirement_preflight.py'
ALLOWED={('server',n) for n in ('gamedata/custom_rosters.json','legend_moments_bulk_npc.py','play-local.bat',SELF,'patches/language_chi.big','patches/验证结果.json')}|{('client','_cache/'+n+'/externalassets/language_chi.big') for n in ('games/fo3id','cdn')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent)
    m=read(server/MANIFEST);client=Path(client or m['client_root'])
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('FC retirement parent changed: '+n)
    spec=importlib.util.spec_from_file_location('fc_retirement_parent',server/'patches/player_value_preflight.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    c,v=p._compose(server,client);guards=v.table(c['guards'])
    if set(v.table(m['files']))!=ALLOWED:raise RuntimeError('Wrong retirement scope')
    v.replace(guards,m['files'],{('server',SELF):None},ALLOWED)
    r=read(server/RECEIPT)
    if r['status']!='INSTALLED_FC13_RETIREMENT' or r['manifest_sha256']!=sha(server/MANIFEST):raise RuntimeError('Retirement receipt mismatch')
    for n in (MANIFEST,RECEIPT):guards[('server',n.casefold())]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(guards.values())
    result=v.verify_manifest(c,server,client)
    registry=read(server/'gamedata/custom_rosters.json')
    assert 13028130 not in {r['fo3_spid'] for r in registry['cards']}
    assert len(next(s for s in registry['seasons'] if s['id']==13)['cards'])==257
    result['status']='READ_ONLY_FC13_RETIREMENT_PASS'
    return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
'''
    (OUT/'fc_retirement_preflight.py').write_text(helper, 'utf-8')
    sys.path.insert(0, 'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/season_expansion')
    import roster_import as codec
    big, _, replace, *_ = codec.load_codecs(SERVER)
    source = SERVER/'patches/language_chi.big'
    lang = json.loads(big.read(source, codec.LANG_MEMBER))
    old = dict(lang)
    assert old['FC_CUSTOM_SEASON_13'] == 'FC精选移植'
    lang['FC_CUSTOM_SEASON_13'] = '现役精选'
    target = OUT/'language_chi.big'; shutil.copyfile(source, target)
    replace(target, codec.LANG_MEMBER, json.dumps(lang, ensure_ascii=False, separators=(',', ':')).encode(), 0)
    assert json.loads(big.read(target, codec.LANG_MEMBER)) == lang
    assert all(v == lang[k] for k,v in old.items() if k != 'FC_CUSTOM_SEASON_13')
    check = read(SERVER/'patches/验证结果.json'); check['sha256'] = sha(target)
    write(OUT/'验证结果.json', check)
    mapping = {'gamedata/custom_rosters.json':'custom_rosters.json',
        'legend_moments_bulk_npc.py':'legend_moments_bulk_npc.py',
        'play-local.bat':'play-local.bat','patches/fc_retirement_preflight.py':'fc_retirement_preflight.py',
        'patches/language_chi.big':'language_chi.big','patches/验证结果.json':'验证结果.json'}
    files = [dict(root='server',relative=n,source=str(OUT/payload),sha256=sha(OUT/payload),
        parent_sha256=sha(SERVER/n) if (SERVER/n).exists() else None) for n,payload in mapping.items()]
    for name in ('games/fo3id','cdn'):
        relative='_cache/'+name+'/externalAssets/language_chi.big'
        assert sha(CLIENT/relative) == sha(source)
        files.append(dict(root='client',relative=relative,source=str(target),sha256=sha(target),parent_sha256=sha(CLIENT/relative)))
    m=dict(schema=1,release_id='fc13-retire-ronaldinho-v1',client_root=str(CLIENT),state_shop_replaced=False,
        retired_spid=SPID,active_season13_cards=257,registered_active_cards=503,legacy_pack_pools_unchanged=True,
        parent_files={n:sha(SERVER/n) for n in ['patches/player_value_preflight.py',
            'patches/player-value-release-manifest.json','patches/player-value-release-installed.json']},files=files)
    write(OUT/'fc-retirement-release-manifest.json',m)
    print(json.dumps({'candidate':str(OUT),'files':len(files),'active_fc':257}))
if __name__=='__main__':build()
