"""Minimal sealed dual-end update, using the established guarded transaction core."""
from pathlib import Path
import datetime,importlib.util,json,os,re,subprocess,sys,types
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;B=R/'build-v7';S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
code=Path('D:/fifaol3/shop-value-v1/deploy.py').read_text('utf-8').replace('SHOP_VALUE','SEASON_REFRESH').replace('shop-value','season-refresh').replace('shop_value','season_refresh')
d=types.ModuleType('season_refresh_transaction');d.__file__=str(R/'deploy.py');exec(compile(code,'<reviewed transaction core>','exec'),d.__dict__)
d.R=R;d.OUT=R/'transaction-v1'
d.MANIFEST='patches/season-refresh-installed.json';d.RECEIPT='patches/season-refresh-receipt.json';d.SELF='patches/season_refresh_preflight.py'
FILES=[('server','gamedata/fifadb.sqlite','fifadb.sqlite'),('client','data/data_0.big','data_0.big'),
 ('server','gamedata/custom_rosters.json','custom_rosters.json'),('server','responses/static_roster.json','static_roster.json'),
 ('server','http_config.py','http_config.py'),('server','product_packs.py','product_packs.py'),('server','npc_exchange.py','npc_exchange.py'),
 ('server','season_retirement.py','season_retirement.py'),('server','gamedata/season_refresh_products.json','season_refresh_products.json'),
 ('server','gamedata/all_item_icon_manifest.json','all_item_icon_manifest.json')]
d.TARGETS={(root,rel) for root,rel,_ in FILES}|{('server','play-local.bat'),('server',d.SELF)}
def prepare():
    proof=d.read(B/'build.json')
    for p,h in proof['sources'].items():assert d.tx.sha(p)==h,('Source drift',p)
    for p,h in proof['files'].items():assert d.tx.sha(B/p)==h,('Built input drift',p)
    out=d.OUT;assert not out.exists();out.mkdir()
    template=(S/'patches/native_roster_preflight.py').read_text('utf-8').replace('native-roster','season-refresh').replace('native_roster','season_refresh').replace('NATIVE_ROSTER','SEASON_REFRESH')
    required={(root,rel.casefold()) for root,rel in d.TARGETS}
    template=re.sub(r'^    required=.*$',lambda _: '    required='+repr(required),template,flags=re.M)
    (out/'season_refresh_preflight.py').write_text(template,'utf-8')
    play=(S/'play-local.bat').read_bytes();name=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode();parentrel='patches/'+name
    parent=d.load(S/parentrel,'season_refresh_parent');check=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
    (out/'play-local.bat').write_bytes(play.replace(('patches\\'+name).encode(),b'patches\\season_refresh_preflight.py'))
    payloads=[(root,rel,B/source) for root,rel,source in FILES]+[('server','play-local.bat',out/'play-local.bat'),('server',d.SELF,out/'season_refresh_preflight.py')]
    rows=[dict(root=root,relative=rel,source=str(source),parent_sha256=d.tx.digest((S if root=='server' else C)/rel),sha256=d.tx.sha(source)) for root,rel,source in payloads]
    guards={(r['root'],r['relative'].replace('\\','/').casefold()):r for r in comp['guards']}
    for row in rows:guards[(row['root'],row['relative'].casefold())]={k:row[k] for k in ('root','relative','sha256')}
    comp.update(guards=list(guards.values()),files_verified=False)
    parent_files={p:d.tx.sha(S/p) for p in (parentrel,parent.MANIFEST,parent.RECEIPT)}
    comp.setdefault('ancestry',[]).append(dict(layer='season-refresh',parent=parent_files,native_status='PENDING'))
    m=dict(schema=1,revision='season-refresh-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'),client=str(C),state_shop_replaced=False,
      guards=list(guards.values()),composition=comp,files=rows,parent_files=parent_files,parent_preflight=parentrel)
    d.write(out/'manifest.json',m);d.write(out/'prepared.json',dict(parent=check,manifest_sha256=d.tx.sha(out/'manifest.json')))
    print(json.dumps(dict(status='PREPARED',parent=check['status'],files=len(rows),manifest_sha256=d.tx.sha(out/'manifest.json'))),flush=True)
def preview(roots):
    m=d.read(d.OUT/'manifest.json');assert len(m['files'])==len(d.TARGETS) and {(r['root'],r['relative']) for r in m['files']}==d.TARGETS
    assert m['state_shop_replaced'] is False
    for rel,h in m['parent_files'].items():assert d.tx.sha(roots['server']/rel)==h,('Parent changed',rel)
    check=d.load(roots['server']/m['parent_preflight'],'season_refresh_live_parent').preflight(**roots)
    for row in m['files']:
        assert d.tx.sha(row['source'])==row['sha256']
        assert d.tx.digest(d.tx.target(roots,row))==row['parent_sha256'],('Target changed',row['relative'])
    return m,check
d.preview=preview
def gameclosed():
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0'],creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('Game is running; no forced exit')
def main():
    assert d.read(R/'test-results.json')['status']=='PASS'
    assert d.read(R/'io-tests.json')['status']=='PASS'
    coord=d.read(Path('D:/fifaol3/coordination-current.json'))
    assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer'),'Another writer requires handoff'
    with d.locks(S):
        gameclosed();prepare();preview(dict(server=S,client=C))
        error=None
        try:
            stop=r"$ErrorActionPreference='Stop'; $managed=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:\\FO3ID\\server\\(?:start_all|http_config|messenger)\.py' }; foreach($p in $managed){Stop-Process -Id $p.ProcessId -ErrorAction SilentlyContinue};exit 0"
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',stop],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            gameclosed();d.stopped();result=d.install(review_sha=d.tx.sha(d.OUT/'manifest.json'))
        except BaseException as e:
            error=e
            play=(S/'play-local.bat').read_bytes();n=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode();d.load(S/'patches'/n,'recover_parent').preflight(S,C)
        env={**os.environ,'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'}
        with (R/'formal.stdout.log').open('ab') as out,(R/'formal.stderr.log').open('ab') as err:
            p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        ready=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,env=env,capture_output=True,text=True)
        if ready.returncode:raise RuntimeError(ready.stdout+ready.stderr)
        if error:raise error
        result.update(service_restart=True,launcher_pid=p.pid,readiness=ready.stdout.strip());d.write(R/'cutover-result.json',result);print(json.dumps(result))
if __name__=='__main__':main()
