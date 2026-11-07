"""Install calibrated existing IM cards using fresh current composition and protected restart."""
from pathlib import Path
from contextlib import contextmanager
import datetime, importlib.util, json, os, re, sys, time, urllib.request, ssl
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from build import S,C,sha,save,load
sys.path.insert(0,r'D:\fifaol3\team-bonus20')
tx=load(Path(r'D:\fifaol3\team-bonus20\install.py'),'im_transaction_utilities');tx.R=R
PY=tx.PY
DOC='docs/工程经验与修改边界.txt'
DOC_ENTRY='\n\nFO3-IM-HIERARCHY22-002（2026-11-07，im-role-hierarchy-plus22-v2）\n用户纠正：IM+10不应压过其它赛季+20，但应强于+18；IM内部也应有合理强弱，允许以整体同档趋势而非逐人同卡严格限制为准。本层替代此前+30；不通过修改旧回执或恢复旧数据库实现。\n123张现有IM按当前本地FC ICON(12)共同来源的overallrating分档，同档再按IM原位置的加权能力排序。内部参考是本地游戏设计数据，不冒称客观足球历史排名。按同位置排序后的其它赛季同档基线配对，IM底板领先21..23点（中心22）；最高参考档+23，中档+22，低档+21。较高参考档不低于较低档。\n33项属性使用本人ICON的同一份属性形状再作等幅移位；当前IM的playerid、位置、模型、身体、花式、逆足、特性及所有非能力字段保持。原平衡记录嵌入prior_balance留痕。其它赛季与数据库其它表逐行保持，BIG只替换UI SQLite成员，原生身份/模型/Lua/语言及非目标成员原压缩字节保持。\n同等级、同位置、同排名档次，双方满强化套、IM触发11人额外加成时：IM+10（24+7+5）对普通+18（40+15）领先2..4点，对普通+20（44+17）落后2..4点。未计各队原俱乐部/国家/特殊套差异，不保证每个同人比较，更不以OVR证明实机手感。\n发布沿用最新父层全部guards/receipt policies、共同双锁、保护停服、新资产快照、备份/CAS、独立player_import及正式完整证书。游戏运行即延后，不自动强退、停服、改资源或使用游戏GUI，不改变真实卡/经验/强化/余额/库存/球队/阵容、价格/成交历史、强化概率或套装规则。\n验证：123卡×33项与28位置、全部同位置参考档排序、同档+18/+20边界、五组主要排序、有序BIG/非目标字节、全表差异、双端回读及player_import --full。正式安装/接口/服务/热包/资产验收看D:/fifaol3/im-balance22/installed-handback.json；工作产物及延期不代表正式生效，原生/比赛/半场/换人仍待验证。\n'
@contextmanager
def locks():
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
            body=tx.encoded(dict(pid=os.getpid(),task='im-balance22',handoff=str(R/'installed-handback.json')))
            owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for path,fd,body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==body:path.unlink()
