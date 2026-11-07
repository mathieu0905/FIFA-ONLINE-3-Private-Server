# Temporary main-version diagnostic: original EXP page, same full XP30 backend and Module.
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MANIFEST='patches/console-backpressure-release-manifest.json'
RECEIPT='patches/console-backpressure-release-installed.json'
SELF='patches/console_backpressure_preflight.py'
PARENT='patches/bulk_seasons_preflight.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise RuntimeError('Duplicate diagnostic metadata key')
            d[k]=v
        return d
    return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def parent(server,m):
    required={'patches/bulk_seasons_preflight.py','patches/bulk-seasons-release-manifest.json','patches/bulk-seasons-release-installed.json'}
    if set(m['parent_bulk_files'])!=required:raise RuntimeError('Wrong diagnostic bulk parent identity set')
    for n,h in m['parent_bulk_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Protected bulk source changed: '+n)
    if sha(server/PARENT)!='3b97d4faca41a466d4035137fe11b15ae5f12f152b1f778f797f311a17596fb2':raise RuntimeError('Unreviewed bulk composer source')
    spec=importlib.util.spec_from_file_location('protected_xp_parent',server/PARENT);xp=importlib.util.module_from_spec(spec);spec.loader.exec_module(xp)
    return xp
def _compose(server,client,m,installed=True):
    server=Path(server).resolve();client=Path(client).resolve()
    if m.get('phase')!='CONSOLE_BACKPRESSURE_COMPAT_ON_BULK' or m.get('adopt_existing_console_fix') is not True:raise RuntimeError('Not the narrow diagnostic scope')
    if installed:
        r=read(server/RECEIPT)
        if r.get('status')!='INSTALLED_CONSOLE_BACKPRESSURE_COMPAT' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('release_id')!=m['release_id'] or r.get('start_all_written') is not False:raise RuntimeError('Diagnostic receipt identity mismatch')
    bulk=parent(server,m);c,v=bulk._compose(server,client);guards=v.table(c['guards']);rows=v.table(m['files'])
    allowed={('server','start_all.py'),('server','play-local.bat'),('server',SELF)}
    if set(rows)!=allowed:raise RuntimeError('Wrong console compatibility row set')
    adopt=rows[('server','start_all.py')]
    if adopt['parent_sha256']!='b4130490f83b472801f2cc100c2817b22ab2a697eb24634673dfb9705b31837d' or adopt['sha256']!='12b633a961b91288341d629dc5b92d82e244fc698f3b06657657f35baace61a0':raise RuntimeError('Wrong audited console adoption pair')
    v.replace(guards,m['files'],{('server',SELF):None},allowed)
    if installed:
        for n in (MANIFEST,RECEIPT):guards[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
        c['ancestry'].append(dict(layer='console-backpressure-compat',adopted_already_deployed_fix=True,start_all_written=False,native_status='INFORMATIONAL_ONLY'))
    c['guards']=list(guards.values());c['files_verified']=False
    return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST);return _compose(server,client or m['client_root'],m)[0]
def preflight(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST);c,v=_compose(server,client or m['client_root'],m);result=v.verify_manifest(c,server,client or m['client_root']);result['status']='READ_ONLY_CONSOLE_BACKPRESSURE_COMPAT_PASS';result['diagnostic_only']=True;result['requirements_completed']=False;return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))