"""Shared paths and deterministic IO. This module never imports the live server."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
SOURCE=R.parent/'club-balance-live'
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
SID=856;MULTIPLIER=.72
BLOCKED_PIDS=frozenset({231747})  # Preserve the later remove-mbappe formal transaction.
CLUB_ALIASES={131681:47,131682:44,115841:46,115845:39}  # Previously verified household aliases.
LANGS=('eng','chi','ind','kor','tha','vie')
sys.path[:0]=[str(S/'tools/re'),str(S/'tools/player_import'),str(W/'work/season_expansion'),str(W/'work/experience_levels'),str(S)]

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text('utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

def source_paths():
    paths=[R/'identity-reuse.json',Path(read(R/'identity-reuse.json')['source_links']),S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'gamedata/player-imports.json',
        S/'responses/static_roster.json',S/'server_display_zh.json',C/'data/data_0.big',C/'data/ui/libs/Module.big',C/'data/ui/components/Label.big',
        S/'patches/language_chi.big',S/'patches/验证结果.json',S/'http_config.py']
    paths += [S/'fair_value_model.py',S/'fair_value_store.py',S/'gamedata/removed-player-profiles.json']
    paths += [C/f'data/ui/localization/{lang}.big' for lang in LANGS]
    paths += [C/f'_cache/{prefix}/externalAssets/language_{lang}.big' for prefix in ('games/fo3id','cdn') for lang in LANGS]
    return [p for p in paths if p.exists()]

def imported_cards():
    cards=[dict(p) for p in read(R/'source-ready.json')['cards'] if p['playerid'] not in BLOCKED_PIDS]
    policy=read(R/'identity-reuse.json');mapping={r['source_playerid']:r for r in policy['rows']}
    if sha(policy['source_links'])!=policy['source_links_sha256']:raise ValueError('Verified identity bridge changed')
    for p in cards:
        p['official_source_spid']=p['source_spid'];p['official_source_playerid']=p['playerid']
        if p['playerid'] in mapping:
            row=mapping[p['playerid']];p.update(playerid=row['canonical_playerid'],source_spid=row['local_spid'],native_existing=True,appearance_route='existing_verified_native_identity')
    assert len({p['source_spid'] for p in cards})==len(cards)
    return cards
