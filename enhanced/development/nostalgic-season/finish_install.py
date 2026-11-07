from pathlib import Path
import datetime,hashlib,json,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parent));from install_season import load,sha,read,write,S,C,R
proof=load(S/'patches/nostalgia_preflight.py','nostalgia_final').preflight(S,C)
assert read(R/'live-result.json')['status']=='LIVE_READ_ONLY_PASS'
doc=S/'docs/工程经验与修改边界.txt';before=doc.read_bytes();backup=S/'backups/nostalgia-20261106-200540/engineering-before.txt';shutil.copyfile(doc,backup)
entry='''

FO3-NOSTALGIA-019（2026-11-06，nostalgia-20261106-200540，正式安装，native待验证）
人类明确“安装吧”，主协调分配唯一正式writer及一次受管服务重启。游戏实际已退出；按.shop-release.lock→.fo3-publish.lock执行源freshcheck、备份及文件事务，无游戏启动或Computer Use。父层exp_batch1199物理PASS，保留新EXP2555、恢复空格popupc580、Module经验30/金额/筛选及Label84/金额等既有修改，历史manifest/receipt不改。
正式新增独立19“怀旧神兽”88卡，60678→60766；14ST/16边路/20MID/16CB/16FB/6GK。各卡沿用准确FO3身份/原型模型、身体、特性及惯用脚等，仅能力按主位置升至原始88..89（1级/+1为93..94），指定主位置保留原位兼任；原WB博格巴手改与全部旧行保留。六许可表各新增88行，所有其它表无增删。新双端DB解密回读一致，data0目录有序，270非DB成员原压缩字节完全一致。
新增中文key FC_CUSTOM_SEASON_19，static_roster/registry追加19，88张赛季头像及双缓存。Module只改PlayerListUtil.getSeasonString/method14，其它方法原字节保留；Label两尺寸OG矢量季标各追加19season末帧，旧帧/ABC保持；PlayerInfoNew卡背景追加19season末帧，复用UL显示列表，原ABC/旧帧保持。server补丁源与client同步，避免启动安装器覆回旧Label/PlayerInfo。
安装191payload及新manifest/receipt，完整1379物理guard PASS，compose_manifest(server=None,client=None)可继续组合，无_compose。备份server/backups/nostalgia-20261106-200540。新top nostalgia_preflight.py SHA5cdbb7bc9d2bfb3b1b63fbd3a8205a619dcf93fd27c7d81e11c6c731f85c77b3，manifest99ee9eb8453add8a37bc34efc42ada157c2567ce9257a80e7ff791bed834faf0，receipt1673807ff74bd418395a2709674f1c1d32bc126401b0fc226891f01e836f2dfa。
验证：真实443/8088新PID93772、28002新PID33544；8088全库60766、19季88行分页集合、7核心详情精确字段、registry/static_roster与88张CDN头像均PASS；正式就绪提示版本检查通过。停服事务期间state/shop及3概率配置SHA完全保持；重启后排除市场自然推进的全部业务顶层指纹与安装前相等，shop字节保持，不回写快照、不创建或赠送测试卡。
冻结池：执行生产源的cadence/catalogue/product适配函数，102legacy/14cadence/54catalogue/56product共226已发行item球员/强化权重保持，19卡未混入旧池；这是离线函数证据，不冒充真实开包验收。194临时文件晚期191/最终校验失败回退与完整安装测试PASS，测试仅一次性文件。先前prepare遇到其它合法writer的http_config中间态失配按预期拒绝，无正式修改；新父完整通过后才重建release-v2。
能力、结构、HTTP和静态资源通过，不等于GFx实际显示或比赛通过。人类停止Computer Use约束仍有效，本次未自动启动或操作游戏，19徽标/背景/原经理启动/比赛加载均待实机。当前没有专属新售怀旧连锁，追加链需求交统一商城owner新SKU实现，不改变已售旧池或库存权益。
证据D:/fifaol3/nostalgic-season/sealed-result.json、contracts-result.json、transaction-result.json、release-v2/installed-result.json、live-result.json；复验正式.venv/Scripts/python.exe -B patches/nostalgia_preflight.py，工作verify_live.py及verify_contracts.py。新卡一旦进入真实资产，不得盲目卸载DB或恢复旧state/shop；先核对资产依赖再迁移。
'''
assert doc.read_bytes()==before;doc.write_bytes(before+entry.encode('utf-8'))
assert load(S/'patches/nostalgia_preflight.py','nostalgia_final_after_doc').preflight(S,C)['files']==1379
handoff=dict(status='INSTALLED_PROTOCOL_PASS_NATIVE_PENDING',revision=proof['revision'],season=19,cards=88,top='patches/nostalgia_preflight.py',api='preflight(server=None,client=None); compose_manifest(server=None,client=None) -> dict; no _compose',files={n:sha(S/n) for n in ('patches/nostalgia_preflight.py','patches/nostalgia-installed.json','patches/nostalgia-receipt.json','play-local.bat')},services={'https443_admin8088':93772,'messenger28002':33544},preflight=proof,business_assets_unchanged=True,shop_and_probability_files_unchanged=True,game_started=False,computer_use=False,native_verified=False,match_verified=False,backup=str(backup.parent))
write(R/'installed-handback.json',handoff)
roster=R/'怀旧神兽名单.md';text=roster.read_text('utf-8');text=text.replace('状态：构建完成，正式安装和原生验收尚未完成。','状态：已安装正式双端版本，8088/协议与静态资源验证通过；原生画面及比赛尚未验证。');roster.write_text(text,'utf-8')
print(json.dumps(handoff,ensure_ascii=True,indent=2))
