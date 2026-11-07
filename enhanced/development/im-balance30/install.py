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
DOC_ENTRY='''

FO3-IM-BALANCE30-001（2026-11-07，im-best-other-plus30-v1）
用户指出IM难以强化到+20，原基础+15会被其它赛季高强化反超。本层按当前同人非IM卡在IM主位置的最高真实加权能力+30作底线；对现有IM的33项能力作同幅上移，保留其属性差、原本强项及全部身份/位置/身体/花式/逆足/特性/模型元数据，已有更强者不下调。
123张既有84赛季卡全部校准；未新增身份/资源。原IM贝克汉姆取10季65模板仅得80，低于MUL88，现校至118；大罗104→120，范巴斯滕103→120。基础主位置111..122。此为当前数据库同位置、同等级的数值口径，不代表实机手感。
当前强化曲线+10属性24、+20属性44；IM基础领先至少30使IM+10在不计套装时至少领先同人非IM+20约10点；再计满首发强化套7对17及IM额外5后，理论仍至少+5（未计两队原俱乐部/国家/特殊套差异）。不改强化概率、道具、套装规则、NPC强化上限或价格/成交历史。
数据只改服务端UI SQLite中IM的33项字段，BIG只替换同一UI SQLite成员，注册表追加当前平衡来源/前后行哈希；其它球员/表、原生EA身份库、模型、Lua、语言与非目标成员原压缩字节保持。不得改历史模板回执或把旧存档回写。
发布沿用fresh最新父层完整guards/receipt policies、共同双锁、正式保护停服、停服实时state/shop快照、备份/CAS、player_import独立检查及更新绑定正式输入的完整校验证书。用户游戏运行则延后，禁止强退/GUI操作。
验证：123卡×33项、123卡×28位置差值、同人最好锚点和高强化追平、数据库全表非目标差异、有序BIG/非目标原字节、双端解密一致、player_import --full；正式接口/服务/热包与资产核对见D:/fifaol3/im-balance30/installed-handback.json。首页/比赛/半场/换人仍待实机验收。
'''
@contextmanager
def locks():
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
            body=tx.encoded(dict(pid=os.getpid(),task='im-balance30',handoff=str(R/'installed-handback.json')))
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
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');revision='im-balance30-'+stamp
    gate='patches/im_balance30_'+stamp+'_preflight.py';manifest='patches/'+revision+'-installed.json';receipt='patches/'+revision+'-receipt.json'
    helper=(S/parentrel).read_text('utf8')
    for old,new in ((parent.MANIFEST,manifest),(parent.RECEIPT,receipt),(parent.SELF,gate),(oldreceipt['status'],'INSTALLED_IM_BALANCE30'),(prior['status'],'IM_BALANCE30_PREFLIGHT_PASS')):
        assert old in helper;helper=helper.replace(old,new)
    anchor='\n if not required<=seen:';assert helper.count(anchor)==1
    required={('server','gamedata/fifadb.sqlite'),('server','gamedata/custom_rosters.json'),('server','gamedata/player-import-validation.json'),('client','data/data_0.big')}
    helper=helper.replace(anchor,'\n required.update('+repr(required)+')'+anchor);compile(helper,gate,'exec')
    pairs=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),
           ('client','data/data_0.big',out/'data_0.big'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json')]
    doc=(S/DOC).read_bytes();assert b'FO3-IM-BALANCE30-001' not in doc
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
    payloads[S/manifest]=tx.encoded(m);payloads[S/receipt]=tx.encoded(dict(status='INSTALLED_IM_BALANCE30',revision=revision,manifest_sha256=tx.digest(payloads[S/manifest]),state_shop_replaced=False,native_status='PENDING'))
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
            base_rating_range=[p['build']['base_min'],p['build']['base_max']],highlights=p['build']['highlights'],
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
if __name__=='__main__':main()
