from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--parent-preflight');args=parser.parse_args()
descriptor=json.loads(Path(r'D:\fifaol3\root-current-top.json').read_text(encoding='utf-8-sig'))
top=Path(args.parent_preflight or descriptor['top_preflight'])
spec=importlib.util.spec_from_file_location('elite_parent',top);parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
parent.preflight(S,C)
baseline=json.loads((R/'baseline.json').read_text())
for name,digest in baseline.items():assert sha(S/name)==digest,'Rebase elite source: '+name
source=(R.parent/'v2/product_packs_preflight.py').read_text(encoding='utf8')
source=source.replace("MANIFEST='patches/product-packs-release-manifest.json'","MANIFEST='patches/elite-chains-release-manifest.json'").replace("RECEIPT='patches/product-packs-release-installed.json'","RECEIPT='patches/elite-chains-release-installed.json'").replace("SELF='patches/product_packs_preflight.py'","SELF='patches/elite_chains_preflight.py'")
start=source.index('TARGETS=');end=source.index('\n\ndef sha',start)
source=source[:start]+"TARGETS={('server',n) for n in ('product_packs.py','gamedata/product_chain_elite.json','play-local.bat',SELF)}"+source[end:]
source=source.replace("'INDEPENDENT_PRODUCT_PACKS'","'ELITE_PRODUCT_CHAINS'").replace("'INSTALLED_INDEPENDENT_PRODUCT_PACKS'","'INSTALLED_ELITE_PRODUCT_CHAINS'").replace('READ_ONLY_INDEPENDENT_PRODUCT_PACKS_PASS','READ_ONLY_ELITE_PRODUCT_CHAINS_PASS').replace("layer='independent-product-packs'","layer='elite-product-chains'")
anchor="    # Exact reviewed metadata projection of the frozen retirement-only parent."
assert source.count(anchor)==1
source=source.replace(anchor,"""    if hasattr(parent,'compose_manifest'):
        c=parent.compose_manifest(server,client)
        validator_path=server/'patches/startup_market_preflight.py'
        if sha(validator_path)!='49eafb6eaa5ec954bfc65c4460aec2a3f14e9bb93dbbf6547cedfded44393d8a':raise RuntimeError('Unreviewed shared validator')
        spec=importlib.util.spec_from_file_location('elite_shared_validator',validator_path)
        validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
        validator.table(c['guards'])
        return c,validator
"""+anchor,1)
(R/'elite_chains_preflight.py').write_text(source,encoding='utf8')
launcher=(S/'play-local.bat').read_bytes();assert launcher.count(top.name.encode())==1
(R/'play-local.bat').write_bytes(launcher.replace(top.name.encode(),b'elite_chains_preflight.py'))
mapping={'product_packs.py':R/'product_packs.py','gamedata/product_chain_elite.json':R/'product_chain_elite.json','play-local.bat':R/'play-local.bat','patches/elite_chains_preflight.py':R/'elite_chains_preflight.py'}
rows=[]
for name,path in mapping.items():
    output=R/'payload/server'/name;output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,output)
    rows.append(dict(root='server',relative=name,parent_sha256=sha(S/name) if (S/name).exists() else None,sha256=sha(output)))
manifest=S/parent.MANIFEST;receipt=S/parent.RECEIPT
m=dict(schema=1,release_id='20261106-elite-product-chains-v1',phase='ELITE_PRODUCT_CHAINS',state_shop_replaced=False,client_root=str(C),parent_preflight=top.relative_to(S).as_posix(),parent_manifest=manifest.relative_to(S).as_posix(),parent_identity={p.relative_to(S).as_posix():sha(p) for p in (top,manifest,receipt)},files=rows)
(R/'elite-chains-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
assert (R/'install.py').exists(), 'Reviewed server-only installer required'
assert (R/'test_install.py').exists(), 'Keep the reviewed concurrency fault corpus'
print(json.dumps(dict(status='OFFLINE_PACKAGED',parent=str(top),targets=len(rows))))
