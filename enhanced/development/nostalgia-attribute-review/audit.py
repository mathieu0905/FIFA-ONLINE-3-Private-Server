"""Trace nostalgia source attributes and distinguish valuation proxy from playability."""
from pathlib import Path
from contextlib import closing
import datetime,hashlib,json,sqlite3,sys
S=Path('D:/FO3ID/server');W=Path('D:/fifaol3');P=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
import fair_value_model as model
def read(p):return json.loads(Path(p).read_text('utf8'))
def digest(r):return hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 spec=read(W/'nostalgic-season/roster-audit.json');later=read(W/'pack_limits/nostalgia-stats2/build-results.json');changes={r['spid']:r for r in later['changes']};cfg=read(S/'gamedata/fair-value-v12-model.json')
 receipt=read(S/'patches/nostalgia-receipt.json');backup=Path(receipt['backup']);journal=read(backup/'transaction.json');entry=next(e for e in journal['entries'] if Path(e['target'])==S/'gamedata/fifadb.sqlite');sourcefile=backup/entry['backup'];assert hashlib.sha256(sourcefile.read_bytes()).hexdigest()==entry['before']
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split();rows=[];source_mismatches=[]
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db,closing(sqlite3.connect(sourcefile.as_uri()+'?mode=ro',uri=True)) as original_db:
  db.row_factory=sqlite3.Row;original_db.row_factory=sqlite3.Row
  for card in spec['cards']:
   sid=19000000+card['base_playerid'];r=dict(db.execute('select * from players where spid=?',(sid,)).fetchone());original=dict(original_db.execute('select * from players where spid=?',(card['template_spid'],)).fetchone());assert r==changes[sid]['after']
   source_digest=digest(original)
   if source_digest!=card['source_row_sha256']:source_mismatches.append(sid)
   w=cfg['role_weights'][roles[r['preferredposition1']]];rating=lambda v:sum(v[k]*a for k,a in w.items())//sum(w.values())+5;e=model.explain(r,cfg);fields=model.fields(cfg)
   preserved=['playerid','height','weight','bodytypecode','headtypecode','headclasscode','trait1','trait2','runningcode1','finishingcode1','weakfootabilitytypecode','skillmoves']
   rows.append(dict(spid=sid,name=card['name_zh'],source_spid=card['template_spid'],source_season=card['template_label'],source_grade1_ability=rating(original),current_grade1_ability=rating(r),initial_manual_target=card['target_ovr'],initial_shift=card['stat_lift'],later_plus2=True,field_increases={k:r[k]-original[k] for k in fields},proxy_valuation_score=e['effective_score'],proxy_best_role=e['best_role'],identity_factor=e['identity_factor'],current_fair_price=e['fair_price_ep'],height=r['height'],weight=r['weight'],bodytypecode=r['bodytypecode'],trait1=r['trait1'],trait2=r['trait2'],native_identity_model_and_trait_fields_preserved=all(r[k]==original[k] for k in preserved),source_row_sha256=source_digest))
 selected=[next(x for x in rows if x['name']==name) for name in ['罗霍','费莱尼','博格巴','贝尔']]
 result=dict(status='AUDIT_CONFIRMED_GENERATION_AND_VALUATION_DESIGN_ISSUES',at=datetime.datetime.now().astimezone().isoformat(),cards=88,all_current_rows_match_generated_plus2_artifact=True,source_rows_all_match_original_digests=not source_mismatches,source_mismatches=source_mismatches,source_backup=dict(path=str(sourcefile),sha256=entry['before']),identity_body_traits_preserved=all(r['native_identity_model_and_trait_fields_preserved'] for r in rows),manual_higher_target_names=[r['name'] for r in rows if r['initial_manual_target']==89],selected=selected,rows=rows,problems=['Manual89 vs88 target mistakes nostalgia reputation for higher visible OVR','Per-player uniform shifts compress source OVR hierarchy and inflate unrelated abilities','Later all33stats+2 also modifies non-role GK/outfield fields','v12 effective score is role-weight maximum plus stars, not measured playability; body/traits/animations are not modeled','No current native match evidence quantifies model bonuses'],formal_written=False,game_GUI=False,price_changed=False)
 (P/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
 lines=['怀旧神兽属性与实用性审计（只读）',result['at'],'88张均精确匹配旧生成产物，异常来自设计规则，不是后来随机损坏。',f"原型摘要全部匹配：{result['source_rows_all_match_original_digests']}；原生身份/身体/动作/特性保留：{result['identity_body_traits_preserved']}。",'原初部分名单目标89、其余88；之后全体+2，现基础90/91，对应1级+1展示95/96。','估值字段有效能力分仅指岗位加权与星级，不是实测实用性。','','球员｜原型｜原型1级+1｜怀旧1级+1｜速度加点｜当前估值分｜身高体重｜身份因子']
 for r in selected:lines.append(f"{r['name']}｜{r['source_season']}｜{r['source_grade1_ability']}｜{r['current_grade1_ability']}｜+{r['field_increases']['sprintspeed']}｜{r['proxy_valuation_score']:.2f}｜{r['height']}cm/{r['weight']}kg｜{r['identity_factor']:.3f}")
 lines+=['','后续应先核实真实原型属性及卡型，保留强项和短板，停止按神兽名单统一抬总评。实用性按对抗/制空/回追/转身/进攻等岗位维度解释；模型、特性和动作权重需要对应引擎证据或受控实测，不按大个子/名气随意加分。','任何正式属性修正必须同步重建v12估值目录，player_import完整校验，并保留当前真实资产与其它聊天改动。','本次未修改正式属性、模型、价格、存档、服务或GUI。']
 (P/'审计结论.txt').write_text('\n'.join(lines)+'\n','utf8');print(json.dumps({k:result[k] for k in ['cards','source_rows_all_match_original_digests','source_mismatches','identity_body_traits_preserved','selected']},ensure_ascii=False))
if __name__=='__main__':main()
