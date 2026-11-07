"""Client-only season19 name fix. No server stop/restart or game startup."""
from pathlib import Path
import copy,datetime,json,os,re,sys
sys.dont_write_bytecode=True;sys.path.insert(0,str(Path(__file__).resolve().parent))
from install_season import S,C,R,read,write,sha,load,closed
sys.path.insert(0,str(S));from player_editor.publish_database import transaction
from verify_live import business
O=R/'name-callback';B=O/'callback-v1';stage=O/'release-v1'
SELF='patches/nostalgia_name_preflight.py';MANIFEST='patches/nostalgia-name-installed.json';RECEIPT='patches/nostalgia-name-receipt.json'
def run():
 build=read(B/'build.json');replay=read(B/'replay.json');assert replay['changed_seasons']==[19] and replay['cases']==128
 assert sha(C/'data/ui/libs/Module.big')==build['source_sha256'] and sha(B/'Module.big')==build['module_sha256']
 assert not stage.exists();stage.mkdir()
 template=(R/'nostalgia_preflight.py').read_text('utf-8').replace('patches/nostalgia-installed.json',MANIFEST).replace('patches/nostalgia-receipt.json',RECEIPT).replace('patches/nostalgia_preflight.py',SELF).replace('INSTALLED_NOSTALGIA','INSTALLED_NOSTALGIA_NAME').replace('NOSTALGIA_PREFLIGHT_PASS','NOSTALGIA_NAME_PREFLIGHT_PASS')
 (stage/'nostalgia_name_preflight.py').write_text(template,'utf-8')
 closed();owned=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);token=str(os.getpid()).encode();os.write(fd,token);owned.append((path,fd,token))
  closed();parent=load(S/'patches/nostalgia_preflight.py','name_parent');parent.preflight(S,C);comp=parent.compose_manifest(S,C)
  play=(S/'play-local.bat').read_bytes();assert play.count(b'patches\\nostalgia_preflight.py')==1
  (stage/'play-local.bat').write_bytes(play.replace(b'patches\\nostalgia_preflight.py',b'patches\\nostalgia_name_preflight.py'))
  pairs=[(B/'Module.big',C/'data/ui/libs/Module.big'),(stage/'nostalgia_name_preflight.py',S/SELF),(stage/'play-local.bat',S/'play-local.bat')]
  guards={(r['root'],r['relative'].replace('\\','/').casefold()):dict(r) for r in comp['guards']}
  for source,target in pairs:
   root='server' if target.is_relative_to(S) else 'client';relative=target.relative_to(S if root=='server' else C).as_posix();guards[(root,relative.casefold())]=dict(root=root,relative=relative,sha256=sha(source))
  comp=copy.deepcopy(comp);comp['guards']=list(guards.values());comp['ancestry'].append(dict(layer='nostalgia_name',method=12,changed_seasons=[19],native_status='PENDING'))
  revision='nostalgia-name-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=S/'backups'/revision
  m=dict(schema=1,revision=revision,season=19,card_count=88,client=str(C),guards=list(guards.values()),composition=comp,state_shop_replaced=False,native_status='PENDING',scope='method12 season19 callback only')
  write(stage/'nostalgia-name-installed.json',m)
  receipt=dict(status='INSTALLED_NOSTALGIA_NAME',manifest_sha256=sha(stage/'nostalgia-name-installed.json'),revision=revision,backup=str(backup),state_shop_replaced=False,native_status='PENDING')
  write(stage/'nostalgia-name-receipt.json',receipt)
  assets=business();protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('shop.json','fifadb.sqlite','custom_rosters.json','pack_cadence.json','pack_catalogue.json','product_packs.json')}
  # Select the new gate only after all resources and metadata are on disk.
  ordered=pairs[:2]+[(stage/'nostalgia-name-installed.json',S/MANIFEST),(stage/'nostalgia-name-receipt.json',S/RECEIPT)]+pairs[2:]
  assert sha(C/'data/ui/libs/Module.big')==build['source_sha256'];parent.preflight(S,C);closed()
  def verify():
   assert all(sha(p)==h for p,h in protected.items()) and business()==assets
   load(S/SELF,'name_installed').preflight(S,C)
  transaction(ordered,backup,verify)
  result=dict(status='INSTALLED_NAME_CALLBACK_NATIVE_PENDING',revision=revision,backup=str(backup),preflight=load(S/SELF,'name_proof').preflight(S,C),files={n:sha(S/n) for n in (SELF,MANIFEST,RECEIPT)},module_sha256=sha(C/'data/ui/libs/Module.big'),all_other_module_methods_exact=True,callback_replay_cases=128,changed_seasons=[19],business_assets_unchanged=True,protected=protected,services_restarted=False,game_started=False,native_verified=False)
  write(O/'installed-result.json',result);print(json.dumps(result,ensure_ascii=True,indent=2))
 finally:
  for path,fd,token in reversed(owned):
   os.close(fd)
   if path.exists() and path.read_bytes()==token:path.unlink()
if __name__=='__main__':run()
