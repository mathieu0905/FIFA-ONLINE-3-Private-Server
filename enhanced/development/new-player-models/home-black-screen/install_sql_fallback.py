"""Publish the error-only SQL fallback, preserving the fresh formal release and assets."""
from pathlib import Path
import datetime, importlib.util, json, re, socket, subprocess, sys, time, urllib.request, ssl
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import install_names_route as tx
from build_sql_fallback import build
S=tx.S;C=tx.C
SELF='patches/native_sql_fallback_preflight.py';MANIFEST='patches/native-sql-fallback-installed.json';RECEIPT='patches/native-sql-fallback-receipt.json'
def stop():
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(S/'stop-server.ps1')],check=True)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        try:
            sock=socket.create_connection(('127.0.0.1',443),timeout=.2);sock.close();time.sleep(.2)
        except OSError:return
    raise RuntimeError('Managed HTTP service did not stop; no payload may be changed')
def start():
    script="""$ErrorActionPreference='Stop'
$env:FO3_GAME='D:\\FO3ID\\32795';$env:FO3_LANGUAGE='chi';$env:FO3_MAX_GRADE='20';$env:FO3_ADMIN_PORT='8088'
Start-Process -FilePath 'D:\\FO3ID\\server\\.venv\\Scripts\\python.exe' -ArgumentList '-B','-u','D:\\FO3ID\\server\\start_all.py' -WorkingDirectory 'D:\\FO3ID\\server' -WindowStyle Hidden -RedirectStandardOutput 'D:\\fifaol3\\new-player-models\\home-black-screen\\sql-fallback-service.log' -RedirectStandardError 'D:\\fifaol3\\new-player-models\\home-black-screen\\sql-fallback-service.err.log'
"""
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],check=True)
    subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','40'],check=True)
def business(raw):return {k:v for k,v in json.loads(raw).items() if k!='market_simulation'}
def verify_live():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    checks=[]
    for database,sql in [('fifadb','SELECT * FROM nameschi WHERE playerid=252371'),('fifadb','SELECT * FROM players WHERE spid=13252371'),('chi','SELECT * FROM names WHERE playerid=252371'),('fifadb','SELECT * FROM playerhistory WHERE playerid=252371 ORDER BY ordernum DESC')]:
        req=urllib.request.Request('https://127.0.0.1/static/sql/'+database,data=json.dumps(dict(sql=sql)).encode(),headers={'Content-Type':'application/json','Host':'APSEODESK172'})
        with opener.open(req,timeout=10) as response:rows=json.load(response)
        assert isinstance(rows,list) and rows,(database,rows)
        checks.append(dict(database=database,sql=sql,rows=len(rows)))
    req=urllib.request.Request('https://127.0.0.1/static/sql/fifadb',data=json.dumps(dict(sql='DELETE FROM players')).encode(),headers={'Content-Type':'application/json'})
    with opener.open(req,timeout=10) as response:denied=json.load(response)
    assert denied.get('result') is False
    checks.append(dict(write_rejected=denied))
    return checks
