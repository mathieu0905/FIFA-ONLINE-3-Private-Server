"""Read-only FC retirement layer over the exact current installed parent."""
from pathlib import Path
import hashlib, importlib.util, json
MANIFEST='patches/fc-retirement-release-manifest.json'
RECEIPT='patches/fc-retirement-release-installed.json'
SELF='patches/fc_retirement_preflight.py'
ALLOWED={('server',n) for n in ('gamedata/custom_rosters.json','legend_moments_bulk_npc.py','play-local.bat',SELF)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent)
    m=read(server/MANIFEST);client=Path(client or m['client_root'])
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('FC retirement parent changed: '+n)
    spec=importlib.util.spec_from_file_location('fc_retirement_parent',server/'patches/player_value_preflight.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    c,v=p._compose(server,client);guards=v.table(c['guards'])
    if set(v.table(m['files']))!=ALLOWED:raise RuntimeError('Wrong retirement scope')
    v.replace(guards,m['files'],{('server',SELF):None},ALLOWED)
    r=read(server/RECEIPT)
    if r['status']!='INSTALLED_FC13_RETIREMENT' or r['manifest_sha256']!=sha(server/MANIFEST):raise RuntimeError('Retirement receipt mismatch')
    for n in (MANIFEST,RECEIPT):guards[('server',n.casefold())]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(guards.values())
    result=v.verify_manifest(c,server,client)
    registry=read(server/'gamedata/custom_rosters.json')
    assert 13028130 not in {r['fo3_spid'] for r in registry['cards']}
    assert len(next(s for s in registry['seasons'] if s['id']==13)['cards'])==257
    result['status']='READ_ONLY_FC13_RETIREMENT_PASS'
    return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
