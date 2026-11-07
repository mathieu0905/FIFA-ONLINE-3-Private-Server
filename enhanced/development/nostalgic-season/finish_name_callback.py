from pathlib import Path
import json,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parent));from install_season import R,S,C,read,write,load,sha
result=read(R/'name-callback/installed-result.json');proof=load(S/'patches/nostalgia_name_preflight.py','name_final').preflight(S,C)
doc=S/'docs/工程经验与修改边界.txt';old=doc.read_bytes();backup=Path(result['backup'])/'engineering-before.txt';shutil.copyfile(doc,backup)
extra='''

FO3-NOSTALGIA-019 名称回调补齐（2026-11-06 20:16，nostalgia-name-20261106-201608）
88卡安装后复核发现PlayerListUtil.method12的默认回调仍以数字拼赛季名，新增19即使method14已有中文也会漏到该路径。另一赛季名owner明确继续暂停且不写Module，本怀旧聊天在独立人类安装任务内只补19，不抢其12/13/84待处理范围。
基于实际25a5669... Module仅method12 offset111插入40字节，19调用已有getSeasonString14；method14新19和所有其它方法records/常量池、其它SWF tag与BIG成员压缩字节保持。实际128季字节码有界回放只有19从数字名变“怀旧神兽 测试球员”，其它127季相同、栈不超过原max_stack。静态代码缺漏确认，不冒称用户在某具体原生页面的根因或实机已通过。
游戏实际已退出，共同双锁和最新nostalgia1379物理门槛通过后，5文件事务（Module、新helper/manifest/receipt、最后play）直接安装；新top nostalgia_name_preflight.py1382PASS，compose_manifest(server=None,client=None)完整dict无_compose。Module SHA1b9519f979ae58ac11a0d5442b726be1e36919b3f8018a1a313c05c7ba0a8016。三元组：helper4071e53aaab431e533151cbfd88e58d8d971fea8da667b9afe69ef84520dca63，manifest a15b686c802cae410e6fda472af1961c604e4250d5a0dd1c3419d980d5af95f6，receipt54b923e2f387215236a38143f2bd84f70117e39412584a0f6afb1afd06b865e0。备份server/backups/nostalgia-name-20261106-201608。
DB/registry/shop/3旧概率配置完全不变，全部非market业务指纹保持；此次无服务启停、无游戏启动或CUA，PID仍93772/33544。新画面与比赛仍未验证。证据nostalgic-season/name-callback/callback-v1/build.json、replay.json及name-callback/installed-result.json。后续12/13/84修复必须继承当前method12的19分支，不能用dd0/25a或旧callback全方法覆盖。
'''
assert doc.read_bytes()==old;doc.write_bytes(old+extra.encode('utf-8'))
handoff=read(R/'installed-handback.json');handoff.update(top='patches/nostalgia_name_preflight.py',revision=result['revision'],preflight=proof,module_sha256=result['module_sha256'],files={**result['files'],'play-local.bat':sha(S/'play-local.bat')},name_callback_checked=True,name_callback_native_verified=False)
write(R/'installed-handback.json',handoff);print(json.dumps(dict(status='NAME_FIX_HANDED_BACK',preflight=proof),ensure_ascii=True))