def main():
    tx.closed();transaction_tests=tx.test_commit()
    with tx.locks():
        tx.closed();play=S/'play-local.bat';oldplay=play.read_bytes()
        parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parent=tx.load(S/parentrel,'sql_fallback_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
        proof=build();source=(S/'patches/reward_upgrade_preflight.py').read_text('utf8')
        source=source.replace('reward-upgrade-installed.json','native-sql-fallback-installed.json').replace('reward-upgrade-receipt.json','native-sql-fallback-receipt.json').replace('reward_upgrade_preflight.py','native_sql_fallback_preflight.py')
        source=source.replace('INSTALLED_REWARD_UPGRADE','INSTALLED_NATIVE_SQL_FALLBACK').replace('REWARD_UPGRADE_PREFLIGHT_PASS','NATIVE_SQL_FALLBACK_PREFLIGHT_PASS').replace('manutd-legends','native-sql-fallback').replace('Club-history','Native-SQL-fallback')
        source=source.replace("('server',SELF)}","('server',SELF),('server','native_sql_fallback.py'),('server','http_config.py'),('client','data/ui/libs/module.big')}")
        compile(source,SELF,'exec');revision='native-sql-fallback-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-UI-NAMES 续（'+revision+'）：\n'
          '上一names-route未解决实机故障：00:17:47真实UI telemetry已从no such table: names变成no such table: nameschi，证实路由已加载但客户端读取主库仍失败。不能把离线存在表与整表等价当原生打开成功。该失败样本保留captures/http_config.log及本任务sql-fallback-build.json。启动临时7BC7.tmp为0字节、7BD8.tmp为完整chi加密库，尚未证明底层读取失败的唯一原因，不修改内存池掩盖问题。\n'
          '修复为SQLConnection.execute原生错误回调单次兜底：原生成功直接按原数据/错误回调；仅原生查询失败才使用原客户端既有/static/sql/<db> HTTP分支及原method7响应处理，读取正式fifadb或当前data0语言库的只读查询。不是忽略错误或返回虚构空球员。新增Reader只读URI/query_only/authorizer/超时和行数上限，写入、删表、ATTACH、PRAGMA、load_extension、多语句拒绝。原生3D/比赛是否恢复仍待实机确认。\n'
          '实际回调字节码回放5种成功/缺表样本通过；6语言姓名、主库真实贝林属性、履历及恶意写语句16类只读回归通过。仅一个Module DoABC中的SQLConnection.execute包装原native回调并增加双参闭包，原HTTP回调、其它方法/签名/trait/非目标tags保持。正式HTTP仅追加install hook，保留最新ratesv2/市场等修改。共同双锁+fresh parent+停服新资产快照，保留经理/球队/卡/余额/库存/阵容，绝不回写旧state/shop。\n'
          '证据D:/fifaol3/new-player-models/home-black-screen/sql-fallback-installed.json；回归build_sql_fallback.py与正式patches/native_sql_fallback_preflight.py。状态：正式安装、只读API通过，native首页/贝林/比赛待人类验证。\n')
        payloads={C/'data/ui/libs/Module.big':Path(proof['payload']).read_bytes(),S/'http_config.py':(ROOT/'sql-fallback-http_config.py').read_bytes(),S/'native_sql_fallback.py':(ROOT/'native_sql_fallback.py').read_bytes(),S/SELF:source.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8'),play:oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,b in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert tx.sha(p)==guards[key]['sha256']
            elif p.exists():assert p==doc
            guards[key]=dict(root=root,relative=rel,sha256=tx.digest(b))
        composition.update(guards=list(guards.values()));composition.setdefault('ancestry',[]).append(dict(layer='native-sql-fallback',native_status='PENDING'))
        receipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
        composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel))
        payloads[S/MANIFEST]=tx.encoded(manifest);payloads[S/RECEIPT]=tx.encoded(dict(status='INSTALLED_NATIVE_SQL_FALLBACK',manifest_sha256=tx.digest(payloads[S/MANIFEST]),revision=revision,state_shop_replaced=False,native_status='PENDING'))
        for p in (S/SELF,S/MANIFEST,S/RECEIPT):assert not p.exists()
        before={p:p.read_bytes() if p.exists() else None for p in payloads};backup=S/'backups'/revision;backup.mkdir()
        for i,(p,b) in enumerate(before.items()):
            if b is not None:(backup/(str(i)+'-'+p.name)).write_bytes(b)
        (backup/'before.json').write_bytes(tx.encoded({str(p):tx.digest(b) if b is not None else None for p,b in before.items()}))
        tx.closed();parent.preflight(S,C);stop();committed=[];running=False
        fresh={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json','fifadb.sqlite','custom_rosters.json','enhancement_rates.json')}
        client_db_before=tx.sha(C/'data/data_0.big')
        for name,b in fresh.items():(backup/('fresh-'+name)).write_bytes(b)
        try:
            committed=tx.commit(payloads,before,[p for p in payloads if p!=play]+[play])
            check=tx.load(S/SELF,'sql_fallback_installed').preflight(S,C)
            start();running=True;live=verify_live()
            assert business(fresh['state.json'])==business((S/'gamedata/state.json').read_bytes())
            for name in ('shop.json','fifadb.sqlite','custom_rosters.json','enhancement_rates.json'):assert (S/'gamedata'/name).read_bytes()==fresh[name],name
            assert tx.sha(C/'data/data_0.big')==client_db_before
        except BaseException:
            if running:stop();running=False
            for p in reversed(committed):
                if not p.exists() or p.read_bytes()!=payloads[p]:raise RuntimeError('Later formal version retained; rollback requires review')
                if before[p] is None:p.unlink()
                else:tx.atomic(p,before[p])
            raise
        finally:
            if not running:start()
        report=dict(status='INSTALLED_SERVICES_RUNNING_NATIVE_PENDING',revision=revision,backup=str(backup),parent=parentrel,preflight=check,live_queries=live,transaction_tests=transaction_tests,
            top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
            hashes={str(p):tx.sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,play,C/'data/ui/libs/Module.big',S/'http_config.py',S/'native_sql_fallback.py')},
            services_restarted=True,services_restored=True,gui_used=False,state_shop_written=False,nonmarket_business_unchanged=True,client_data0_unchanged=True,native_verified=False,model_crash_fixed=False)
        (ROOT/'sql-fallback-installed.json').write_bytes(tx.encoded(report))
        observation=dict(status='OBSERVED_NATIVE_SQL_FALLBACK_INSTALLED_NATIVE_PENDING',observed_at=datetime.datetime.now().isoformat(),top_preflight=report['top_preflight'],top_manifest=report['top_manifest'],top_receipt=report['top_receipt'],files=report['hashes'],composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),preflight=check,handoff=str(ROOT/'sql-fallback-installed.json'),state_shop_written=False,services_restored=True,native_verified=False,match_verified=False)
        tx.atomic(Path('D:/fifaol3/root-current-top.json'),tx.encoded(observation));print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
