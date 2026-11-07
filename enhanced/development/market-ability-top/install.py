from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,ssl,subprocess,sys,time,urllib.request
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def module(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args):
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def stop():
 run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
 run(['powershell.exe','-NoProfile','-Command',r"Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:\\FO3ID\\server\\start_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }"])
 time.sleep(.5)
def start():
 with (P/'service.stdout.log').open('ab') as out,(P/'service.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20'),stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 return p.pid
def api(path):
 url=('http://127.0.0.1:8088'+path) if path.startswith('/api/') else 'https://127.0.0.1'+path
 with urllib.request.urlopen(url,context=ssl._create_unverified_context(),timeout=10) as response:return json.load(response)
owned=[];written=[];beforebytes={};afterhash={};stopped=False
try:
 for name in ('.shop-release.lock','.fo3-publish.lock'):
  p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);v=body(dict(owner='market-ability-top',pid=os.getpid(),scope='market_simulation.py,new gate/meta/play',handoff=str(P/'installed-handback.json')));os.write(fd,v);os.fsync(fd);owned.append((p,fd,v))
 print('LOCKED',flush=True)
 play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert match;parentrel='patches/'+match[1].decode();parent=module(S/parentrel,'_top_parent');checked=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
 print('PARENT_PASS',parentrel,checked['files'],flush=True)
 for rel,digest in json.loads((P/'baseline.json').read_text()).items():assert sha(S/rel)==digest,'Concurrent source change; rebase '+rel
 assert json.loads((P/'regression.json').read_text())['status']=='PASS'
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):copy.deepcopy(g) for g in composition['guards']};assert len(guards)==len(composition['guards']);oldkeys=set(guards)
 stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');revision='market-ability-top-'+stamp;backup=S/'backups'/revision;backup.mkdir()
 targets={'market_simulation.py':(P/'market_simulation.py').read_bytes(),'patches/market_ability_top_preflight.py':(P/'market_ability_top_preflight.py').read_bytes(),'play-local.bat':play.replace(match[0],b'patches\\market_ability_top_preflight.py')}
 M='patches/market-ability-top-installed.json';R='patches/market-ability-top-receipt.json';assert not (S/M).exists() and not (S/R).exists()
 for rel,v in targets.items():
  p=S/rel
  if p.exists():
   assert sha(p)==guards[('server',rel.casefold())]['sha256'];beforebytes[rel]=p.read_bytes();dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(beforebytes[rel])
  else:assert ('server',rel.casefold()) not in guards;beforebytes[rel]=None
  if rel.endswith('.py'):compile(v.decode('utf-8-sig'),rel,'exec')
 state=json.loads((S/'gamedata/state.json').read_text('utf8'))
 if state.get('match',{}).get('stage') not in (None,'closed','finished'):
  open_game=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW).returncode==9
  if open_game:raise RuntimeError('MATCH_ACTIVE_RESTART_DEFERRED')
 stop();stopped=True
 for rel in ('gamedata/state.json','gamedata/shop.json'):shutil.copyfile(S/rel,backup/Path(rel).name)
 for rel,v in targets.items():
  p=S/rel;assert (p.read_bytes() if p.exists() else None)==beforebytes[rel];tmp=p.with_name(p.name+'.top-market');tmp.write_bytes(v);os.replace(tmp,p);written.append(rel);afterhash[rel]=sha(p);guards[('server',rel.casefold())]=dict(root='server',relative=rel,sha256=afterhash[rel])
 assert oldkeys<=set(guards)
 comp=copy.deepcopy(composition);comp['guards']=list(guards.values());comp.setdefault('ancestry',[]).append(dict(layer='market-ability-top',revision=revision,native_status='PENDING',ranking='actual listed ability descending',stock_policy='existing supply rotation retained'))
 receiptpath=getattr(parent,'RECEIPT',None)
 if receiptpath:
  r=json.loads((S/receiptpath).read_text('utf-8-sig'));policy=dict(root='server',relative=receiptpath,installation_fields={k:v for k,v in r.items() if k!='native_status'})
  if not any(p['root']==policy['root'] and p['relative'].casefold()==policy['relative'].casefold() for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),parent=parentrel,guards=list(guards.values()),composition=comp,state_shop_replaced=False,backup=str(backup),source_hashes=afterhash)
 mb=body(manifest);rb=body(dict(status='INSTALLED_MARKET_ABILITY_TOP',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),native_status='PENDING',state_shop_replaced=False))
 for rel,v in ((M,mb),(R,rb)):(S/rel).write_bytes(v);beforebytes[rel]=None;written.append(rel);afterhash[rel]=sha(S/rel)
 checker=module(S/'patches/market_ability_top_preflight.py','_top_final');preflight=checker.preflight(S,C);print('NEW_PREFLIGHT_PASS',preflight['files'],flush=True)
 parentpid=start();stopped=False;deadline=time.monotonic()+50;status=None
 while time.monotonic()<deadline:
  try:
   status=api('/api/market_status')
   if status['background']['running'] and status['background']['errors']==0 and status.get('top_policy'):break
  except Exception as e:err=str(e)
  time.sleep(.5)
 else:raise RuntimeError('New market failed startup '+str(status or locals().get('err')))
 from verify_live import verify
 verification=verify(api);top=verification['top_rows']
 moment=api('/transfer/search/84037576');assert moment,'Moment Ronaldo still unavailable';assert status['npc_exchange']['price_store']['runtime_model_loaded'] is False
 after=json.loads((S/'gamedata/state.json').read_text('utf8'));before=json.loads((backup/'state.json').read_text('utf8'));asset_equal={k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'}
 report=dict(status='INSTALLED_AND_LIVE',revision=revision,parent=parentrel,top='patches/market_ability_top_preflight.py',compose_api='compose_manifest(server=None,client=None)',preflight=preflight,backup=str(backup),services_parent_pid=parentpid,ability_verification=verification,top_rows=top,moment_ronaldo_rows=moment,background=status['background'],asset_projection_equal=asset_equal,shop_equal=sha(S/'gamedata/shop.json')==sha(backup/'shop.json'),state_shop_replaced=False,price_model_reinitialized=False,native_verified=False,hashes={rel:sha(S/rel) for rel in ('patches/market_ability_top_preflight.py',M,R)},locks_released_on_exit=True)
 (P/'installed-handback.json').write_bytes(body(report));descriptor=dict(status='INSTALLED_MARKET_ABILITY_TOP_API_PASS_NATIVE_PENDING',observed_at=datetime.datetime.now().isoformat(),top_preflight=str(S/'patches/market_ability_top_preflight.py'),top_manifest=str(S/M),top_receipt=str(S/R),files={str(S/rel):sha(S/rel) for rel in ('patches/market_ability_top_preflight.py',M,R,'play-local.bat')},composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),handoff=str(P/'installed-handback.json'),services_restored=True,state_shop_written=False,native_verified=False,preflight=preflight);(W/'root-current-top.json').write_bytes(body(descriptor))
 print(json.dumps(dict(status=report['status'],abilities=verification["abilities"],moment_ronaldo_stock=[(r['grade'],r['count']) for r in moment],assets_unchanged=asset_equal),ensure_ascii=False),flush=True)
except Exception:
 if written:
  try:stop();stopped=True
  except Exception as e:print('Rollback stop failed',repr(e),file=sys.stderr)
  for rel in reversed(written):
   p=S/rel
   if p.exists() and sha(p)==afterhash[rel]:
    if beforebytes[rel] is None:p.unlink()
    else:p.write_bytes(beforebytes[rel])
 if stopped:start()
 raise
finally:
 for p,fd,v in reversed(owned):
  os.close(fd)
  if p.exists() and p.read_bytes()==v:p.unlink()
