"""Publish read-per-request static DB leaf responses; no code reload or service actions."""
from pathlib import Path
import hashlib,importlib.util,json,os,ssl,urllib.request,datetime
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
spec=importlib.util.spec_from_file_location('rank_online_release',S/'hot_update_release.py');release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,admin=False):
    with op.open(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,timeout=20) as response:return json.load(response)
def main():
    tables=json.loads((R/'input-tables.json').read_text('utf8'));tests=json.loads((R/'online-tests.json').read_text('utf8'))
    assert tests['status']=='PASS' and tests['leaf_tables']==47
    before_hot=get('/api/hot_update_status',True)
    before_source=release.sha(S/'http_config.py')
    assert before_source==tests['server_source_sha256']
    assert release.sha(S/'gamedata/fifadb.sqlite')==tests['database_sha256']
    # Existing module explicitly reopens responses/<path>.json on every request.
    source=(S/'http_config.py').read_text('utf8')
    assert 'with open(f, "rb") as fh:' in source and 'return _upstream_from_file(path)' in source
    files={f'responses/{p.name}':p.read_bytes() for p in (R/'online-responses').glob('*.json')}
    assert len(files)==47 and all('/static_db_SORT' in n for n in files)
    with release.locks(S,'rank-sort-online-tables'):
        for name in ('SORTNATION','SORTLEAGUE','SORTTEAM'):
            assert get('/static/db/'+name)==tables[name], 'Runtime table advanced; rebuild'
        if release.sha(S/'http_config.py')!=before_source:raise RuntimeError('Source advanced')
        doc=(S/'docs/工程经验与修改边界.txt').read_bytes()
        entry='''\n\nFO3-RANK-SORT-LEAF-20261108\n实机日志定位RoomProxy.onStaticDataFetched空引用：/static/db/SORTLEAGUE/18返回{}，应为[16,17]。上游兼容合入漏选两条匿名SORTLEAGUE/SORTTEAM分表路由；同调用栈随后也在进入比赛时出现，不能据uri=/info/server/time误修时间接口。使用现有from_file每请求重读机制，在线补齐19个国家/28个联赛共47份当前运行表分表数组；不reload模块、不停服、不操作游戏、不写state/shop。所有分表来自正式通用表的同次只读快照，完整国家→联赛→球队链和在线GET逐条核对。该在线缓存绑定本次DB/source指纹；后续注册表/联赛变更需重生成，不能沿用旧分表。工作目录rank-ui-language-fix另准备动态路由修复，待游戏自然关闭后安装，届时分表绕过静态快照实时生成。客户端已经缓存的错误对象不保证自动失效，游戏内恢复/整场比赛仍待验证。AI聊天自动语言属于另一个待加载的代码修改，不因本JSON发布而声称已生效。\n证据D:/fifaol3/rank-ui-language-fix/{captured-ui-errors.json,online-tests.json,online-installed-handback.json}。不修改旧历史凭据来消错。\n'''
        files['docs/工程经验与修改边界.txt']=doc+entry.encode('utf8')
        result=release.commit(S,C,'rank_sort_online_v1',files)
    verified=[]
    for kind in ('SORTLEAGUE','SORTTEAM'):
        for key,expected in tables[kind].items():
            actual=get(f'/static/db/{kind}/{key}')
            assert isinstance(actual,list) and actual==expected,(kind,key,actual)
            verified.append(f'/static/db/{kind}/{key}')
    after_hot=get('/api/hot_update_status',True)
    assert after_hot['revision']==before_hot['revision'] and after_hot['error'] is None and after_hot['watcher_running']
    assert release.sha(S/'http_config.py')==before_source
    result.update(status='ONLINE_SORT_LEAVES_ACTIVE_NATIVE_PENDING',table_routes=len(verified),verified_routes=verified,
                  hot_update_status=after_hot,composition_api='compose_manifest(server=None,client=None)',
                  no_service_actions=True,python_source_changed=False,client_resources_changed=False,real_state_shop_written=False,
                  native_verified=False,game_gui_used=False,observed_at=datetime.datetime.now().astimezone().isoformat())
    (R/'online-installed-handback.json').write_bytes(release.body(result))
    with release.locks(S,'rank-sort-online-handback'):
        expected=Path(result['top_preflight']).name.encode()
        if expected in (S/'play-local.bat').read_bytes():release.atomic(R.parent/'root-current-top.json',release.body(result))
    print(json.dumps({'status':result['status'],'table_routes':len(verified),'top_preflight':result['top_preflight'],'services_restarted':False},ensure_ascii=False))
if __name__=='__main__':main()
