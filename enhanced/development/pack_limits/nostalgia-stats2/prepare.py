from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;P=R.parent/'legend-plus2';S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,n):
    spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
build=json.loads((R/'build-results.json').read_text(encoding='utf8'));assert build['status']=='PASS'
assert all(sha(Path(p))==h for p,h in build['source_hashes'].items())
parent=load(S/'patches/legend_plus2_preflight.py','stats_parent');parent.preflight(S,C)
source=(S/'http_config.py').read_text(encoding='utf8')
old='(20043, "Pemain season legenda", _S(*TC_LEGENDS, 19), ("", "ovr", 2), None),';assert source.count(old)==1
source=source.replace(old,old.replace('"ovr", 2','"ovr", 4'))
old='"boostgroups": _tc_groups((5, 6, 2), (7, 8, 2), (9, 11, 2)) if cid == 20043 else _tc_special_groups(b, min(5, sets[cid][1]))'
assert source.count(old)==1;source=source.replace(old,'"boostgroups": _tc_special_groups(b, min(5, sets[cid][1]))')
(R/'http_config.py').write_text(source,encoding='utf8')
assert (R/'http_config.py').read_bytes()==(R.parent/'nostalgia-legend/http_config.py').read_bytes(),'Exact restoration to original mixed legend-set source failed'
gate=(S/'patches/legend_plus2_preflight.py').read_text(encoding='utf8').replace('legend-plus2-release','nostalgia-stats-release').replace('legend_plus2_preflight','nostalgia_stats_preflight').replace('LEGEND_PLUS_TWO_SET','NOSTALGIA_STATS_PLUS_TWO').replace("layer='legend-plus2'","layer='nostalgia-stats-plus2'")
old="TARGETS={('server',n) for n in ('http_config.py','play-local.bat',SELF)}"
new="TARGETS={('server',n) for n in ('http_config.py','play-local.bat','gamedata/fifadb.sqlite',SELF)} | {('client','data/data_0.big')}"
assert gate.count(old)==1;gate=gate.replace(old,new);(R/'nostalgia_stats_preflight.py').write_text(gate,encoding='utf8')
launcher=(S/'play-local.bat').read_bytes();assert launcher.count(b'legend_plus2_preflight.py')==1
(R/'play-local.bat').write_bytes(launcher.replace(b'legend_plus2_preflight.py',b'nostalgia_stats_preflight.py'))
installer=(P/'install.py').read_text(encoding='utf8').replace('legend-plus2-release','nostalgia-stats-release').replace('legend_plus2_preflight','nostalgia_stats_preflight').replace('LEGEND_PLUS_TWO_SET','NOSTALGIA_STATS_PLUS_TWO').replace('legend-plus2-v1','nostalgia-stats-plus2-v1')
old="EXPECTED={('server',n) for n in ('http_config.py','play-local.bat','patches/nostalgia_stats_preflight.py')}"
new="EXPECTED={('server',n) for n in ('http_config.py','play-local.bat','gamedata/fifadb.sqlite','patches/nostalgia_stats_preflight.py')} | {('client','data/data_0.big')}"
assert installer.count(old)==1;installer=installer.replace(old,new).replace('len(keys)!=3','len(keys)!=5').replace('len(set(keys))!=3','len(set(keys))!=5').replace('exactly three reviewed server-only','exactly five reviewed dual-database')
old="(key[1] in {'http_config.py','play-local.bat'})";assert installer.count(old)==1
installer=installer.replace(old,"(key != ('server','patches/nostalgia_stats_preflight.py'))")
(R/'install.py').write_text(installer,encoding='utf8')
rows=[]
for root,name,local in [('server','http_config.py','http_config.py'),('server','play-local.bat','play-local.bat'),('server','gamedata/fifadb.sqlite','fifadb.sqlite'),('client','data/data_0.big','data_0.big'),('server','patches/nostalgia_stats_preflight.py','nostalgia_stats_preflight.py')]:
    target=(S if root=='server' else C)/name;out=R/'payload'/root/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((R/local).read_bytes())
    rows.append(dict(root=root,relative=name,parent_sha256=sha(target) if target.exists() else None,sha256=sha(out)))
m=dict(schema=1,release_id='20261106-nostalgia-stats-plus2-v1',phase='NOSTALGIA_STATS_PLUS_TWO',state_shop_replaced=False,client_root=str(C),parent_preflight=parent.SELF,parent_manifest=parent.MANIFEST,parent_identity={n:sha(S/n) for n in (parent.SELF,parent.MANIFEST,parent.RECEIPT)},files=rows)
(R/'nostalgia-stats-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
t=(P/'test_install.py').read_text(encoding='utf8').replace('legend_plus2_preflight','nostalgia_stats_preflight').replace('legend-plus2-release','nostalgia-stats-release');(R/'test_install.py').write_text(t,encoding='utf8')
print(json.dumps(dict(status='PREPARED',targets=5)))
