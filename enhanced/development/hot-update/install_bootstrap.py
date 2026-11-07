"""Install inert bootstrap on disk; deliberately never restart the user's live game services."""
from pathlib import Path
import ast,datetime,json,sys
sys.dont_write_bytecode=True
from hot_update_release import atomic,body,commit,locks,sha
R=Path(__file__).parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')

def build():
    source=S/'http_config.py';raw=source.read_bytes();code=raw.decode('utf8').replace('\r\n','\n')
    needle='                    ctype, data = from_file(path) or (ENDPOINTS.get(path) or route(path) or fallback)(query, body)'
    assert code.count(needle)==1,'Rebase dispatch hook'
    code=code.replace(needle,'''                    hot_handler = hot_update_manager.handler(path)
                    ctype, data = hot_handler(query, body) if hot_handler else from_file(path) or (ENDPOINTS.get(path) or route(path) or fallback)(query, body)''')
    needle='if __name__ == "__main__":'
    assert code.count(needle)==1 and 'import hot_update_runtime' not in code
    code=code.replace(needle,'import hot_update_runtime\nhot_update_runtime.install(sys.modules[__name__])\n\n'+needle)
    needle='    market_engine.start_background()';assert code.count(needle)==1
    code=code.replace(needle,needle+'\n    hot_update_manager.start()')
    needle='        market_engine.stop_background()';assert code.count(needle)==1
    code=code.replace(needle,'        hot_update_manager.stop()\n'+needle)
    compile(code,str(source),'exec');(R/'http_config.py').write_text(code,'utf8')
    # The only existing request function edited is H._respond; all other defs stay exact.
    old,new=ast.parse(raw),ast.parse(code)
    def definitions(tree):
        out={}
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                if isinstance(node,ast.ClassDef) and node.name=='H':
                    for method in node.body:
                        if isinstance(method,ast.FunctionDef) and method.name!='_respond':out['H.'+method.name]=ast.dump(method,include_attributes=False)
                else:out[node.name]=ast.dump(node,include_attributes=False)
        return out
    assert definitions(old)==definitions(new),'Unrelated host function changed'
    result=dict(status='BOOTSTRAP_PREPARED_NOT_RUNNING',http_before_sha256=sha(source),http_after_sha256=sha(R/'http_config.py'),existing_functions_preserved=True)
    (R/'prepared.json').write_bytes(body(result));return raw,code.encode('utf8')

def main():
    raw,http=build()
    if '--build' in sys.argv:print('BOOTSTRAP_BUILD_PASS');return
    tests=json.loads((R/'tests.json').read_text('utf8'));assert tests['status']=='PASS'
    assert json.loads((R/'bootstrap-tests.json').read_text('utf8'))['status']=='PASS'
    with locks(S,'hot-update-bootstrap-no-restart'):
        coord=json.loads((W/'coordination-current.json').read_text('utf8'));assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
        assert (S/'http_config.py').read_bytes()==raw,'Host changed; rebase'
        payload={'http_config.py':http}
        for name in ('hot_update_runtime.py','hot_update_release.py','hot_update_publish.py','hot_update_control.py'):
            data=(R/name).read_bytes();compile(data,name,'exec');payload[name]=data
        payload['docs/hot-update.md']=(R/'README.md').read_bytes()
        ledger=S/'docs/工程经验与修改边界.txt';ledger.read_bytes()
        note='\r\nFO3-HOT-BUSINESS-001（2026-11-07）：用户明确允许先做好热更新、退出游戏后再重启接入，当前不打断游玩。本层仅在磁盘安装首次引导与版本化精确HTTP业务路由加载器，不执行重启/GUI/客户端资源/state/shop写入。仅shop/bag/items/item/events/specifictarget/monthlypack及独立hot路径；连接/经理/比赛/存档核心/后台worker不热换，不盲目reload模块。编译及发布凭据校验在存档锁外、请求完整事务结束后在同一STATE_LOCK切换，旧请求保留原函数；加载失败保留旧版，运行时业务异常不重试以防重复扣款。发布工具共同双锁+fresh父层+guard/receipt全继承+备份CAS+activation最后原子提交；不可变代码与历史凭据保留，回退/disable仅切业务不回存档。框架回归17项及首次引导静态/派发回归，不代替每项业务的契约/幂等测试或游戏比赛验收。当前进程尚未加载，须游戏自然结束后的正常首次重启；不得将磁盘安装写成当前热更新已激活。证据D:/fifaol3/hot-update/{tests.json,bootstrap-tests.json,installed-handback.json}，正式docs/hot-update.md。\r\n'
        payload['docs/工程经验与修改边界.txt']=ledger.read_bytes()+note.encode()
        result=commit(S,C,'hot_bootstrap',payload)
        result.update(status='HOT_BOOTSTRAP_INSTALLED_PENDING_IDLE_RESTART',observed_at=datetime.datetime.now().astimezone().isoformat(),runtime_active=False,restart_performed=False,tests=tests,activation='After user naturally finishes playing, normal service restart loads bootstrap; never interrupt current game',handoff=str(R/'installed-handback.json'))
        atomic(R/'installed-handback.json',body(result));atomic(W/'root-current-top.json',body(result));print(json.dumps(result))
if __name__=='__main__':main()
