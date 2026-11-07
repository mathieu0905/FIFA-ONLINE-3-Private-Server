from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;E=R.parent/'elite';S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
parent=load(S/'patches/nostalgia_legend_preflight.py','nostalgia_legend_parent');parent.preflight(S,C)
source=(S/'http_config.py').read_text(encoding='utf8')
old='(20043, "Pemain season legenda", _S(*TC_LEGENDS, 19), ("", "ovr", 4), None),'
new=old.replace('"ovr", 4','"ovr", 2')
assert source.count(old)==1
source=source.replace(old,new)
old='"description": desc, "boostgroups": _tc_special_groups(b, min(5, sets[cid][1]))}'
new='"description": desc, "boostgroups": _tc_groups((5, 6, 2), (7, 8, 2), (9, 11, 2)) if cid == 20043 else _tc_special_groups(b, min(5, sets[cid][1]))}'
assert source.count(old)==1
(R/'http_config.py').write_text(source.replace(old,new),encoding='utf8')
gate=(S/'patches/nostalgia_legend_preflight.py').read_text(encoding='utf8').replace('nostalgia-legend-release','legend-plus2-release').replace('nostalgia_legend_preflight','legend_plus2_preflight').replace('NOSTALGIA_LEGEND_SET','LEGEND_PLUS_TWO_SET').replace("layer='nostalgia-legend-set'","layer='legend-plus2'")
(R/'legend_plus2_preflight.py').write_text(gate,encoding='utf8')
launcher=(S/'play-local.bat').read_bytes();assert launcher.count(b'nostalgia_legend_preflight.py')==1
(R/'play-local.bat').write_bytes(launcher.replace(b'nostalgia_legend_preflight.py',b'legend_plus2_preflight.py'))
installer=(R.parent/'nostalgia-legend/install.py').read_text(encoding='utf8').replace('nostalgia-legend-release','legend-plus2-release').replace('nostalgia_legend_preflight','legend_plus2_preflight').replace('NOSTALGIA_LEGEND_SET','LEGEND_PLUS_TWO_SET').replace('nostalgia-legend-set-v1','legend-plus2-v1')
(R/'install.py').write_text(installer,encoding='utf8')
rows=[]
for name,local in [('http_config.py','http_config.py'),('play-local.bat','play-local.bat'),('patches/legend_plus2_preflight.py','legend_plus2_preflight.py')]:
    out=R/'payload/server'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((R/local).read_bytes())
    rows.append(dict(root='server',relative=name,parent_sha256=sha(S/name) if (S/name).exists() else None,sha256=sha(out)))
m=dict(schema=1,release_id='20261106-legend-plus2-v1',phase='LEGEND_PLUS_TWO_SET',state_shop_replaced=False,client_root=str(C),parent_preflight=parent.SELF,parent_manifest=parent.MANIFEST,parent_identity={n:sha(S/n) for n in (parent.SELF,parent.MANIFEST,parent.RECEIPT)},files=rows)
(R/'legend-plus2-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PREPARED',targets=len(rows))))
