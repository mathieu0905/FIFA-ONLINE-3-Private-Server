def sqlite_rows(path,sql):
 with closing(sqlite3.connect(path)) as db:return db.execute(sql).fetchall()

def protected_market(state):
 m=copy.deepcopy(state['market_simulation'])
 for key in ['fair_revision','fair_revision_history','identity_quotes','price_events','system_quote_price_revision','system_quote_repricing_receipts']:m.pop(key,None)
 def clean(row):
  row.pop('price',None);row.pop('_market_price_revision',None)
 for book in list(m.get('books',{}).values())+list(m.get('rare_books',{}).values()):
  for row in book.get('rows',[]):clean(row)
 for row in m.get('legacy_supply',[]):clean(row)
 for a in m.get('npc_exchange',{}).get('assets',{}).values():
  if isinstance(a.get('listing'),dict):clean(a['listing'])
 return m

def plan():
 report=read(P/'prepared.json');audit=read(P/'regression.json');assert audit['status']=='PASS' and read(P/'generation-regression.json')['status']=='PASS'
 for file,h in report['baseline'].items():assert sha(file)==h,'Fresh baseline changed '+file
 for file,h in report['outputs'].items():assert sha(P/file)==h,'Prepared artifact changed '+file
 assert sha(P/'system_quotes.py')==read(P/'generation-regression.json')['quote_source_sha256']
 play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\(\w+_preflight\.py)',play);parent_rel='patches/'+match[1].decode();assert parent_rel!=SELF
 parent=load(S/parent_rel,'v14_fresh_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C);validator=load(S/'patches/startup_market_preflight.py','v14_guard_validator');validator.verify_manifest(composition,S,C);guards=validator.table(composition['guards']);oldkeys=set(guards)
 source=(S/parent_rel).read_text('utf8')
 for a,b in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_GRADE_PRICE_V14'),(prior['status'],'GRADE_PRICE_V14_PREFLIGHT_PASS')]:source=source.replace(a,b)
 assert source.count('\n fair_value=verify_installed(')==1;source=source.replace('\n fair_value=verify_installed(','\n previous_fair_value=verify_installed(',1)
 i=source.index('\n return dict(',source.index('def preflight'))
 source=source[:i]+"\n fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v14-catalogue.json.gz',server/'gamedata/fair-value-v14-model.json',server/'gamedata/fifadb.sqlite')"+source[i:]
 source=source.replace('return dict(','return dict(previous_fair_value=previous_fair_value,',1)
 extra={('server','gamedata/fair-value-v14-model.json'),('server','gamedata/fair-value-v14-catalogue.json.gz')};i=source.index('\n if not required<=seen:');source=source[:i]+'\n required.update('+repr(extra)+')'+source[i:]
 revision='grade-price-v14-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 docs='\n\n2026-11-07 强化单卡价格 v14：v13全部+1基价和球员属性不变；强化价由+1乘独立倍率。采用现有成功率/失败规则/材料选择归一化成本，+1至+5保留原倍率，+5以上对数压缩，+20倍率5000，避免原生数值上限；这不是原始制造期望成本。强化成功率、能力增幅、用户资产、玩家订单、已成交记录不变。新代际保留历史和共同市场因子，系统旧报价按新参考价撤换重挂，数量/期限/NPC钱包和成本不变。纯临时数据校验、正式接口校验不等于实机比赛通过；游玩期间禁止停服。\n'
 payloads={('server','fair_value_store.py'):(P/'fair_value_store.py').read_bytes(),('server','npc_exchange.py'):(P/'npc_exchange.py').read_bytes(),('server','gamedata/fair-value-v14-model.json'):(P/'model.json').read_bytes(),('server','gamedata/fair-value-v14-catalogue.json.gz'):(P/'catalogue.json.gz').read_bytes(),('server','docs/工程经验与修改边界.txt'):(S/'docs/工程经验与修改边界.txt').read_bytes()+docs.encode('utf8'),('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(match[0],SELF.replace('/','\\').encode())}
 before={}
 for (root,rel),body in payloads.items():
  target=S/rel;key=(root,rel.casefold());before[(root,rel)]=target.read_bytes() if target.exists() else None
  if target.exists():assert key in guards and sha(target)==guards[key]['sha256'],'Target outside fresh guard '+rel
  else:assert key not in guards
  if rel.endswith('.py'):compile(body.decode('utf8'),rel,'exec')
  guards[key]=dict(root=root,relative=rel,sha256=hashlib.sha256(body).hexdigest())
 assert oldkeys<=set(guards)
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(x['root']==policy['root'] and x['relative'].casefold()==policy['relative'].casefold() for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
 composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='independent-enhancement-prices-v14',revision=revision,native_status='PENDING'));composition['active_fair_valuation']=dict(model_sha256=report['model_sha256'],profile_sha256=report['profile_sha256'],base_generation='nostalgia-utility-ep-v13',independent_enhancement=True,grade20_multiplier=5000)
 manifest=dict(schema=1,revision=revision,client=str(C),guards=composition['guards'],composition=composition,state_shop_replaced=False,parent=parent_rel,parent_sha256=sha(S/parent_rel),attributes_changed=False)
 for rel,body in [(MANIFEST,data(manifest)),(RECEIPT,data(dict(status='INSTALLED_GRADE_PRICE_V14',revision=revision,manifest_sha256=hashlib.sha256(data(manifest)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))]:assert not (S/rel).exists();payloads[('server',rel)]=body;before[('server',rel)]=None
 audit.update(rows=report['rows'],model_sha256=report['model_sha256'])
 return dict(payloads=payloads,before=before,revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),audit=audit,build=report)
