"""Fresh guarded publication plan; no mutation or service action here."""
from pathlib import Path
import datetime,gzip,json,re
import prepare as p
def build_plan(h,*,read_only_preview=False):
 # This function only reads files and creates in-memory payloads. Preview is
 # allowed during gameplay; the real installer always uses the guarded default.
 if not read_only_preview:h.assert_idle()
 R,S,C,B=h.R,h.S,h.C,h.BUILD
 baseline=p.source.read(B/'baseline.json')
 for file,expected in baseline.items():
  if p.sha(file)!=expected:raise RuntimeError('Fresh build baseline changed; rebuild: '+file)
 result=p.source.read(B/'build-result.json');tests=p.source.read(R/'tests.json');coverage=p.source.read(B/'coverage-report.json');data=p.source.read(B/'plan.json')
 if result['status']!='BUILT_FOR_DIRECT_INSTALL' or not result['verified_subset'] or data['status']!='READY_VERIFIED_SUBSET_SOURCE_REVIEW_REMAINS':raise RuntimeError('Not a verified-subset direct build')
 if tests['status']!='PASS' or tests['database_sha256']!=result['database_sha256']:raise RuntimeError('Actual build regression missing')
 certificate=p.source.read(B/'player-import-validation.json')
 if certificate['status']!='PLAYER_IMPORT_FULL_PASS' or certificate['input_hashes']['database']!=result['database_sha256'] or certificate['input_hashes']['archive0']!=result['big_sha256']:raise RuntimeError('Full certificate drift')
 for file,expected in data['source_record_hashes'].items():
  if p.sha(file)!=expected:raise RuntimeError('Verified source changed: '+file)
 payloads=[]
 for entry in p.source.read(B/'payloads.json'):
  source=Path(entry['source'])
  if p.sha(source)!=entry['sha256']:raise RuntimeError('Payload drift')
  payloads.append((entry['root'],entry['relative'],source))
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
 if len(matches)!=1:raise RuntimeError('Ambiguous actual launcher')
 parent_rel='patches/'+matches[0].decode();parent=p.load(S/parent_rel,'verified_household_actual_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
 verifier=p.load(S/'patches/startup_market_preflight.py','verified_household_manifest_verifier');verifier.verify_manifest(composition,S,C)
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in composition['guards']}
 assert len(guards)==len(composition['guards'])
 old_receipt=p.source.read(S/parent.RECEIPT);helper=(S/parent_rel).read_text('utf8')
 for old,new in [(parent.MANIFEST,h.MANIFEST),(parent.RECEIPT,h.RECEIPT),(parent.SELF,h.SELF),(old_receipt['status'],'INSTALLED_CUSTOM_HOUSEHOLDS_VERIFIED'),(prior['status'],'CUSTOM_HOUSEHOLDS_VERIFIED_PREFLIGHT_PASS')]:
  if old not in helper:raise RuntimeError('Fresh parent helper contract differs: '+old)
  helper=helper.replace(old,new)
 compile(helper,h.SELF,'exec')
 revision='custom-households-verified-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');marker='FO3-CUSTOM-HOUSEHOLDS-VERIFIED-20261107-V1'
 doc=(S/h.DOC).read_bytes()
 if marker in doc.decode('utf-8-sig'):raise RuntimeError('Already installed')
 entry=('\r\n\r\n'+marker+'\r\n'
  f'用户明确安装已核实部分：{coverage["registered_cards"]}张当前注册新增卡、{coverage["identities"]}个身份；打开{coverage["enabled_history_cards"]}张原生履历开关，32张中国明日之星当前球队统一999327/中国明日之星。历史真实球队保留。\r\n'
  f'本批{coverage["changed_players"]}人新增{coverage["new_player_club_eligibilities"]}组已核实俱乐部资格（含租借、俱乐部青训），只追加新户口，原{coverage["rows_before"]}行完整保留。明确身份及已安装/官方EA球队ID才加入；不靠加入年对齐自动认定新球队，不创建猜测的小俱乐部ID。\r\n'
  f'仍有{coverage["pending_identities"]}个身份资料、{coverage["unmapped_clubs"]}个未匹配俱乐部名待核；本次不宣称全部补齐。未知日期保留未知；国家队/纯校队/足协训练中心不当俱乐部；能力、星数、位置、模型选择器、估值属性指纹不变。保留最新姆巴佩删除及所有并发合法修改。\r\n'
  '双端数据库与六语言team/TEAMNAMES校验、非目标BIG成员压缩字节保留、player_import完整验证、生产套装逻辑临时数据回归；不改现行套装数值、价格、概率、热包路由或资产。共同双锁、fresh全部guards/receipt policies、备份/CAS、保护停服和本次实时资产快照；游戏运行即延后。未知日期实机显示、首页和比赛尚未验收，不将结构/接口通过写成实机通过。\r\n'
  f'证据D:/fifaol3/all-custom-households/；正式证据{h.EVIDENCE}。\r\n')
 evidence=gzip.compress(h.encoded(dict(coverage=coverage,plan=data,tests=tests,layout=p.source.read(B/'layout.json'),tooling={name:p.sha(R/name) for name in ('prepare.py','install_builder.py','install_tests.py','install.py','install_plan.py','club_aliases.json')})),mtime=0)
 payloads.extend([('server',h.DOC,doc+entry.encode('utf8')),('server',h.EVIDENCE,evidence),('server',h.SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),h.SELF.replace('/','\\').encode()))])
 for root,rel,source in payloads:
  target=(S if root=='server' else C)/rel;key=(root,rel.replace('\\','/').casefold())
  if key in guards and h.current_hash(target)!=guards[key]['sha256']:raise RuntimeError('Fresh parent target differs: '+rel)
  if rel in (h.SELF,h.EVIDENCE) and target.exists():raise RuntimeError('Immutable path exists')
  guards[key]=dict(root=root,relative=rel,sha256=p.sha(source) if isinstance(source,Path) else h.digest(source))
 policies=list(composition.get('receipt_policies',[]))
 if not any(x['root']=='server' and x['relative']==parent.RECEIPT for x in policies):policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'}))
 composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False);composition.setdefault('ancestry',[]).append(dict(layer='custom-households-verified-subset',revision=revision,native_status='PENDING'))
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parent_rel,parent_preflight_sha256=p.sha(S/parent_rel),coverage=coverage,evidence=h.EVIDENCE,native_status='PENDING',full_career_review_complete=False)
 body=h.encoded(manifest);payloads.extend([('server',h.MANIFEST,body),('server',h.RECEIPT,h.encoded(dict(status='INSTALLED_CUSTOM_HOUSEHOLDS_VERIFIED',revision=revision,manifest_sha256=h.digest(body),state_shop_replaced=False,native_status='PENDING')))])
 entries=[]
 for root,rel,source in payloads:
  target=(S if root=='server' else C)/rel
  if rel in (h.MANIFEST,h.RECEIPT) and target.exists():raise RuntimeError('Immutable metadata exists')
  entries.append(dict(root=root,relative=rel,target=target,source=source,before=h.current_hash(target),after=p.sha(source) if isinstance(source,Path) else h.digest(source)))
 entries.sort(key=lambda x:x['relative']=='play-local.bat')
 return dict(revision=revision,parent=parent_rel,parent_hash=p.sha(S/parent_rel),entries=entries,prior=prior,coverage=coverage)
