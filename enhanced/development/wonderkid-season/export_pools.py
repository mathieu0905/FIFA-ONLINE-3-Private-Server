from pathlib import Path
import hashlib,json,os,shutil,sqlite3,sys,tempfile,types
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
T=Path(tempfile.mkdtemp(prefix='pool-read-',dir=R));(T/'gamedata').mkdir()
for p in S.glob('*.json'):shutil.copyfile(p,T/p.name)
for p in (S/'gamedata').glob('*.json'):shutil.copyfile(p,T/'gamedata'/p.name)
shutil.copytree(S/'responses',T/'responses');os.link(S/'gamedata/fifadb.sqlite',T/'gamedata/fifadb.sqlite')
with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(T/'gamedata/npc-market-prices.sqlite') as dest:src.backup(dest)
def audit(event,args):
    if event=='open':
        path,mode,flags=args
        if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Non-temporary write rejected')
sys.addaudithook(audit)
sys.path.insert(0,str(S));sys.argv=['http_config.py'];os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
h=types.ModuleType('http_config');h.__file__=str(T/'http_config.py');sys.modules['http_config']=h
source=(S/'http_config.py').read_text('utf-8');exec(compile(source,h.__file__,'exec'),h.__dict__)
pools={};grades={}
for i in h.PACKS:
    pools[str(i)]=h.pack_pool(i);grades[str(i)]=h.pack_grades(i)
out=dict(pools=pools,grades=grades,source_sha256=hashlib.sha256((S/'http_config.py').read_bytes()).hexdigest())
(R/'frozen-pools.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),'utf-8')
print(json.dumps(dict(packs=len(pools),rows=sum(map(len,pools.values())))),flush=True)
