from pathlib import Path
import datetime,json,sys,urllib.request
sys.dont_write_bytecode=True
sys.path.insert(0,'D:/FO3ID/server')
from hot_update_release import atomic,body,commit,locks,sha
S=Path('D:/FO3ID/server');W=Path('D:/fifaol3');R=Path(__file__).parent
SECTION='''
## 已接入的业务热更新（2026-11-07）

- 首次接入重启已经完成；不要因为新开聊天再做“首次重启”。每次先在正式目录执行 `.venv\\Scripts\\python.exe -B hot_update_control.py`，以实际ABI/revision/watcher_running/error判断运行状态；初始revision为bootstrap、routes为空表示机制已运行但尚无业务热包，不代表所有现有Python代码都已支持热加载。
- 服务端功能修改优先使用已接入的业务热更新或原有在线配置接口，避免为方便安装而重启。先阅读正式 `D:\\FO3ID\\server\\docs\\hot-update.md`。只有适配为 `(host, query, body)` 的精确HTTP处理函数可使用当前ABI1；支持/shop/、/bag/、/items/、/item/、/events/、/hot/以及/bag、/events、/specifictarget、/monthlypack。普通Python文件覆盖、市场后台worker/对象方法/闭包不会自动更新，不能报成已生效。
- 连接、经理会话、比赛、存档格式、数据库结构、客户端BIG/模型/语言不属于当前热更新范围。禁止盲目reload整个模块或重新运行install hooks，禁止通过停服/断线实现“热更新”。需中断的改动仍按游戏期间不得打断约定延后。
- 热包顶层只允许文档字符串和无装饰器/注解/默认参数的函数定义；不得在加载时写资产、启动线程或改连接/全局状态。沿用现有STATE_LOCK和存档事务/校验/幂等规则，先以临时数据完成该业务自己的回归；框架通过不代替业务正确性或实机验收。
- 正式发布用 `.venv\\Scripts\\python.exe -B hot_update_publish.py --source <已验证代码.py> --revision <唯一版本> --expected-revision <实际运行版本> --route <精确路径=函数名>`。工具沿用共同双锁、最新父层、完整guards/receipt policies、备份/CAS和最后原子激活；不得覆盖不可变历史business.py，不手工绕过发布工具改active.json，不写真实测试卡/余额。
- 发布成功只表示文件事务完成。再次执行hot_update_control.py，只有实际revision匹配、watcher_running=true、error=null才报告已激活。加载失败继续旧版本；运行时业务异常不会自动重放，避免重复扣费/发卡。提交后交还实际最新入口、compose_manifest及三元组哈希，不恢复旧顶层。
- 回退使用 `hot_update_control.py --rollback <历史版本>`；撤下全部热路由使用 `hot_update_control.py --disable`。二者仅切换业务函数，绝不回退state/shop或撤销已完成交易，完成后核实状态。用户游玩中禁止额外重启、强退或游戏GUI操作。
- 当前接入证据：`D:\\fifaol3\\hot-update\\connected-handback.json`，框架18项和首次引导4项回归通过，HTTPS/管理页/messenger就绪；实际业务包正式热切换及游戏/比赛验收尚未完成，不得冒称通过。后续证据应按实际进展更新。
'''
def update(path):
    original=path.read_bytes()
    assert '## 已接入的业务热更新'.encode() not in original
    text=original.decode('utf8')
    text=text.replace('只有经确认支持在线读取/事务热保存且兼容当前运行进程的服务端配置或功能，才可在游戏期间正式生效；','只有经确认兼容当前运行进程的在线配置、事务热保存或下述已适配业务热包，才可在游戏期间正式生效；')
    return original,(text+'\n'+SECTION).encode('utf8')
def main():
    with locks(S,'update-agent-hot-update-docs'):
        coord=json.loads((W/'coordination-current.json').read_text('utf8'));assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8088/api/hot_update_status',timeout=3) as r:status=json.load(r)
        assert status.get('abi')==1 and status.get('watcher_running') and status.get('error') is None,status
        workspace_old,workspace_new=update(W/'AGENTS.md');server_old,server_new=update(S/'AGENTS.md')
        ledger=S/'docs/工程经验与修改边界.txt'
        note='\r\nFO3-HOT-BUSINESS-001 文档续（2026-11-07）：首次接入重启完成，实际hot_update_status为ABI1/bootstrap/routes空/error空/watcher_running真。按用户要求同步工作/正式AGENTS：优先业务热更新、范围/发布/激活判断/回退/资产与不中断边界；不把连接完成写成实际业务包或实机比赛通过。本次纯文档增量+新组合门禁，无服务启停/游戏操作/资产写入。证据hot-update/agent-docs-handback.json。\r\n'
        result=commit(S,Path('D:/FO3ID/32795'),'hot_agent_docs',{'AGENTS.md':server_new,'docs/工程经验与修改边界.txt':ledger.read_bytes()+note.encode()})
        backup=Path(result['backup']);(backup/'workspace-AGENTS.before').write_bytes(workspace_old)
        assert (W/'AGENTS.md').read_bytes()==workspace_old,'Concurrent workspace instructions edit; retain and reconcile'
        atomic(W/'AGENTS.md',workspace_new)
        assert '## 已接入的业务热更新' in (S/'AGENTS.md').read_text('utf8') and '## 已接入的业务热更新' in (W/'AGENTS.md').read_text('utf8')
        result.update(status='HOT_UPDATE_AGENT_DOCS_UPDATED',observed_at=datetime.datetime.now().astimezone().isoformat(),hot_update_status=status,runtime_active=True,restart_performed=False,updated_docs={str(p):sha(p) for p in (S/'AGENTS.md',W/'AGENTS.md')},handoff=str(R/'agent-docs-handback.json'))
        atomic(R/'agent-docs-handback.json',body(result));atomic(W/'root-current-top.json',body(result));print(json.dumps(result))
if __name__=='__main__':main()
