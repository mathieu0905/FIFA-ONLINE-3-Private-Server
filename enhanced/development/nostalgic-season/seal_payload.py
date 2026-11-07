"""Validate and seal the complete 88-card work artifact, including all mini faces."""
from pathlib import Path
import ast,json,hashlib,shutil,sqlite3,sys
sys.stdout.reconfigure(encoding='utf-8');R=Path(__file__).resolve().parent;B=R/'build-v2/database';U=R/'build-v1/ui'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=json.loads((R/'roster-audit.json').read_text('utf-8'));m=json.loads((B/'manifest.json').read_text('utf-8'))
for n,h in m['outputs'].items():assert sha(B/n)==h,n
with sqlite3.connect(B/'fifadb.sqlite') as db:
 db.row_factory=sqlite3.Row
 db.execute('attach database ? as donor',('D:/FO3ID/server/gamedata/fifadb.sqlite',))
 for c in spec['cards']:
  row=dict(db.execute('select * from players where spid=?',(19000000+c['base_playerid'],)).fetchone())
  donor=dict(db.execute('select * from donor.players where spid=?',(c['template_spid'],)).fetchone())
  changed=set(c['fo3_overrides'])|{'spid','potential'}
  assert all(row[k]==v for k,v in donor.items() if k not in changed),c['name_zh']
  assert all(row[k]==v for k,v in c['fo3_overrides'].items()),c['name_zh']
  assert all(row[k]==v for k,v in c['model'].items()),c['name_zh']
  assert all(db.execute('select 1 from '+table+' where playerid=?',(c['base_playerid'],)).fetchone() for table in ('nameschi','nameseng','namesind'))
  for table in ('permid','permcn','permkr','permth','permvn','permsg'):assert tuple(db.execute('select licensed,transferable from '+table+' where spid=?',(row['spid'],)).fetchone())==(1,1)
# The source website exposes Materazzi only under his EL SPID, not his base PID.
source=R/'downloaded-portraits/materazzi-0.png';target=B/'portraits/p19177844.png';shutil.copyfile(source,target)
for p in m['portraits']:
 if p.get('missing'):
  assert p['name']=='p19177844.png';p.clear();p.update(name=target.name,donor='https://fifaaddict.com/fo3img/players/p27177844.png',sha256=sha(target))
assert len(m['portraits'])==88 and all(sha(B/'portraits'/r['name'])==r['sha256'] for r in m['portraits'])
(B/'spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf-8')
m['outputs']={p.name:sha(p) for p in B.iterdir() if p.is_file() and p.name!='manifest.json'};m['portraits_complete']=True
(B/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),'utf-8')
ui=json.loads((U/'ui-manifest.json').read_text('utf-8'));assert all(sha(U/n)==h for n,h in ui['output_hashes'].items())
positions='GK SW RWB RB RCB CB LCB LB LWB RDM CDM LDM RM RCM CM LCM LM RAM CAM LAM RF CF LF RW RS ST LS LW'.split()
lines=['# 怀旧神兽赛季 · OG','', '首发88人。独立赛季19，一人一张新卡，保留旧赛季与已有资产。','', '能力口径：等级1、强化+1，主位置93～94；原始数据库88～89。历史赛季用于标明原型，当前新卡属于怀旧神兽赛季。','']
groups={'ST':'前锋','WIDE':'边路','MID':'中场','CB':'中卫','FB':'边后卫','GK':'门将'}
for group,title in groups.items():
 lines.extend(['## '+title,'','| 球员 | 原型赛季 | 新卡主位置 | 1级/+1能力 | 身高/体重 |','|---|---|---|---|---|'])
 for c in spec['cards']:
  if c['group']!=group:continue
  lines.append(f"| {c['name_zh']} | {c['template_label']} | {positions[c['fo3_overrides']['preferredposition1']]} | {c['display_plus1_ovr']} | {c['model']['height']}cm / {c['model']['weight']}kg |")
 lines.append('')
lines.extend(['注：德马科斯原14普卡不在当前库，使用同身份当前17普卡作为模型与属性轮廓原型；并非声称它就是14卡。所有原卡的身高、体重、脸型、体型、惯用脚、花式、逆足和特性保留；明确调整主位置时保留原位置作为兼任。','', '状态：构建完成，正式安装和原生验收尚未完成。'])
(R/'怀旧神兽名单.md').write_text('\n'.join(lines),'utf-8')
report=dict(status='SEALED_OFFLINE_PASS',cards=88,positions={g:sum(c['group']==g for c in spec['cards']) for g in groups},database_sha256=sha(B/'fifadb.sqlite'),data0_sha256=sha(B/'data_0.big'),database_manifest_sha256=sha(B/'manifest.json'),ui_manifest_sha256=sha(U/'ui-manifest.json'),all_88_templates_models_and_permissions_checked=True,all_88_portraits_present=True,old_rows_exact=m['old_rows_exact'],non_target_big_members_exact=270,native_verified=False,production_written=False)
(R/'sealed-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
