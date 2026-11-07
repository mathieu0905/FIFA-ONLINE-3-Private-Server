"""Publish local review artifacts, not game files or player assets."""
from pathlib import Path
import ast, hashlib, json, sqlite3, sys

ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
CANDIDATE = ROOT / 'candidates/bulk-seasons-v2'
SANDBOX = ROOT / 'private-servers/bulk-seasons-v2'
sys.dont_write_bytecode = True
sys.path.insert(0, 'D:/FO3QA/modern_player_integration_v2')
import native_peer_guard_v1 as guard


def read(p):
    return json.loads(p.read_text('utf-8'))


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


manifest = read(CANDIDATE / 'manifest.json')
runtime = read(SANDBOX / 'runtime-PASS.json')
resources = read(ROOT / 'bulk-seasons-v2-resources-PASS.json')
assert runtime['status'] == 'PASS_PRIVATE_BULK_RUNTIME_NATIVE_PENDING'
assert resources['registered_cards'] == runtime['registered_searchable'] == 504
registry = read(CANDIDATE / 'custom_rosters.json')
peers = guard.active_peers(WORK, Path('D:/FO3ID/32795'))
formal_db = Path('D:/FO3ID/server/gamedata/fifadb.sqlite')
with sqlite3.connect((CANDIDATE / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    db.execute('attach database ? as formal', (formal_db.as_uri() + '?mode=ro',))
    formal_count = db.execute('select count(*) from formal.players').fetchone()[0]
    incompatible = []
    for (table,) in db.execute("select name from formal.sqlite_master where type='table'").fetchall():
        if db.execute(f'select * from formal."{table}" except select * from main."{table}" limit 1').fetchone():
            incompatible.append(table)
    assert not incompatible, ('Current formal changes require a data rebase', incompatible)
current_registry = read(Path('D:/FO3ID/server/gamedata/custom_rosters.json'))
assert all(r in registry['cards'] for r in current_registry['cards'])
current_formal = dict(rows=formal_count, sha256=sha(formal_db), all_current_table_rows_preserved_in_candidate=True,
                      registry_entries=len(current_registry['cards']), net_remaining_cards=manifest['rows'] - formal_count)
native = dict(status='WAITING_PEER_OVERLAY_RESTORE' if peers else 'AWAITING_NATIVE_INSTALLATION_AND_ACCEPTANCE',
              active_peers=peers, client='D:/FO3ID/32795', candidate_manifest_sha256=sha(CANDIDATE / 'manifest.json'),
              installed=False, native_verified=False, match_verified=False, current_formal=current_formal,
              ui_delta=str(ROOT / 'ui/bulk-seasons-v1/manifest.json'),
              required=(['Restore the other chat native overlay before changing shared game resources'] if peers else []) + [
                        'Rebase Module/language on the final returned formal baseline and update startup preflight/receipts together',
                        'Use private backend and reversible client overlay for slot12/13/84 cards, near/far models and actual matches',
                        'Test acquisition, save/relogin and unchanged original manager/wallet/cards before formal release',
                        'Future BB4 price profile requires a separate contract; this batch validated the current formal profile only'])
write(ROOT / 'native-preflight.json', native)

meta = read(WORK / 'work/season_expansion/spid.json')
compatible = {x['playerid'] for x in read(WORK / 'work/season_expansion/model_compatible_icons.json')}
icon_backlog = [x | dict(playerid=x['id'] % 1000000, reason='FC ICON identity has no audited same-PID FO3 template/model') for x in meta if x['id'] // 1000000 == 101 and x['id'] % 1000000 not in compatible]
backlog = dict(modern=read(ROOT / 'bulk-sources/backlog.json'), icons=icon_backlog,
               note='No generic substitute or invented identity was added for these entries. Existing same-slot Messi/Ronaldo remain frozen.')
write(ROOT / '继续扩充待办.json', backlog)

tree = ast.parse((SANDBOX / 'http_config.py').read_text('utf-8'))
weights = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROLE_WEIGHTS' for t in n.targets))
roles = 'GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
positions = 'GK SW RWB RB RCB CB LCB LB LWB RDM CDM LDM RM RCM CM LCM LM RAM CAM LAM RF CF LF RW RS ST LS LW'.split()
catalog = []
with sqlite3.connect((CANDIDATE / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    for entry in registry['cards']:
        row = db.execute('select * from players where spid=?', (entry['fo3_spid'],)).fetchone()
        pos = row['preferredposition1']
        rating = sum(row[k] * n for k, n in weights[roles[pos]].items()) // 100 + 5
        catalog.append(dict(spid=row['spid'], playerid=row['playerid'], season=row['spid'] // 1000000,
                            name_zh=entry['name_zh'], name_en=entry.get('name_en'), position=positions[pos],
                            grade1_level1_no_teamcolour_ovr=rating, previously_installed=row['spid'] in (13020801, 13028130, 13158023)))
catalog.sort(key=lambda r: (r['season'], -r['grade1_level1_no_teamcolour_ovr'], r['spid']))
write(ROOT / '完整球员名单.json', catalog)
lines = ['FO3私服扩充候选：504张注册卡，其中501张新增，未正式安装',
         '评分口径：+1、1级、无队色，按FO3实际位置权重计算。',
         '12号：123张传奇；13号：255张新现役+原有3张；84号：123张传奇时刻。', '']
for sid, label in [(13, '现役及原有精选'), (12, '传奇精选'), (84, '传奇时刻')]:
    lines.append(f'{label}（{sum(r["season"] == sid for r in catalog)}张）')
    for row in catalog:
        if row['season'] == sid:
            lines.append(f'{row["spid"]}  {row["name_zh"]}  {row["position"]}  OVR {row["grade1_level1_no_teamcolour_ovr"]}' + ('  [原有卡]' if row['previously_installed'] else ''))
    lines.append('')
(ROOT / '完整球员名单.txt').write_text('\n'.join(lines) + '\n', 'utf-8')

report = '''FIFA ONLINE 3 私服：三批球员扩充
核对日期：2026-11-06

已构建（独立候选，未正式安装）
现役：255张新增；加原有梅西、C罗、小罗，共258张13号槽卡。
传奇精选：123张12号槽卡。
传奇时刻：123张84号槽卡。
合计净新增501张，注册扩展卡504张，数据库60177→60678行。
三批起点为24/12/4，本次在合并四十卡后又增加461张。

已执行验证
378份官方能力来源均成功保存，失败抓取已补齐；保留首次失败记录。
所有正式数据库表的既有行完整保留，原有已发行3卡未被替换。
服务端SQLite与客户端加密数据库一致，BIG目录271项有序，另270个成员相对姓名修复基线逐字节相同。
501张新增卡头像PNG通过解码校验；六种客户端姓名库覆盖全部504张卡的380个不同身份。
504张注册卡逐张通过真实复制后端的搜索与市场许可检查；引擎模板不会混入这些搜索结果。
全部504张卡+1..+20共10080组价格均为正整数、单调递增、未超过signed64。
123张传奇时刻在1/20/23级、28个位置共10332组真实后端评分比较中，新+1等于同人经典+9。
传奇时刻从NPC随机池、直接查询、遗留库存和伪造购买入口排除；保留玩家交易许可。
旧102卡包池和9抽奖配置不变；验证副本state/shop字节保持，检查未启动任何监听。
12/13/84中文赛季名已生成组合UI增量，只改姓名方法，保留其他方法与旧语言键。

未完成
另一个对话正在继续主版本修改与验收；本次没有启停其服务或修改正式数据库/存档。
组合UI基于当前测试资源，只是候选；待另一测试归还后必须按最终基线重建，不能直接覆盖安装。
原生卡面、近远景模型、实际比赛、买卡与重登仍未验收，不把协议或PNG检查当作实机通过。
当前价格验证只适用正式服现有规则，未来BB4/新经济配置必须另验。
255张现役沿用原0.75转换，传奇沿用0.75转换+3本地奖励，传奇时刻为同人最强原FO3模板33属性+15。
保留同人原FO3模型；已有24人候选中19个转换模型依赖保留，所有模型均仍需原生观察。
243个新现役身份及30个新ICON身份缺少已审核同PID模型/模板，单列继续扩充待办；另2个现役来源因原有同槽卡已发行而不覆盖。

交付位置
候选：D:\\fifaol3\\candidates\\bulk-seasons-v2
独立后端：D:\\fifaol3\\private-servers\\bulk-seasons-v2
完整名单：D:\\fifaol3\\完整球员名单.txt
来源快照：D:\\fifaol3\\bulk-sources\\sources.json
实际后端验证：D:\\fifaol3\\private-servers\\bulk-seasons-v2\\runtime-PASS.json
资源验证：D:\\fifaol3\\bulk-seasons-v2-resources-PASS.json
实机前置状态：D:\\fifaol3\\native-preflight.json
'''
(ROOT / '扩充报告.txt').write_text(report, 'utf-8')
fresh_note = f'\n最新主版本兼容复核：当前正式库{formal_count}行，候选仍完整保留其全部表行与注册条目；当前尚需导入{manifest["rows"] - formal_count}张。贝林汉姆已由另一对话加入主版本，因此原始净增501与当前待导入数量相差1，不重复发卡。当前客户端活动overlay数量：{len(peers)}。\n'
(ROOT / '扩充报告.txt').write_text(report + fresh_note, 'utf-8')
(ROOT / '新赛季跟进.txt').write_text(report + fresh_note, 'utf-8')
index = dict(status='501_NEW_CARDS_BUILT_PRIVATE_CHECKS_PASS_NATIVE_PENDING', candidate=str(CANDIDATE), sandbox=str(SANDBOX),
             counts={'new_modern': 255, 'icons': 123, 'moments': 123, 'existing': 3, 'net_new': 501, 'registered': 504},
             formal_installed=False, native_verified=False, match_verified=False, current_formal=current_formal,
             artifacts={str(p): sha(p) for p in [CANDIDATE / 'manifest.json', SANDBOX / 'runtime-PASS.json',
                                                ROOT / 'bulk-seasons-v2-resources-PASS.json', ROOT / 'native-preflight.json',
                                                ROOT / '完整球员名单.json', ROOT / '完整球员名单.txt', ROOT / '扩充报告.txt', ROOT / '继续扩充待办.json']})
write(ROOT / '交付索引.json', index)
print(json.dumps(dict(status=index['status'], counts=index['counts'], active_native_peers=len(peers))))
