from pathlib import Path
import hashlib,json
R=Path(__file__).parent;S=Path('D:/FO3ID/server');W=Path('D:/fifaol3')
policy='''
## 游戏期间安装不得打断游玩（用户长期约定，2026-11-07）

- 游戏运行期间，功能开发、只读分析、构建和临时数据回归可继续；不得要求用户为后台安装退出游戏，不得自动退出客户端、停止/重启服务或断开当前会话。此规则优先于旧的“必要重启默认授权”，用户针对某次中断另行明确授权时才例外。
- 只有经确认支持在线读取/事务热保存且兼容当前运行进程的服务端配置或功能，才可在游戏期间正式生效；不得把写入磁盘的Python代码称为已热加载。不得对整个HTTP/messenger模块盲目importlib.reload，不能以短暂断线当作无影响。
- 需要重启服务、变更协议/数据库结构，或替换客户端BIG/模型/语言资源的更新，在游戏运行期间延后正式提交与激活；继续完成可独立工作的开发和验证。等用户自行结束游玩后，fresh当前版本、共同锁、最新资产快照与备份/CAS再安装；不建第二套服务，不固定旧基线，不把延后称为已生效。
- 安装器须在任何正式写入及停服前判定影响；游戏运行时发现必须中断即返回“更新已延后，当前游戏继续运行”，不要提示“请先退出游戏”。调用正式stop-server.ps1的保护不得绕过；也不得改为直接Stop-Process/taskkill终止服务。不要在捕获延期/停服失败后继续写文件或继续启动重复服务。
- 真实state/shop及新进度保护、完整guards/receipt policies、player_import独立检查仍保留。用户明确要求安装某功能不等于允许中断正在进行的游戏。
'''
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
original=(S/'stop-server.ps1').read_text('utf8').replace('\r\n','\n')
assert original.startswith("$ErrorActionPreference='Stop'\n")
guard='''# Never interrupt an active game for a background installation.
function Assert-FO3GameIdle {
    if (Get-Process -Name fifazf -ErrorAction SilentlyContinue) {
        throw '更新已延后，当前游戏继续运行。游戏运行期间禁止停止或重启服务。'
    }
}
Assert-FO3GameIdle
'''
fixed=original.replace("$ErrorActionPreference='Stop'\n","$ErrorActionPreference='Stop'\n"+guard,1)
fixed=fixed.replace('foreach($item in $targets){ Stop-Process','foreach($item in $targets){ Assert-FO3GameIdle; Stop-Process')
assert fixed.count('Assert-FO3GameIdle')==3
(R/'stop-server.ps1').write_text(fixed,'utf-8-sig')
targets=[dict(target=str(S/'stop-server.ps1'),source=str(R/'stop-server.ps1'),before=sha(S/'stop-server.ps1'),root='server',relative='stop-server.ps1')]
for name,path,root,relative in [('server-agents.txt',S/'AGENTS.md','server','AGENTS.md'),('workspace-agents.txt',W/'AGENTS.md','workspace','AGENTS.md')]:
    raw=path.read_bytes();assert '游戏期间安装不得打断游玩'.encode() not in raw
    (R/name).write_bytes(raw+b'\r\n'+policy.encode('utf8'));targets.append(dict(target=str(path),source=str(R/name),before=sha(path),root=root,relative=relative))
coordpath=W/'coordination-current.json';coord=json.loads(coordpath.read_text('utf8'))
coord['game_update_policy']=dict(no_game_exit_requests=True,no_service_interruption_while_game_running=True,server_code_restart='defer_until_user_finishes_playing',client_resources='defer_until_user_finishes_playing',hot_apply='only_verified_compatible_live_configuration_or_transaction',explicit_interruption_authorization_required=True)
(R/'coordination-current.json').write_bytes(body(coord));targets.append(dict(target=str(coordpath),source=str(R/'coordination-current.json'),before=sha(coordpath),root='workspace',relative='coordination-current.json'))
ledger=S/'docs/工程经验与修改边界.txt';ledger.read_bytes()
note='\r\nFO3-NONINTERRUPT-001（2026-11-07）：用户要求游戏期间安装新功能不影响游玩且不要要求退出。确认旧stop-server.ps1无游戏进程保护，部分服务端安装脚本直接停服。正式stop-server现于查目标前和每次终止前检查fifazf，运行时抛“更新已延后，当前游戏继续运行”，不终止任何游戏或服务。工作/正式AGENTS与coordination补充：仅已验证在线兼容配置可热应用；需服务重启/协议DB变更/客户端资源替换均延期，不能把写磁盘称为已热加载，不能绕过停止保护。此保护不能替代安装器正式写入前影响判定，也不能阻止外部任意taskkill；未实现通用Python热加载或自动更新队列。本次无服务重启/客户端资源/state/shop写入。实Windows PowerShell5.1隔离模拟回归覆盖游戏运行、无游戏、停止前出现游戏；不会实际停止服务。证据D:/fifaol3/evidence/noninterrupt-updates。\r\n'
(R/'ledger.txt').write_bytes(ledger.read_bytes()+note.encode());targets.append(dict(target=str(ledger),source=str(R/'ledger.txt'),before=sha(ledger),root='server',relative='docs/工程经验与修改边界.txt'))
(R/'prepared.json').write_bytes(body(targets));print('PREPARED_NONINTERRUPT_UPDATE_POLICY')
