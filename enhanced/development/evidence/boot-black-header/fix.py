from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,struct,sys,zlib
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
sys.path[:0]=[str(W/'manutd-legends'),str(W/'season-display'),str(S/'tools/re')]
import bigdir as big,build_moments_display as gfx
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
tx=load(W/'manutd-legends/install.py','tx_boot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def write(p,v):p.write_bytes(body(v))
SELF='patches/boot_header_preflight.py';MANIFEST='patches/boot-header-installed.json';RECEIPT='patches/boot-header-receipt.json'
def build():
 source=C/'data/ui/components/Label.big';baseline=sha(source)
 member=next(n for n,*_ in big.entries(source) if n.endswith('.gfx'));compressed=big.read(source,member)
 plain=b'FWS'+compressed[3:8]+zlib.decompress(compressed[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
 tags=list(gfx.tags(plain,start));assert [(k,struct.unpack_from('<H',p)[0]) for k,p,_ in tags[:2]]==[(2,65018),(2,65019)]
 assert tags[2][0]==1000 and tags[3][0]==1009 and tags[4][0]==69
 original=tags[2:];index=next(i for i,(k,p,_) in enumerate(original) if k in (2,22,32,39,83))
 reordered=original[:index]+tags[:2]+original[index:]
 fixed=bytearray(plain[:start]+b''.join(raw for _,_,raw in reordered));assert len(fixed)==len(plain)
 assert sorted(raw for _,_,raw in tags)==sorted(raw for _,_,raw in reordered)
 assert b''.join(raw for _,_,raw in reordered if not (len(raw)>0 and raw in [tags[0][2],tags[1][2]]))==b''.join(raw for _,_,raw in original)
 out=R/'Label.big';gfx.replace_ui_member(source,out,member,b'CFX'+fixed[3:8]+zlib.compress(fixed[8:],9),big)
 reread=big.read(out,member);assert zlib.decompress(reread[8:])==fixed[8:]
 backup=S/'backups/wonderkid-20261107-024750-790336-attempt-024807-525795/0011.before'
 known=big.read(backup,member);prior=b'FWS'+known[3:8]+zlib.decompress(known[8:]);prior_start=8+(5+4*(prior[8]>>3)+7)//8+4
 prior_tags=list(gfx.tags(prior,prior_start));assert [k for k,_,_ in prior_tags[:9]]==[k for k,_,_ in reordered[:9]]
 report=dict(status='STATIC_PASS_NATIVE_PENDING',baseline=baseline,payload_sha256=sha(out),before_first_tags=[k for k,_,_ in tags[:9]],after_first_tags=[k for k,_,_ in reordered[:9]],known_working_first_tags=[k for k,_,_ in prior_tags[:9]],all_tag_bytes_preserved=True,only_tag_order_changed=True,shape_ids_preserved=[65018,65019],native_verified=False)
 write(R/'build.json',report);return report
def main():
 b=build()
 if '--build' in sys.argv:print(json.dumps(b));return
 held=[]
 try:
  for name in ('.shop-release.lock','.fo3-publish.lock'):
   p=S/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|os.O_BINARY);token=body(dict(task='boot-header-fix',pid=os.getpid()));held.append((p,fd,token));os.write(fd,token);os.fsync(fd)
  coord=json.loads((W/'coordination-current.json').read_text('utf8'));assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
  tx.closed();assert sha(C/'data/ui/components/Label.big')==b['baseline']
  play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
  parent_rel=matches[0].decode().replace('\\','/');parent=load(S/parent_rel,'boot_parent');prior=parent.preflight(S,C)
  comp=copy.deepcopy(parent.compose_manifest(S,C));table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
  receipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
  helper=(S/parent_rel).read_text('utf8').replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF).replace(receipt['status'],'INSTALLED_BOOT_HEADER').replace(prior['status'],'BOOT_HEADER_PREFLIGHT_PASS');compile(helper,SELF,'exec')
  ledger=S/'docs/工程经验与修改边界.txt'
  note='\r\nFO3-BOOT-HEADER-001（2026-11-07）：用户02:58启动后选经理前黑屏，HTTP仅locale/_timestamp/language_chi，无经理握手；02:50同样样本早于02:58:54只读启动器修改。确认wonderkid Label把新DefineShape(65018/65019)置于GFx ExporterInfo1000/ExternalImage1009/FileAttributes69之前，改变已运行版本头顺序。本层只将这两个完整tag原字节移至头/脚本元数据之后、原第一个图形定义之前；全部tag字节多重集、两个徽章、144/735新增18season帧和其它资源保持，不回退整个Label、不动Module/语言/球员/DB/state/shop。双份Label同步，完整继承实际最新父层guards及receipt policies。无服务重启/GUI/自动游戏启动。静态格式顺序修复确认，黑屏根因仍为推断，须人类重新启动验证；不能写成实机或比赛通过。证据D:/fifaol3/evidence/boot-black-header/{build.json,installed-handback.json}，回归fix.py --build，正式patches/boot_header_preflight.py。\r\n'
  payload=[('client','data/ui/components/Label.big',(R/'Label.big').read_bytes()),('server','patches/Label.big',(R/'Label.big').read_bytes()),('server',SELF,helper.encode()),('server','docs/工程经验与修改边界.txt',ledger.read_bytes()+note.encode()),('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))]
  entries=[]
  for root,rel,data in payload:
   target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=(root,rel.casefold())
   if key in table:assert table[key]['sha256']==before,('Changed baseline',rel)
   else:assert before is None,('Existing unregistered target',rel)
   table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=data,before=before,after=after))
  comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='boot-header',native_status='PENDING'))
  policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'})
  if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
  rev='boot-header-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=S/'backups'/rev
  mb=body(dict(schema=1,revision=rev,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel))
  rb=body(dict(status='INSTALLED_BOOT_HEADER',revision=rev,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
  for rel,data in ((MANIFEST,mb),(RECEIPT,rb)):
   assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=data,before=None,after=hashlib.sha256(data).hexdigest()))
  entries.sort(key=lambda e:e['relative']=='play-local.bat');tx.closed()
  tx.commit(entries,backup,lambda:load(S/SELF,'boot_installed').preflight(S,C))
  result=dict(status='INSTALLED_BOOT_HEADER_NATIVE_PENDING',backup=str(backup),preflight=load(S/SELF,'boot_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_available=True,function_signatures=dict(preflight='server=None, client=None',compose_manifest='server=None, client=None'),files={str(p):sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',C/'data/ui/components/Label.big',S/'patches/Label.big')},state_shop_written=False,services_action='No restart',native_verified=False,match_verified=False,observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
  write(R/'installed-handback.json',result);tx.atomic(body(result),W/'root-current-top.json');print(json.dumps(result))
 finally:
  for p,fd,token in reversed(held):
   os.close(fd)
   if p.exists() and p.read_bytes()==token:p.unlink()
if __name__=='__main__':main()
