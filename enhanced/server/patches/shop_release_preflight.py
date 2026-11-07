"""Read-only startup check for the shop-only production release."""
from pathlib import Path
import hashlib,json,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def inside(root,relative):
    root=Path(root).resolve();relative=Path(relative)
    if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('Non-relative release path')
    path=(root/relative).resolve()
    if path==root or not path.is_relative_to(root):raise RuntimeError('Release path escapes explicit root')
    return path
def verify_files(m,server,client):
    roots={'server':Path(server).resolve(),'client':Path(client).resolve()};seen=set()
    for entry in m['files']:
        pair=(entry['root'],entry['relative'].replace('\\','/').casefold())
        if pair in seen:raise RuntimeError('Duplicate canonical release target')
        seen.add(pair);path=inside(roots[entry['root']],entry['relative'])
        if not path.is_file() or sha(path)!=entry['sha256']:raise RuntimeError('Installed shop release missing/edited: '+entry['relative'])
    for entry in m['unchanged']:
        path=inside(roots[entry['root']],entry['relative'])
        if not path.is_file() or sha(path)!=entry['sha256']:raise RuntimeError('Stable DB/BIG/language/dependency differs: '+entry['relative'])
    return {'server':str(roots['server']),'client':str(roots['client']),'files':len(m['files']),'stable_guards':len(m['unchanged'])}
def preflight(server=None,client=None):
    server=Path(server or HERE.parent).resolve();manifest=server/'patches/shop-release-manifest.json';receipt=server/'patches/shop-release-installed.json'
    m=read(manifest);r=read(receipt)
    if r.get('status')!='INSTALLED' or r.get('manifest_sha256')!=sha(manifest) or r.get('release_id')!=m['release_id']:raise RuntimeError('No exact installed shop release receipt')
    proof=r.get('native_proof',{})
    if proof.get('status')!='PASS' or proof.get('release_manifest_sha256')!=sha(manifest):raise RuntimeError('Native proof does not match installed release')
    result=verify_files(m,server,client or m['client_root'])
    return dict(result,status='READ_ONLY_SHOP_RELEASE_PREFLIGHT_PASS',state_shop_touched=False)
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
