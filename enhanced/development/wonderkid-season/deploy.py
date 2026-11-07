"""Additive production installation using the shared backed-up transaction core."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,sqlite3,subprocess,sys,time,types
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;B=R/'install-build-v3';S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
code=Path('D:/fifaol3/shop-value-v1/deploy.py').read_text('utf-8').replace('SHOP_VALUE','WONDERKID').replace('shop-value','wonderkid').replace('shop_value','wonderkid')
d=types.ModuleType('wonderkid_transaction');d.__file__=str(R/'deploy.py');exec(compile(code,'<shared guarded transaction>','exec'),d.__dict__)
d.R=R;d.OUT=R/'transaction-v1';d.MANIFEST='patches/wonderkid-installed.json';d.RECEIPT='patches/wonderkid-receipt.json';d.SELF='patches/wonderkid_preflight.py'
FILES=[('server','gamedata/fifadb.sqlite',B/'fifadb.sqlite'),('client','data/data_0.big',B/'data_0.big'),('server','gamedata/custom_rosters.json',B/'custom_rosters.json'),('server','responses/static_roster.json',B/'static_roster.json'),('server','server_display_zh.json',B/'server_display_zh.json'),('server','http_config.py',B/'http_config.py'),('server','wonderkid_runtime.py',B/'wonderkid_runtime.py'),('server','gamedata/wonderkid_legacy_pools.json',R/'frozen-pools.json'),('server','gamedata/wonderkid_price_seeds.json',R/'price-seeds.json'),('server','gamedata/npc-market-prices.sqlite',R/'fresh-market.sqlite'),('client','data/ui/libs/Module.big',B/'Module.big'),('client','data/ui/components/Label.big',B/'Label.big'),('server','patches/Label.big',B/'Label.big'),('server','patches/language_chi.big',B/'language_chi.big'),('server','patches/验证结果.json',B/'language-check.json')]
for lang in ('chi','eng','ind','kor','tha','vie'):FILES.append(('client',f'data/ui/localization/{lang}.big',B/f'{lang}.big'))
for prefix in ('games/fo3id','cdn'):
    for p in (B/'languages'/prefix).glob('*.big'):FILES.append(('client',f'_cache/{prefix}/externalAssets/{p.name}',B/'language_chi.big' if p.name=='language_chi.big' else p))
    for p in (B/'crests').rglob('*.png'):FILES.append(('client',f'_cache/{prefix}/externalAssets/crests/{p.parent.name}/{p.name}',p))
    for p in (B/'portraits').glob('*.png'):FILES.append(('client',f'_cache/{prefix}/externalAssets/players/{p.name}',p))
FILES.append(('server','docs/wonderkid-season-install.json',R/'engineering.json'))
FILES.append(('server','docs/wonderkid-portrait-sources.json',R/'portraits-supplement.json'))
FILES.append(('server','gamedata/player-import-validation.json',R/'player-import-ready.json'))
d.TARGETS={(root,rel) for root,rel,_ in FILES}|{('server','play-local.bat'),('server',d.SELF)}
MUTABLE=('server','gamedata/npc-market-prices.sqlite')
def prepare():
    proof=d.read(B/'build.json')
    assert d.read(R/'price-seeds.json')['source_database_sha256']==d.tx.sha(B/'fifadb.sqlite')
    assert d.read(R/'portraits-supplement.json')['status']=='PASS'
    for row in d.read(R/'portraits-supplement.json')['rows']:assert d.tx.sha(B/'portraits'/f'p{row["spid"]}.png')==row['sha256']
    for p,h in proof['source_hashes'].items():assert d.tx.sha(p)==h,('Source drift',p)
    assert d.read(R/'frozen-pools.json')['source_sha256']==d.tx.sha(S/'http_config.py')
    for p,h in proof['output_hashes'].items():assert d.tx.sha(B/p)==h,('Build drift',p)
    certificate=d.read(R/'player-import-staged.json');assert certificate['status']=='PLAYER_IMPORT_FULL_PASS'
    inputs={'database':B/'fifadb.sqlite','registry':B/'custom_rosters.json','imports':S/'gamedata/player-imports.json','rig-map':S/'tools/player_import/rig-map.json',**{'archive'+str(i):B/'data_0.big' if i==0 else C/f'data/data_{i}.big' for i in (0,3,4,6)},**{'checker:'+p.name:p for p in (S/'tools/player_import').glob('*.py')}}
    assert {k:d.tx.sha(p) for k,p in inputs.items()}==certificate['input_hashes'],'Semantic validation inputs changed'
    portraits={}
    for name,h in certificate['portrait_hashes'].items():
        assert d.tx.sha(name)==h
        p=Path(name)
        if p.is_relative_to(B/'portraits'):
            for prefix in ('games/fo3id','cdn'):portraits[str(C/f'_cache/{prefix}/externalAssets/players/{p.name}')]=h
        else:portraits[name]=h
    certificate['portrait_hashes']=portraits;d.write(R/'player-import-ready.json',certificate)
    out=d.OUT;assert not out.exists();out.mkdir()
    template=(S/'patches/native_roster_preflight.py').read_text('utf-8').replace('native-roster','wonderkid').replace('native_roster','wonderkid').replace('NATIVE_ROSTER','WONDERKID')
    required={(root,rel.casefold()) for root,rel in d.TARGETS if (root,rel)!=MUTABLE}
    template=re.sub(r'^    required=.*$',lambda _:'    required='+repr(required),template,flags=re.M)
    extra='''    import importlib.util
    spec=importlib.util.spec_from_file_location('_wonderkid_prices',server/'market_price_store.py');store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
    store.verify_seed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/npc-market-seed.json.gz')
    import sqlite3
    seed=json.loads((server/'gamedata/wonderkid_price_seeds.json').read_text('utf-8'))
    with sqlite3.connect((server/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        for spid,price in seed['rows']:
            assert db.execute('select initial_price,model_sha256 from seeds where spid=?',(spid,)).fetchone()==(price,seed['model_sha256'])
            assert db.execute('select basis_price from prices where spid=?',(spid,)).fetchone()[0]>0
'''
    template=template.replace("    return dict(status='WONDERKID_PREFLIGHT_PASS'",extra+"    return dict(status='WONDERKID_PREFLIGHT_PASS'")
    (out/'wonderkid_preflight.py').write_text(template,'utf-8');compile(template,'wonderkid_preflight.py','exec')
    play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play);assert len(matches)==1;name=matches[0].decode();parentrel='patches/'+name
    parent=d.load(S/parentrel,'wonderkid_parent');check=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
    (out/'play-local.bat').write_bytes(play.replace(('patches\\'+name).encode(),b'patches\\wonderkid_preflight.py'))
    payloads=FILES+[('server','play-local.bat',out/'play-local.bat'),('server',d.SELF,out/'wonderkid_preflight.py')]
    rows=[dict(root=root,relative=rel,source=str(source),parent_sha256=d.tx.digest((S if root=='server' else C)/rel),sha256=d.tx.sha(source)) for root,rel,source in payloads]
    guards={(r['root'],r['relative'].replace('\\','/').casefold()):r for r in comp['guards']};oldkeys=set(guards)
    assert MUTABLE not in guards,'Mutable market prices must not be frozen'
    for row in rows:
        if (row['root'],row['relative'])!=MUTABLE:guards[(row['root'],row['relative'].casefold())]={k:row[k] for k in ('root','relative','sha256')}
    assert oldkeys<=set(guards)
    comp.update(guards=list(guards.values()),files_verified=False)
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in d.read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    parent_files={p:d.tx.sha(S/p) for p in (parentrel,parent.MANIFEST,parent.RECEIPT)}
    comp.setdefault('ancestry',[]).append(dict(layer='wonderkid40',parent=parent_files,native_status='PENDING'))
    m=dict(schema=1,revision='wonderkid-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'),client=str(C),state_shop_replaced=False,guards=list(guards.values()),composition=comp,files=rows,parent_files=parent_files,parent_preflight=parentrel,mutable_files=[MUTABLE[1]])
    d.write(out/'manifest.json',m);print(json.dumps(dict(status='PREPARED',files=len(rows),parent=check['status'])),flush=True)
def preview(roots):
    m=d.read(d.OUT/'manifest.json');assert len(m['files'])==len(d.TARGETS) and {(r['root'],r['relative']) for r in m['files']}==d.TARGETS
    for rel,h in m['parent_files'].items():assert d.tx.sha(roots['server']/rel)==h,('Parent changed',rel)
    check=d.load(roots['server']/m['parent_preflight'],'wonderkid_live_parent').preflight(**roots)
    for row in m['files']:
        assert d.tx.sha(row['source'])==row['sha256'];assert d.tx.digest(d.tx.target(roots,row))==row['parent_sha256'],('Target changed',row['relative'])
    return m,check
d.preview=preview
def gameclosed():
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0'],creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('Game is running; no forced exit')
def snapshot_prices():
    target=R/'fresh-market.sqlite'
    if target.exists():target.rename(R/('fresh-market-attempt-'+datetime.datetime.now().strftime('%H%M%S-%f')+'.sqlite'))
    with sqlite3.connect((S/MUTABLE[1]).as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(target) as dest:src.backup(dest)
    seed=d.read(R/'price-seeds.json')
    with sqlite3.connect(target.as_uri(),uri=True) as db:
        stamp=time.time()
        for spid,price in seed['rows']:
            db.execute('insert into seeds values(?,?,?,?)',(spid,price,seed['model_sha256'],stamp));db.execute('insert into prices values(?,?,?,?,null)',(spid,float(price),price,stamp))
        db.commit();db.execute('attach database ? as old',((S/MUTABLE[1]).as_uri()+'?mode=ro',))
        for table in ('seeds','prices','price_events','metadata'):assert not db.execute(f'select * from old.{table} except select * from main.{table}').fetchone(),table
        assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
def main():
    assert d.read(R/'test-results.json')['status']=='PASS';assert d.read(R/'io-tests.json')['status']=='PASS'
    coord=d.read(Path('D:/fifaol3/coordination-current.json'));assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
    with d.locks(S):
        gameclosed()
        play=(S/'play-local.bat').read_bytes();n=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode();d.load(S/'patches'/n,'before_stop').preflight(S,C)
        error=None
        try:
            stop=r"$managed=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:\\FO3ID\\server\\(?:start_all|http_config|messenger)\.py' }; foreach($p in $managed){Stop-Process -Id $p.ProcessId -ErrorAction SilentlyContinue};exit 0"
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',stop],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            gameclosed();d.tx.stopped();snapshot_prices();prepare();preview(dict(server=S,client=C));result=d.install(review_sha=d.tx.sha(d.OUT/'manifest.json'))
        except BaseException as e:
            error=e
            play=(S/'play-local.bat').read_bytes();n=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode();d.load(S/'patches'/n,'recover_parent').preflight(S,C)
        env={**os.environ,'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'}
        with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
            p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,env=env,capture_output=True,text=True)
        if ready.returncode:raise RuntimeError(ready.stdout+ready.stderr)
        if error:raise error
        result.update(service_restart=True,launcher_pid=p.pid,readiness=ready.stdout.strip());d.write(R/'cutover-result.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