def plan():
    out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path']);build=json.loads((out/'report.json').read_text('utf8'))
    tests=json.loads((R/'tests.json').read_text('utf8'))
    assert tests['status']=='PASS' and tests['cards']==build['cards'] and tests['builder_sha256']==sha(R/'build.py')
    assert tests['outputs']==build['outputs']
    for name,h in build['baseline'].items():assert sha(name)==h,'Official source changed; rebuild '+name
    for name,h in build['outputs'].items():assert sha(out/name)==h,'Build changed '+name
    play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)\r?$',play)
    assert len(matches)==1
    parentrel=matches[0].decode().replace('\\','/');parent=load(S/parentrel,'im_fresh_parent')
    prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
    validator=load(S/'patches/startup_market_preflight.py','im_validator');validator.verify_manifest(composition,S,C)
    guards=validator.table(composition['guards']);oldreceipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');revision='im-balance22-'+stamp
    gate='patches/im_balance22_'+stamp+'_preflight.py';manifest='patches/'+revision+'-installed.json';receipt='patches/'+revision+'-receipt.json'
    helper=(S/parentrel).read_text('utf8')
    for old,new in ((parent.MANIFEST,manifest),(parent.RECEIPT,receipt),(parent.SELF,gate),(oldreceipt['status'],'INSTALLED_IM_HIERARCHY22'),(prior['status'],'IM_HIERARCHY22_PREFLIGHT_PASS')):
        assert old in helper;helper=helper.replace(old,new)
    anchor='\n if not required<=seen:';assert helper.count(anchor)==1
    required={('server','gamedata/fifadb.sqlite'),('server','gamedata/custom_rosters.json'),('server','gamedata/player-import-validation.json'),('client','data/data_0.big')}
    helper=helper.replace(anchor,'\n required.update('+repr(required)+')'+anchor);compile(helper,gate,'exec')
    pairs=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),
           ('client','data/data_0.big',out/'data_0.big'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json')]
    doc=(S/DOC).read_bytes();assert b'FO3-IM-HIERARCHY22-002' not in doc
    payloads={S/rel:path.read_bytes() for root,rel,path in pairs if root=='server'}
    payloads.update({C/rel:path.read_bytes() for root,rel,path in pairs if root=='client'})
    payloads.update({S/DOC:doc+DOC_ENTRY.encode('utf8'),S/gate:helper.encode('utf8'),S/'play-local.bat':play.replace(matches[0],gate.replace('/','\\').encode())})
    for path,body in payloads.items():
        root='server' if path.is_relative_to(S) else 'client';base=S if root=='server' else C;rel=path.relative_to(base).as_posix();key=(root,rel.casefold())
        if key in guards:assert sha(path)==guards[key]['sha256'],'Current guard differs '+rel
        elif path.exists():raise RuntimeError('Unexpected unguarded existing target '+rel)
        guards[key]=dict(root=root,relative=rel,sha256=tx.digest(body))
    policies=list(composition.get('receipt_policies',[]));policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in oldreceipt.items() if k!='native_status'})
    if not any(p.get('root')=='server' and p.get('relative')==parent.RECEIPT for p in policies):policies.append(policy)
    composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
    composition.setdefault('ancestry',[]).append(dict(layer='im-best-other-plus30-v1',revision=revision,native_status='PENDING'))
    m=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=sha(S/parentrel))
    payloads[S/manifest]=tx.encoded(m);payloads[S/receipt]=tx.encoded(dict(status='INSTALLED_IM_HIERARCHY22',revision=revision,manifest_sha256=tx.digest(payloads[S/manifest]),state_shop_replaced=False,native_status='PENDING'))
    before={p:p.read_bytes() if p.exists() else None for p in payloads}
    return dict(payloads=payloads,before=before,revision=revision,gate=gate,manifest=manifest,receipt=receipt,parent=parentrel,parent_hash=sha(S/parentrel),build=build,out=out)
def apply(p,snapshot):
    tx.closed();assert sha(S/p['parent'])==p['parent_hash']
    backup=S/'backups'/p['revision'];backup.mkdir(parents=True)
    for path,body in p['before'].items():
        if body is not None:
            base=S if path.is_relative_to(S) else C;kind='server' if base==S else 'client';b=backup/kind/path.relative_to(base);b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(body)
    for name,body in snapshot.items():(backup/('snapshot-'+name)).write_bytes(body)
    committed=[]
    try:
        for path in [x for x in p['payloads'] if x!=S/'play-local.bat']+[S/'play-local.bat']:
            tx.closed();tx.cas(path,p['before'][path],p['payloads'][path]);committed.append(path)
        cert=load(S/'tools/player_import/check.py','im_formal_full').validate(S,C,full=True)
        assert cert==json.loads((S/'gamedata/player-import-validation.json').read_text('utf8'))
        check=load(S/p['gate'],'im_installed_gate').preflight(S,C)
        tx.run([PY,'-B',R/'test.py','--installed'])
        for name,body in snapshot.items():assert (S/'gamedata'/name).read_bytes()==body,'Stopped assets changed; never restore assets'
    except BaseException:
        conflicts=[]
        for path in reversed(committed):
            try:tx.cas(path,p['payloads'][path],p['before'][path])
            except RuntimeError:conflicts.append(str(path))
        if conflicts:raise RuntimeError('Later legitimate modifications preserved: '+repr(conflicts))
        raise
    return dict(status='INSTALLED',revision=p['revision'],backup=str(backup),preflight=check,full_player_import=cert['status'],
        top_preflight=str(S/p['gate']),top_manifest=str(S/p['manifest']),top_receipt=str(S/p['receipt']),composition_api='compose_manifest(server=None,client=None)',state_shop_written=False)
