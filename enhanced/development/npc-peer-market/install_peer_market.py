"""Locked direct production install; fresh parent, no state/shop replacement."""
from pathlib import Path
import os,sys,re,json,copy,hashlib,datetime,importlib.util,subprocess,shutil,time,urllib.request
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
body=lambda d:(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
load=lambda p,name:None

def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(args):
 result=subprocess.run(args,cwd=S,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
 return result.stdout

def start():
 env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (R/'live.stdout.log').open('ab') as out,(R/'live.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 return p.pid

owned=[];written=[];stopped=False;backup=None;baseline={};newhash={}
try:
 for rel in ('.shop-release.lock','.fo3-publish.lock'):
  p=S/rel;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|os.O_BINARY);value=body(dict(owner='npc-peer-market',pid=os.getpid(),scope='attribute +1 prices and autonomous NPC peers'));os.write(fd,value);os.fsync(fd);owned.append((p,fd,value))
 # No GUI or forced client exit. The server restart is permitted only while closed.
 if '--allow-live-restart' not in sys.argv:
  run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}; exit 0'])
 launcher=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\([A-Za-z_]+_preflight\.py)',launcher);assert match
 parent_rel='patches/'+match[1].decode();parent=module(S/parent_rel,'npc_parent')
 checked=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):copy.deepcopy(g) for g in composed['guards']}
 assert len(guards)==len(composed['guards'])
 expected=json.loads((R/'engine-base.json').read_text('utf8'))['sha256'];assert sha(S/'market_simulation.py')==expected,'Market source changed; rebase required'
 http=(S/'http_config.py').read_bytes();needle=b'if __name__ == "__main__":';assert http.count(needle)==1
 updated_http=http.replace(needle,b'import npc_exchange\nnpc_exchange.install(sys.modules[__name__])\n\n'+needle)
 targets={'market_simulation.py':(R/'market_simulation.py').read_bytes(),'npc_exchange.py':(R/'npc_exchange.py').read_bytes(),'npc_attribute_value.py':(R/'npc_attribute_value.py').read_bytes(),'gamedata/npc_attribute_value.json':(R/'attributes-value-model.json').read_bytes(),'http_config.py':updated_http,'patches/npc_peer_market_preflight.py':(R/'npc_peer_market_preflight.py').read_bytes(),'play-local.bat':launcher.replace(match[0],b'patches\\npc_peer_market_preflight.py')}
 for rel in targets:
  p=S/rel;key=('server',rel.casefold())
  if p.exists():
   assert key in guards and sha(p)==guards[key]['sha256'],rel
   baseline[rel]=p.read_bytes()
  else:assert key not in guards;baseline[rel]=None
  if rel.endswith('.py'):compile(targets[rel].decode('utf-8-sig'),rel,'exec')
 stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=S/'backups'/('npc-peer-market-'+stamp);backup.mkdir()
 for rel,raw in baseline.items():
  if raw is not None:
   target=backup/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 for rel,raw in targets.items():
  p=S/rel;assert (p.read_bytes() if p.exists() else None)==baseline[rel],rel
  tmp=p.with_name(p.name+'.npc-tmp');tmp.write_bytes(raw);os.replace(tmp,p);written.append(rel);newhash[rel]=sha(p)
  guards[('server',rel.casefold())]=dict(root='server',relative=rel,sha256=newhash[rel])
 composition=copy.deepcopy(composed);composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='npc-peer-market',native_status='PENDING',model='attribute-only-plus1',grade_curve='inherited',old_packs_replaced=False))
 revision='npc-peer-market-'+stamp;M='patches/npc-peer-market-installed.json';P='patches/npc-peer-market-receipt.json'
 assert not (S/M).exists() and not (S/P).exists()
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=list(guards.values()),composition=composition,parent=parent_rel,backup=str(backup),source_hashes=newhash)
 for rel,raw in ((M,body(manifest)),(P,body(dict(status='INSTALLED_NPC_PEER_MARKET',revision=revision,manifest_sha256=hashlib.sha256(body(manifest)).hexdigest(),native_status='PENDING',state_shop_replaced=False)))):
  (S/rel).write_bytes(raw);baseline[rel]=None;written.append(rel);newhash[rel]=sha(S/rel)
 verifier=module(S/'patches/npc_peer_market_preflight.py','npc_new_preflight');report=verifier.preflight(S,C)
 (R/'preflight.json').write_bytes(body(report))
 run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')]);stopped=True
 # Snapshot actual state only after the existing worker has stopped.
 for rel in ('gamedata/state.json','gamedata/shop.json'):
  shutil.copyfile(S/rel,backup/Path(rel).name)
 parent_pid=start();stopped=False
 deadline=time.monotonic()+40;status=None;last_error=None
 while time.monotonic()<deadline:
  try:
   with urllib.request.urlopen('http://127.0.0.1:8088/api/market_status',timeout=3) as response:status=json.load(response)
   if status.get('npc_exchange',{}).get('initialized') and status['background']['running'] and status['background']['errors']==0:break
  except Exception as exc:last_error=str(exc)
  time.sleep(1)
 else:raise RuntimeError('NPC startup failed: '+str(status or last_error))
 before=json.loads((backup/'state.json').read_text('utf8'));after=json.loads((S/'gamedata/state.json').read_text('utf8'))
 def assets(s):
  s=copy.deepcopy(s);s.pop('market_simulation',None)
  for coach in s.get('coaches',[]):coach.pop('_market_owner',None)
  return s
 assert assets(before)==assets(after),'Business assets changed during install'
 assert sha(S/'gamedata/shop.json')==sha(backup/'shop.json')
 handoff=dict(status='INSTALLED_AND_RUNNING',revision=revision,top='patches/npc_peer_market_preflight.py',compose_api='compose_manifest(server=None,client=None)',preflight_api='preflight(server=None,client=None)',parent=parent_rel,preflight=report,backup=str(backup),services_parent_pid=parent_pid,model_scope='single-card +1 attribute value; old reference ratio supplies grade multipliers',player_assets_unchanged=True,state_shop_replaced=False,native_verified=False,initial_npc_status=status['npc_exchange'],hashes={rel:sha(S/rel) for rel in ('patches/npc_peer_market_preflight.py',M,P)},locks_released_on_exit=True)
 (R/'installed-handback.json').write_bytes(body(handoff))
 # Observation only; do not resume any paused coordinator goal.
 descriptor=dict(status='OBSERVED_NPC_PEER_INSTALLED',top_preflight=str(S/'patches/npc_peer_market_preflight.py'),top_manifest=str(S/M),top_receipt=str(S/P),files={str(S/rel):sha(S/rel) for rel in ('patches/npc_peer_market_preflight.py',M,P,'play-local.bat')},handoff=str(R/'installed-handback.json'),composition_available=True,state_shop_written=False,services_restored=True,GUI_status='NO_GUI; native pending',preflight=report)
 Path('D:/fifaol3/root-current-top.json').write_bytes(body(descriptor))
 print(json.dumps(dict(status=handoff['status'],top=handoff['top'],parent=parent_rel,guards=report['files'],npc=status['npc_exchange']),ensure_ascii=False),flush=True)
except Exception:
 # Restore only our exact after-images; never restore state/shop or another writer.
 if written:
  try:run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')]);stopped=True
  except Exception as stop_error:print('Rollback service stop failed:',repr(stop_error),file=sys.stderr)
  for rel in reversed(written):
   p=S/rel
   if p.exists() and sha(p)==newhash[rel]:
    old=baseline[rel]
    if old is None:p.unlink()
    else:p.write_bytes(old)
  if stopped:start()
 raise
finally:
 for p,fd,value in reversed(owned):
  os.close(fd)
  if p.exists() and p.read_bytes()==value:p.unlink()
