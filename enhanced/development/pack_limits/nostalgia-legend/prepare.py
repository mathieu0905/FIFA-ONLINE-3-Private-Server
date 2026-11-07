from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;E=R.parent/'elite';S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
parent=load(S/'patches/elite_chains_preflight.py','nostalgia_legend_parent');parent.preflight(S,C)
source=(S/'http_config.py').read_text(encoding='utf8')
old='(20043, "Pemain season legenda", _S(*TC_LEGENDS), ("", "ovr", 4), None),'
new='(20043, "Pemain season legenda", _S(*TC_LEGENDS, 19), ("", "ovr", 4), None),'
assert source.count(old)==1
(R/'http_config.py').write_text(source.replace(old,new),encoding='utf8')
gate=(S/'patches/elite_chains_preflight.py').read_text(encoding='utf8')
gate=gate.replace('elite-chains-release','nostalgia-legend-release').replace('elite_chains_preflight','nostalgia_legend_preflight').replace('ELITE_PRODUCT_CHAINS','NOSTALGIA_LEGEND_SET').replace("layer='elite-product-chains'","layer='nostalgia-legend-set'")
gate=gate.replace("('product_packs.py','gamedata/product_chain_elite.json','play-local.bat',SELF)","('http_config.py','play-local.bat',SELF)")
(R/'nostalgia_legend_preflight.py').write_text(gate,encoding='utf8')
launcher=(S/'play-local.bat').read_bytes();assert launcher.count(b'elite_chains_preflight.py')==1
(R/'play-local.bat').write_bytes(launcher.replace(b'elite_chains_preflight.py',b'nostalgia_legend_preflight.py'))
installer=(E/'install.py').read_text(encoding='utf8')
installer=installer.replace("('product_packs.py','gamedata/product_chain_elite.json','play-local.bat','patches/elite_chains_preflight.py')","('http_config.py','play-local.bat','patches/nostalgia_legend_preflight.py')")
installer=installer.replace('len(keys)!=4','len(keys)!=3').replace('len(set(keys))!=4','len(set(keys))!=3').replace('exactly four','exactly three').replace("{'product_packs.py','play-local.bat'}","{'http_config.py','play-local.bat'}")
installer=installer.replace('elite-chains-release','nostalgia-legend-release').replace('elite_chains_preflight','nostalgia_legend_preflight').replace('ELITE_PRODUCT_CHAINS','NOSTALGIA_LEGEND_SET').replace('elite-product-chains-v1','nostalgia-legend-set-v1')
(R/'install.py').write_text(installer,encoding='utf8')
rows=[]
for name,local in [('http_config.py','http_config.py'),('play-local.bat','play-local.bat'),('patches/nostalgia_legend_preflight.py','nostalgia_legend_preflight.py')]:
    out=R/'payload/server'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((R/local).read_bytes())
    rows.append(dict(root='server',relative=name,parent_sha256=sha(S/name) if (S/name).exists() else None,sha256=sha(out)))
m=dict(schema=1,release_id='20261106-nostalgia-legend-set-v1',phase='NOSTALGIA_LEGEND_SET',state_shop_replaced=False,client_root=str(C),parent_preflight=parent.SELF,parent_manifest=parent.MANIFEST,parent_identity={n:sha(S/n) for n in (parent.SELF,parent.MANIFEST,parent.RECEIPT)},files=rows)
(R/'nostalgia-legend-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PREPARED',targets=len(rows))))
