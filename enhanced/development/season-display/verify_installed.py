from pathlib import Path
import hashlib, importlib.util, json, re, sqlite3, ssl, sys, urllib.request
sys.dont_write_bytecode = True
R=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')

def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

receipt=read(S/'patches/moments-display-release-installed.json');backup=Path(receipt['backup']);tx=read(backup/'transaction.json')
assert tx['status']=='installed'
play=(S/'play-local.bat').read_text('utf-8')
entry=re.findall(r'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(entry)==1
spec=importlib.util.spec_from_file_location('installed_current_top',S/'patches'/entry[0]);top=importlib.util.module_from_spec(spec);spec.loader.exec_module(top)
check=top.preflight(S,C)
assert any(e.get('layer')=='moments-display' for e in check['ancestry'])
for row in tx['entries']:
    if row['root']=='server' and row['relative']=='play-local.bat' and entry[0]!='moments_display_preflight.py':
        continue  # A verified descendant owns the newer launcher; all other payloads remain exact.
    assert sha((S if row['root']=='server' else C)/row['relative'])==row['sha256']
with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    groups=db.execute('select teamid,leagueid,count(*) from players where spid/1000000=84 group by 1,2').fetchall();assert groups==[(999984,2028,123)]
    assert db.execute('select count(*) from players').fetchone()[0]==60678
before=read(backup/'audit-state.json');after=read(S/'gamedata/state.json')
assert before['coaches']==after['coaches'] and before['teams']==after['teams']
assert sha(S/'gamedata/shop.json')==sha(backup/'audit-shop.json')
for path,digest in tx['protected'].items():
    if Path(path).name not in ('state.json',):assert sha(Path(path))==digest
import sys
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
for lang in ('chi','eng','ind','kor','tha','vie'):
    p=C/f'data/ui/localization/{lang}.big';member=next(n for n,*_ in bigdir.entries(p) if '/TEAMNAMES_' in n)
    values=json.loads(bigdir.read(p,member));assert values['999984']==('传奇时刻' if lang=='chi' else 'Legend Moments')
ctx=ssl._create_unverified_context();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ctx))
http=[]
for folder,letter in [('small','s'),('large','l')]:
    with opener.open(f'https://127.0.0.1/cdn/externalAssets/crests/{folder}/{letter}999984.png',timeout=10) as response:
        body=response.read();assert response.status==200
    assert hashlib.sha256(body).hexdigest()==sha(C/f'_cache/games/fo3id/externalAssets/crests/{folder}/{letter}999984.png')
    http.append(dict(path=folder+'/'+letter+'999984.png',status=200,hash_match=True))
with opener.open('https://127.0.0.1/info/player/level_rules',timeout=10) as response:rules=json.load(response)
assert 30 in rules.values()
owned=sum(len(t.get('players',[])) for t in after['teams'].values())
report=dict(status='INSTALLED_FORMAL_MOMENTS_DISPLAY_READONLY_PASS',release_id=receipt['release_id'],backup=str(backup),manifest_sha256=receipt['manifest_sha256'],
            preflight=check,affiliation_groups=groups,scope_cards=123,all_stats_and_history_preserved_by_candidate_proof=True,
            existing_coaches_teams_wallets_cards_and_shop_unchanged=True,owned_cards_current_snapshot=owned,
            compact_module_fontconfig_and_money_ABC_preserved=True,http_crests=http,player_level_rules=rules,native_verified=False)
(R/'installed-PASS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(status=report['status'],cards=123,groups=groups,owned_cards_current_snapshot=owned,guards=check['files'])))
