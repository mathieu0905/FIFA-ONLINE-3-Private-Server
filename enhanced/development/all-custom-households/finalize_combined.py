"""Record the observed final installation; no gameplay or formal file writes."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def read(path):return json.loads(Path(path).read_text('utf8'))
def body(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def sha(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
 combined=read(R/'combined-installed-handback.json');assert combined['status']=='COMBINED_INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING'
 h=combined['households'];u=combined['ucl25'];play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play);assert len(matches)==1;actual='patches/'+matches[0].decode()
 expected=Path(h['top_preflight']);assert (S/actual).resolve()==expected.resolve(),'Later launcher changed; inspect without rollback'
 triad=[Path(h[k]) for k in ('top_preflight','top_manifest','top_receipt')]
 for path in triad:assert sha(path)==h['files'][str(path)],path
 hot=json.loads(subprocess.check_output([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'hot_update_control.py')],cwd=S,creationflags=subprocess.CREATE_NO_WINDOW));assert hot['revision']==u['hot_update_status']['revision'] and hot['watcher_running'] and hot['error'] is None
 final=dict(status='COMBINED_INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',ucl_cards=u['cards_imported'],ucl_multiplier=u['multiplier'],existing_identities_reused=len(read(R.parent/'ucl25-import/identity-reuse.json')['rows']),genuinely_new_native=u['new_native'],households=h['coverage'],actual_preflight=str(expected),actual_manifest=h['top_manifest'],actual_receipt=h['top_receipt'],actual_triad_sha256={str(p):sha(p) for p in triad},actual_play_sha256=sha(S/'play-local.bat'),composition_api='compose_manifest(server=None,client=None)',services_restored=h['services_restored'] and u['services_restored'],services_restarted_once=combined['services_restarted_once'],service_restart_count=combined.get('service_restart_count',1),hot_update_status=hot,real_state_shop_replaced=False,stopped_snapshots_preserved=h['assets_identical_while_stopped'] and u['assets_identical_while_stopped'],GUI_used=False,native_game_verified=False,match_verified=False,full_career_review_complete=False,evidence=str(R/'combined-installed-handback.json'),observed_at=datetime.datetime.now().astimezone().isoformat())
 (R/'final-install-verification.json').write_bytes(body(final));(R/'work-status.json').write_bytes(body(final))
 root=R.parent/'root-current-top.json';previous=root.read_bytes();without_lock=dict(h);without_lock.pop('locks_released',None)
 if previous in (body(h),body(without_lock)):
  enriched=dict(h,combined_25ucl=dict(cards=u['cards_imported'],multiplier=u['multiplier'],existing_identities_reused=121,new_native=u['new_native'],handback=u['handoff']),combined_handback=str(R/'combined-installed-handback.json'))
  if root.read_bytes()==previous:
   temporary=root.with_suffix('.combined.tmp');temporary.write_bytes(body(enriched));temporary.replace(root)
 log=R/'WORKLOG.md';old=log.read_text('utf8');header='''# 最新正式安装结果

25UCL 与已核实户口更新均已生效。首个户口事务因读取 SQLite 的句柄未释放，在写入任何户口文件前回退；收集已结束读取的连接后重试成功。实际共恢复服务两次。详细实际入口、三元组 SHA 和验证范围见 `final-install-verification.json` / `combined-installed-handback.json`。

25UCL 360 张，0.72 倍率；121 人复用已有身份与外观，87 人新建登记的通用脸型身份。保留姆巴佩删除。新增赛季履历开关和已核实俱乐部户口已装；中国明日之星 32 张当前球队统一名称。未核实资料/小俱乐部仍待补，不宣称全部补齐。真实 state/shop 没有替换，停服快照在两个提交阶段均逐字节保持。GUI、首页、带球和比赛验收仍未进行。

以下为此前阶段的历史工作记录，不代表当前仍延期。

'''
 if not old.startswith('# 最新正式安装结果'):log.write_text(header+old,encoding='utf8')
 print(json.dumps({k:final[k] for k in ('status','ucl_cards','ucl_multiplier','existing_identities_reused','genuinely_new_native','services_restored','services_restarted_once','stopped_snapshots_preserved')},ensure_ascii=True))
if __name__=='__main__':main()
