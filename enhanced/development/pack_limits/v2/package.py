"""Freeze candidate payload and its exact current parent after all source rebasing."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
descriptor=json.loads(Path(r'D:\fifaol3\root-current-top.json').read_text(encoding='utf-8-sig'))
top=Path(descriptor['top_preflight']);manifest=Path(descriptor['top_manifest']);receipt=Path(descriptor['top_receipt'])
p=argparse.ArgumentParser();p.add_argument('--parent-preflight');args=p.parse_args()
if args.parent_preflight:top=Path(args.parent_preflight)
spec=importlib.util.spec_from_file_location('candidate_parent',top);parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
if args.parent_preflight:manifest=S/parent.MANIFEST;receipt=S/parent.RECEIPT
parent.preflight(S,C)
baseline=json.loads((R/'baseline.json').read_text())
for name,digest in baseline.items():assert sha(S/name)==digest,'Rebase candidate first: '+name
payload=R/'payload'
mapping={n:R/n for n in ('http_config.py','pack_catalogue.py','product_packs.py','pack_probability.py','admin.py','admin/index.html')}
mapping.update({'gamedata/product_packs.json':R/'product_packs.json','patches/product_packs_preflight.py':R/'product_packs_preflight.py'})
launcher=(S/'play-local.bat').read_bytes()
assert launcher.count(top.name.encode())==1
(R/'play-local.bat').write_bytes(launcher.replace(top.name.encode(),b'product_packs_preflight.py'))
mapping['play-local.bat']=R/'play-local.bat'
rows=[]
for name,source in mapping.items():
    destination=payload/'server'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    rows.append(dict(root='server',relative=name,parent_sha256=sha(S/name) if (S/name).exists() else None,sha256=sha(destination)))
name='data/ui/TeamManagementDraftPackScreen.big';source=R/'TeamManagementDraftPackScreen.big'
destination=payload/'client'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
rows.append(dict(root='client',relative=name,parent_sha256=sha(C/name),sha256=sha(destination)))
m=dict(schema=1,release_id='20261106-independent-product-packs-v1',phase='INDEPENDENT_PRODUCT_PACKS',state_shop_replaced=False,client_root=str(C),
       parent_preflight=top.relative_to(S).as_posix(),parent_manifest=manifest.relative_to(S).as_posix(),
       parent_identity={p.relative_to(S).as_posix():sha(p) for p in (top,manifest,receipt)},files=rows)
(R/'product-packs-release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PACKAGED',parent=str(top),targets=len(rows))))
