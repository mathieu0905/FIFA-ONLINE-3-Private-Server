from pathlib import Path
import hashlib,importlib.util,json,re,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');B=R.parent/'nostalgia-stats2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,n):
    spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
build=json.loads((R/'build-results.json').read_text(encoding='utf8'));assert sha(Path(build['source']))==build['source_sha256']
play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches[\\/][a-z_0-9]+_preflight\.py',play);assert len(names)==1
parent_path=names[0].decode().replace('\\','/');parent=load(S/parent_path,'search_parent');parent.preflight(S,C)
gate=(B/'nostalgia_stats_preflight.py').read_text(encoding='utf8').replace('nostalgia-stats-release','choice-search-release').replace('nostalgia_stats_preflight','choice_search_preflight').replace('NOSTALGIA_STATS_PLUS_TWO','CHOICE_SEARCH_CALLBACK_FIX').replace("layer='nostalgia-stats-plus2'","layer='choice-search-callback-fix'")
old="TARGETS={('server',n) for n in ('http_config.py','play-local.bat','gamedata/fifadb.sqlite',SELF)} | {('client','data/data_0.big')}"
new="TARGETS={('server','play-local.bat'),('server',SELF),('client','data/ui/TeamManagementDraftPackScreen.big'.casefold())}"
assert gate.count(old)==1;gate=gate.replace(old,new);(R/'choice_search_preflight.py').write_text(gate,encoding='utf8')
(R/'play-local.bat').write_bytes(play.replace(names[0],b'patches\\choice_search_preflight.py'))
installer=(B/'install.py').read_text(encoding='utf8').replace('nostalgia-stats-release','choice-search-release').replace('nostalgia_stats_preflight','choice_search_preflight').replace('NOSTALGIA_STATS_PLUS_TWO','CHOICE_SEARCH_CALLBACK_FIX').replace('nostalgia-stats-plus2-v1','choice-search-callback-v1')
old="EXPECTED={('server',n) for n in ('http_config.py','play-local.bat','gamedata/fifadb.sqlite','patches/choice_search_preflight.py')} | {('client','data/data_0.big')}"
assert installer.count(old)==1;installer=installer.replace(old,"EXPECTED={('server','play-local.bat'),('server','patches/choice_search_preflight.py'),('client','data/ui/teammanagementdraftpackscreen.big')}")
installer=installer.replace('len(keys)!=5','len(keys)!=3').replace('len(set(keys))!=5','len(set(keys))!=3').replace('exactly five reviewed dual-database','exactly three reviewed search-UI')
start=installer.index('def blocking_processes(rows):');end=installer.index('\n@contextmanager',start)
installer=installer[:start]+'''def blocking_processes(rows):
    query="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'fifazf.exe' } | Select-Object -ExpandProperty ProcessId"
    return [int(value) for value in subprocess.check_output(['powershell.exe','-NoProfile','-Command',query],text=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).split()]
''' +installer[end:]
(R/'install.py').write_text(installer,encoding='utf8')
rows=[]
for root,name,local in [('client','data/ui/TeamManagementDraftPackScreen.big','TeamManagementDraftPackScreen.big'),('server','play-local.bat','play-local.bat'),('server','patches/choice_search_preflight.py','choice_search_preflight.py')]:
    target=(S if root=='server' else C)/name;out=R/'payload'/root/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((R/local).read_bytes());rows.append(dict(root=root,relative=name,parent_sha256=sha(target) if target.exists() else None,sha256=sha(out)))
m=dict(schema=1,release_id='20261106-choice-search-callback-v1',phase='CHOICE_SEARCH_CALLBACK_FIX',state_shop_replaced=False,client_root=str(C),parent_preflight=parent_path,parent_manifest=parent.MANIFEST,parent_identity={n:sha(S/n) for n in (parent_path,parent.MANIFEST,parent.RECEIPT)},files=rows)
(R/'choice-search-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
t=(B/'test_install.py').read_text(encoding='utf8').replace('nostalgia_stats_preflight','choice_search_preflight').replace('nostalgia-stats-release','choice-search-release')
t=t.replace("first=roots['server']/m['files'][0]['relative']","first=roots[m['files'][0]['root']]/m['files'][0]['relative']")
t=t.replace("if source.suffix.lower() in ('.py','.json','.html','.bat','.ps1'):","if source.name.casefold()=='teammanagementdraftpackscreen.big' or source.suffix.lower() in ('.py','.json','.html','.bat','.ps1'):")
(R/'test_install.py').write_text(t,encoding='utf8');print(json.dumps(dict(status='PREPARED',parent=parent_path,targets=3)))
