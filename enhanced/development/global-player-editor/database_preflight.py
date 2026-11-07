"""Exact-file read-only gate for a global player database revision."""
from pathlib import Path
import hashlib,json
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/'patches/player-database-installed.json').read_text('utf-8'))
    if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Wrong database scope')
    roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
    for r in m['guards']:
        root=roots[r['root']];target=(root/r['relative']).resolve();key=(r['root'],r['relative'].replace('\\','/').casefold())
        if not target.is_relative_to(root) or target==root or key in seen:raise RuntimeError('Invalid database guard')
        seen.add(key)
        if not target.is_file() or sha(target)!=r['sha256']:raise RuntimeError('Installed file differs: '+r['root']+'/'+r['relative'])
    required={('server','gamedata/fifadb.sqlite'),('client','data/data_0.big'),('server','play-local.bat'),('server','patches/player_database_preflight.py')}
    if not required<=seen:raise RuntimeError('Incomplete database guards')
    return dict(status='PLAYER_DATABASE_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],native_status='PENDING',state_shop_touched=False)
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