def sql_read(query):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    req=urllib.request.Request('https://127.0.0.1/static/sql/fifadb',data=json.dumps(dict(sql=query)).encode(),headers={'Content-Type':'application/json'})
    with opener.open(req,timeout=20) as f:return json.load(f)
def finish(p,result,snapshot,old_hot):
    deadline=time.monotonic()+20;hot=tx.hot_status()
    while (hot['revision']!=old_hot['revision'] or not hot['watcher_running']) and time.monotonic()<deadline:time.sleep(.2);hot=tx.hot_status()
    assert hot['revision']==old_hot['revision'] and hot['routes']==old_hot['routes'] and hot['error'] is None and hot['watcher_running']
    rows=sql_read('SELECT * FROM players WHERE spid/1000000=84');actual={p['spid']:p for p in rows}
    changes=json.loads((p['out']/'changes.json').read_text('utf8'))
    assert len(actual)==len(changes)
    for row in changes:assert actual[row['spid']]==row['after_row']
    colors=tx.get('https://127.0.0.1/static/info/teamcolor');definitions={c['teamcolorid']:c for c in colors['teamColors']}
    assert definitions[60084]['type']=='feature' and definitions[10120]['boostgroups'][0]['boosts'][0]['amount']==17
    with locks():
        assert (S/'play-local.bat').read_bytes()==p['payloads'][S/'play-local.bat'],'Newer legitimate top; retain it'
        check=load(S/p['gate'],'im_final_gate').preflight(S,C)
        state0=json.loads(snapshot['state.json']);state1=json.loads((S/'gamedata/state.json').read_bytes())
        assets=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
        assert assets(state0)==assets(state1),'Concurrent business progress retained; never restore old state'
        assert (S/'gamedata/shop.json').read_bytes()==snapshot['shop.json']
        result.update(status='INSTALLED_AND_RUNTIME_ACTIVE',runtime_active=True,services_restored=True,services_restarted=True,
            preflight=check,hot_update_status=hot,native_verified=False,match_verified=False,state_business_exact=True,shop_exact=True,
            validation=dict(cards=123,stat_checks=4059,position_checks=3444,full_player_import=True,live_sql_all123_exact=True,
                team_bonus20_and_moments_extra_preserved=True,non_target_database_and_big_exact=True,game_gui_used=False),
            base_rating_range=p['build']['base_range'],rank_pairs=json.loads((R/'installed-tests.json').read_text('utf8'))['rank_pairs'],comparison_scope=p['build']['comparison_scope'],im10_vs_peer18_range=p['build']['im10_vs_peer18_range'],im10_vs_peer20_range=p['build']['im10_vs_peer20_range'],
            files={str(path):sha(path) for path in (S/p['gate'],S/p['manifest'],S/p['receipt'],S/'play-local.bat',S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/player-import-validation.json')},
            observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
        save(R/'installed-handback.json',result)
        top=Path(r'D:\fifaol3\root-current-top.json');tx.cas(top,top.read_bytes(),tx.encoded(result))
    print(json.dumps(result,ensure_ascii=True),flush=True)
def main():
    tx.closed()
    regression=json.loads((R/'transaction-tests.json').read_text('utf8'))
    assert regression['status']=='PASS' and regression['installer_sha256']==sha(R/'install.py') and regression['utilities_sha256']==sha(Path(r'D:\fifaol3\team-bonus20\install.py'))
    with locks():
        tx.closed();tx.run([PY,'-B',R/'test.py']);p=plan()
        save(R/'plan.json',{k:(str(v) if isinstance(v,Path) else v) for k,v in p.items() if k not in ('payloads','before','build')})
        old_hot=tx.hot_status();tx.stop()
        snapshot={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
        error=None
        try:result=apply(p,snapshot)
        except BaseException as exc:error=exc
        pid,ready=tx.start()
        if error:raise error
        result.update(launcher_pid=pid,readiness=ready)
    finish(p,result,snapshot,old_hot)
if __name__=='__main__':
    try:main()
    except RuntimeError as exc:
        if str(exc)!='更新已延后，当前游戏继续运行':raise
        save(R/'pending-handback.json',dict(status='DEFERRED_GAME_RUNNING',reason=str(exc),formal_files_written=False,services_restarted=False,state_shop_written=False,game_gui_used=False,latest_build=str(R/'latest-build.json')))
        print(str(exc),flush=True)

