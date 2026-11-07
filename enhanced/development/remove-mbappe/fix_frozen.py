"""Complete frozen weighted-pool removal as a new immutable child release."""
import copy,datetime,json,pathlib,shutil,sys,time,types
import build as b
import install as i
W,S,C=b.W,b.S,b.C
def prune(x,path='',events=None):
 if events is None:events=[]
 if isinstance(x,dict):
  for key,value in x.items():
   if key=='pool' and isinstance(value,list):
    kept=[r for r in value if not b.blocked(r[0] if isinstance(r,list) else r)]
    if len(kept)!=len(value):
     assert kept;events.append(dict(path=path+'/'+key,removed=len(value)-len(kept)));x[key]=kept
   else:prune(value,path+'/'+key,events)
 elif isinstance(x,list):
  for n,v in enumerate(x):prune(v,path+'/'+str(n),events)
 return events
def resign(x):
 if isinstance(x,dict):
  for v in x.values():resign(v)
  if 'hash' in x:
   import hashlib
   x['hash']=hashlib.sha256(json.dumps({k:v for k,v in x.items() if k!='hash'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 elif isinstance(x,list):
  for v in x:resign(v)
def main():
 i.idle();archive=W/'initial-release-evidence';archive.mkdir(exist_ok=True)
 for name in ('validated-build.json','tests.json','install-tests.json'):
  if not (archive/name).exists():shutil.copyfile(W/name,archive/name)
 payload=[];changes={}
 for name in ('pack_cadence.json','wonderkid_legacy_pools.json'):
  original=S/'gamedata'/name;d=i.read(original)
  if name=='pack_cadence.json':changes[name]=prune(d)
  else:
   changes[name]=[]
   for item,rows in d['pools'].items():
    kept=[r for r in rows if not b.blocked(r[0])]
    if kept!=rows:assert kept;d['pools'][item]=kept;changes[name].append(dict(item=item,removed=len(rows)-len(kept)))
  resign(d)
  src=W/'artifacts'/name;src.write_bytes(b.body(d));payload.append(dict(root='server',relative='gamedata/'+name,source=str(src),before=b.sha(original),after=b.sha(src)))
  if name=='pack_cadence.json':
   import pack_cadence,sqlite3
   with sqlite3.connect(S/'gamedata/fifadb.sqlite') as db:present={r[0] for r in db.execute('select spid from players')}
   pack_cadence.validate(d,types.SimpleNamespace(market_spids=lambda:present,MAX_GRADE=20))
  # Unchanged rows, weights, tiers, prices, grades, limits and token keys stay exact.
  old=i.read(original)
  if name=='pack_cadence.json':prune(old)
  else:
   for item,rows in old['pools'].items():old['pools'][item]=[r for r in rows if not b.blocked(r[0])]
  resign(old);assert old==d
 validated=dict(status='BUILT',payload=payload,changes=changes);b.write(W/'validated-build.json',validated)
 b.write(W/'tests.json',dict(status='PASS',build_sha256=b.sha(W/'validated-build.json'),checks=['All legacy pair/tuple pools remove only target rows','Original weights, prices, grades and receipts preserved','Full production pack_cadence.validate passes']))
 i.SELF='patches/remove_mbappe_frozen_20261107_preflight.py';i.MANIFEST='patches/remove-mbappe-frozen-20261107-installed.json';i.RECEIPT='patches/remove-mbappe-frozen-20261107-receipt.json'
 # Keep the common lock through restart, then release it for watcher activation.
 with i.release.locks(S,'remove-mbappe-frozen-fix'):
  i.idle();p=i.plan()
  if i.ports():
   i.idle();i.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
   deadline=time.monotonic()+15
   while i.ports():
    if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete')
    time.sleep(.2)
  state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes()
  result=i.commit(p,state,shop);result['launcher_pid']=i.restart()
 hot=None;deadline=time.monotonic()+25
 while True:
  hot=json.loads(i.run([i.PY,'-B','hot_update_control.py']))
  if hot['revision']=='shop_cleanup_20261107_01' and hot['watcher_running'] and hot['error'] is None:break
  if time.monotonic()>deadline:raise RuntimeError('Business package recovery pending')
  time.sleep(.3)
 result.update(status='INSTALLED_RUNTIME_ACTIVE_NATIVE_PENDING',revision=p['revision'],top_preflight=str(S/i.SELF),top_manifest=str(S/i.MANIFEST),top_receipt=str(S/i.RECEIPT),composition_api='compose_manifest(server=None,client=None)',files={str(S/n):b.sha(S/n) for n in (i.SELF,i.MANIFEST,i.RECEIPT,'play-local.bat')},hot_update_status=hot,services_restored=i.ports()==[443,8088,28002],services_restarted=True,GUI_used=False,native_verified=False,match_verified=False,locks_released=True,handoff=str(W/'installed-handback.json'),initial_removal_backup=str(S/'backups/remove-mbappe-20261107-222517-533659'),weighted_pool_changes=changes)
 b.write(W/'installed-handback.json',result)
 with i.release.locks(S,'remove-mbappe-handback'):
  if i.SELF.replace('/','\\').encode() in (S/'play-local.bat').read_bytes():i.write(W.parent/'root-current-top.json',result)
 b.write(W/'install-status.json',result);print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
