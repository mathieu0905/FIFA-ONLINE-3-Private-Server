"""Install only the client dispatch correction and a fresh guard layer; no service restart."""
from pathlib import Path
import datetime,json,re,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import install_names_route as tx
from build_sql_http import build
S=tx.S;C=tx.C
SELF='patches/sql_http_preflight.py';MANIFEST='patches/sql-http-installed.json';RECEIPT='patches/sql-http-receipt.json'
def main():
    tx.closed()
    with tx.locks():
        tx.closed();play=S/'play-local.bat';oldplay=play.read_bytes()
        parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parent=tx.load(S/parentrel,'sql_http_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
        proof=build();source=(S/'patches/reward_upgrade_preflight.py').read_text('utf8')
        source=source.replace('reward-upgrade-installed.json','sql-http-installed.json').replace('reward-upgrade-receipt.json','sql-http-receipt.json').replace('reward_upgrade_preflight.py','sql_http_preflight.py')
        source=source.replace('INSTALLED_REWARD_UPGRADE','INSTALLED_SQL_HTTP').replace('REWARD_UPGRADE_PREFLIGHT_PASS','SQL_HTTP_PREFLIGHT_PASS').replace('manutd-legends','sql-http').replace('Club-history','SQL-HTTP')
        source=source.replace("('server',SELF)}","('server',SELF),('client','data/ui/libs/module.big')}")
        compile(source,SELF,'exec');revision='sql-http-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-UI-NAMES 再续（'+revision+'）：\n'
          '前一双参native错误回调封装未通过实机：00:36:06点击经理开始后仅有PLAYERGRADE请求、未出现任何兜底SQL HTTP，00:36:51 CLIENT_CRASH。未获得崩溃栈，不能将其当底层损坏已确诊；此回调封装撤回。保留前一正式版本备份及build证明，不覆盖其它聊天代码/资产。\n'
          '本次严格证明当前SQLConnection除本聊天execute和新增callback外与原始一致，再移除本聊天新增callback，恢复原始method数量/全部签名/traits；只在原execute的backend选择前加一条跳转，直接进入原程序现成HTTP SQL分支。原HTTP响应method7、SQLStatement回调、全部原指令及分支重定位保持，不再包装native回调。主服务前一层只读SQL端点保持，姓名/属性/履历真实API已通过，所有写/删表/ATTACH/PRAGMA/load_extension拒绝。\n'
          '仅修改Module及新gate/play/本条账本，不改HTTP/服务/数据库/原生模型/经理资产，不需要重启服务。5种前序字节码测试未覆盖真实native回调ABI，不能再以其冒充native验收；当前原HTTP分支也须以实际/static/sql请求和原生首页为准。\n'
          '证据D:/fifaol3/new-player-models/home-black-screen/sql-http-installed.json、sql-http-build.json；回归build_sql_http.py以及正式patches/sql_http_preflight.py。实机首页/贝林/比赛仍PENDING。\n')
        payloads={C/'data/ui/libs/Module.big':Path(proof['payload']).read_bytes(),S/SELF:source.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8'),play:oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,b in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert tx.sha(p)==guards[key]['sha256']
            elif p.exists():raise AssertionError('Unregistered target: '+str(p))
            guards[key]=dict(root=root,relative=rel,sha256=tx.digest(b))
        composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='sql-http',native_status='PENDING'))
        receipt=json.loads((S/parent.RECEIPT).read_text('utf8'));composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel))
        payloads[S/MANIFEST]=tx.encoded(manifest);payloads[S/RECEIPT]=tx.encoded(dict(status='INSTALLED_SQL_HTTP',manifest_sha256=tx.digest(payloads[S/MANIFEST]),revision=revision,state_shop_replaced=False,native_status='PENDING'))
        for p in (S/SELF,S/MANIFEST,S/RECEIPT):assert not p.exists()
        before={p:p.read_bytes() if p.exists() else None for p in payloads};backup=S/'backups'/revision;backup.mkdir()
        for i,(p,b) in enumerate(before.items()):
            if b is not None:(backup/(str(i)+'-'+p.name)).write_bytes(b)
        (backup/'before.json').write_bytes(tx.encoded({str(p):tx.digest(b) if b is not None else None for p,b in before.items()}))
        protected={str(p):tx.sha(p) for p in (S/'http_config.py',S/'native_sql_fallback.py',S/'gamedata/fifadb.sqlite',C/'data/data_0.big')}
        tx.closed();parent.preflight(S,C);committed=tx.commit(payloads,before,[p for p in payloads if p!=play]+[play])
        try:result=tx.load(S/SELF,'sql_http_installed').preflight(S,C)
        except BaseException:
            for p in reversed(committed):
                if p.read_bytes()!=payloads[p]:raise RuntimeError('Later change retained')
                if before[p] is None:p.unlink()
                else:tx.atomic(p,before[p])
            raise
        assert all(tx.sha(Path(p))==v for p,v in protected.items())
        report=dict(status='INSTALLED_ORIGINAL_HTTP_PATH_NATIVE_PENDING',revision=revision,backup=str(backup),parent=parentrel,preflight=result,
            top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
            hashes={str(p):tx.sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,play,C/'data/ui/libs/Module.big')},protected=protected,
            services_restarted=False,services_restored=True,gui_used=False,state_shop_written=False,native_verified=False,model_crash_fixed=False,failed_native_callback_wrapper_removed=True)
        (ROOT/'sql-http-installed.json').write_bytes(tx.encoded(report))
        observation=dict(status=report['status'],observed_at=datetime.datetime.now().isoformat(),top_preflight=report['top_preflight'],top_manifest=report['top_manifest'],top_receipt=report['top_receipt'],files=report['hashes'],function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),composition_available=True,handoff=str(ROOT/'sql-http-installed.json'),preflight=result,state_shop_written=False,services_restored=True,native_verified=False,match_verified=False)
        tx.atomic(Path('D:/fifaol3/root-current-top.json'),tx.encoded(observation));print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
