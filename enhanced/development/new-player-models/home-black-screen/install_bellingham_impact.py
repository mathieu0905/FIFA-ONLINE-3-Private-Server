"""Install exact Bellingham mesh deltas and withdraw only our failed UI edits."""
from pathlib import Path
import datetime,json,os,re,shutil,sys,tempfile
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import install_names_route as tx
S,C=tx.S,tx.C
SELF='patches/bellingham_impact_preflight.py';MANIFEST='patches/bellingham-impact-installed.json';RECEIPT='patches/bellingham-impact-receipt.json'
def stage(target,source):
    fd,name=tempfile.mkstemp(prefix=target.name+'.bellingham-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as out,Path(source).open('rb') as inp:
            shutil.copyfileobj(inp,out,8*1024*1024);out.flush();os.fsync(out.fileno())
        assert tx.sha(name)==tx.sha(source)
        return Path(name)
    except BaseException:
        Path(name).unlink(missing_ok=True);raise
def main():
    tx.closed()
    coord=json.loads(Path('D:/fifaol3/coordination-current.json').read_text('utf8'))
    assert not coord.get('queue') and not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer'),'Another writer requires coordination'
    with tx.locks('bellingham-impact'):
        tx.closed();play=S/'play-local.bat';oldplay=play.read_bytes()
        parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parent=tx.load(S/parentrel,'impact_parent');parent.preflight(S,C);composition=parent.compose_manifest(S,C)
        build=json.loads((R/'bellingham-impact/archive-build.json').read_text('utf8'))
        payloads={Path(f['target']):Path(f['payload']) for f in build['files']}
        for f in build['files']:
            assert tx.sha(f['target'])==f['before_sha256'] and tx.sha(f['payload'])==f['after_sha256'],'Resource baseline drift'
        revision='bellingham-impact-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        work=R/'bellingham-impact/install-input';work.mkdir(exist_ok=True)
        source=(S/'patches/sql_http_preflight.py').read_text('utf8')
        source=source.replace('sql-http','bellingham-impact').replace('sql_http_preflight.py','bellingham_impact_preflight.py').replace('SQL_HTTP','BELLINGHAM_IMPACT').replace('SQL-HTTP','Bellingham-Impact')
        source=source.replace("('client','data/ui/libs/module.big')}","('client','data/ui/libs/module.big'),('client','data/data_4.big'),('client','data/data_6.big')}")
        assert 'bellingham-impact-installed.json' in source and 'data/data_6.big' in source
        compile(source,SELF,'exec')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-UI-NAMES / FO3-001 模型续（'+revision+'）：\n'
          '失败样本：本聊天names路由、native回调兜底和强制HTTP SQL分支均未通过实机；00:42:36经理开始后仅一次nameschi SQL请求，00:43:21 CLIENT_CRASH。此次撤回本聊天Module全部改动，严格当前8a8f3a97…基线及原始备份1b9519f9…匹配，非gfx成员逐字节一致，原始gfx解压与修改前current-Module.swf一致；不回退其它聊天服务/资源/发行层。只读HTTP端点保留但原始Module不会被强制路由过去。\n'
          '确认：用户00:55:59正式客户端经理列表只读dump，PID84080，7EA8.tmp=54134784、7EC8.tmp=5647360，与当前主库/chi库完整长度相同；原生FileGetSize离线重放三路径成功。早先主库临时文件为0异常未稳定复现，池容量不足仍是假设，不据此改内存池。\n'
          '确认：贝林头/近发/远发源255骨骼，原生ImpactEngine252，编号存在不同语义。使用作者FIFA Converter25.09.14静态CIL提取的BoneStrToIEIndex别名及FIFA14_Switch/ImpactEngine骨骼表，将实际正权重骨骼逐名映射，合并同骨骼整数权重，总权重不变；保留目的原生skin模板252矩阵，与作者ConvertToRx3策略一致。未执行第三方转换器。仅修改三份RX3的blend索引/权重、remap和skin；所有位置/法线/UV/三角索引/材质/贴图/section offset/文件长度不变，skin尾部192字节留零空隙。\n'
          '正式data4只改贝林头和近发，data6只改贝林远发，BIG目录/其它成员原压缩字节全相同；独立有界解析器验证5个mesh均252矩阵、骨骼范围/重映射覆盖/权重/索引/有限数值通过。保留贝林两张卡及全部其它真实资产/阵容，不改state/shop/DB/data0/player.lua/其它新球员。此静态兼容修复不等于原生首页或比赛通过，真正崩溃原因尚待用户手动启动验收。\n'
          '证据D:/fifaol3/new-player-models/home-black-screen/bellingham-impact/{report.json,independent-mesh-validation.json,archive-build.json}、bellingham-impact-installed.json；坏样本原始导入资源与此前Module备份保留。回归retarget_bellingham.py仅用于构建前源基线，安装后使用正式patches/bellingham_impact_preflight.py及独立mesh解析器。无GUI操作，无启动/强制关闭游戏，无服务重启。\n')
        small={S/SELF:source.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8'),play:oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
        for i,(p,b) in enumerate(small.items()):q=work/('small-'+str(i));q.write_bytes(b);payloads[p]=q
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,q in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert tx.sha(p)==guards[key]['sha256']
            elif p.exists():raise AssertionError('Unregistered target '+str(p))
            guards[key]=dict(root=root,relative=rel,sha256=tx.sha(q))
        composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='bellingham-impact',native_status='PENDING'))
        receipt=json.loads((S/parent.RECEIPT).read_text('utf8'));composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel))
        for p,b in {S/MANIFEST:tx.encoded(manifest),S/RECEIPT:tx.encoded(dict(status='INSTALLED_BELLINGHAM_IMPACT',manifest_sha256=tx.digest(tx.encoded(manifest)),revision=revision,state_shop_replaced=False,native_status='PENDING'))}.items():
            assert not p.exists();q=work/p.name;q.write_bytes(b);payloads[p]=q
        for p in (S/SELF,S/MANIFEST,S/RECEIPT):assert not p.exists()
        before={p:tx.sha(p) if p.exists() else None for p in payloads};after={p:tx.sha(q) for p,q in payloads.items()}
        backup=S/'backups'/revision;backup.mkdir();saved={}
        for i,p in enumerate(payloads):
            if before[p] is not None:
                q=backup/(str(i)+'-'+p.name);shutil.copyfile(p,q);assert tx.sha(q)==before[p];saved[p]=q
        protected={str(p):tx.sha(p) for p in (S/'http_config.py',S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/shop.json')}
        # Read-only fresh asset evidence, never restored by this client-only transaction.
        state=(S/'gamedata/state.json').read_bytes();(backup/'state-observed-readonly.json').write_bytes(state)
        snapshot=json.loads(state);assets_before={k:v for k,v in snapshot.items() if not k.startswith('market')}
        (backup/'before.json').write_bytes(tx.encoded({str(p):h for p,h in before.items()}))
        staged={};committed=[]
        try:
            for p,q in payloads.items():staged[p]=stage(p,q)
            tx.closed();parent.preflight(S,C)
            for p in [p for p in payloads if p!=play]+[play]:
                tx.closed()
                assert (tx.sha(p) if p.exists() else None)==before[p],'Concurrent edit retained '+str(p)
                os.replace(staged[p],p);committed.append(p)
            result=tx.load(S/SELF,'impact_installed').preflight(S,C)
            for p,h in protected.items():assert tx.sha(p)==h,'Protected file changed '+p
        except BaseException:
            for p in reversed(committed):
                if tx.sha(p)!=after[p]:raise RuntimeError('Later version retained; cannot roll back '+str(p))
                if before[p] is None:p.unlink()
                else:os.replace(stage(p,saved[p]),p)
            raise
        finally:
            for q in staged.values():q.unlink(missing_ok=True)
        snapshot_after=json.loads((S/'gamedata/state.json').read_bytes());assets_after={k:v for k,v in snapshot_after.items() if not k.startswith('market')}
        report=dict(status='INSTALLED_BELLINGHAM_IMPACT_NATIVE_PENDING',revision=revision,backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=result,
          hashes={str(p):tx.sha(p) for p in [S/SELF,S/MANIFEST,S/RECEIPT,play]+[Path(f['target']) for f in build['files']]},parent=parentrel,services_restarted=False,gui_used=False,state_shop_written=False,nonmarket_state_equal=assets_before==assets_after,protected=protected,native_verified=False,match_verified=False)
        (R/'bellingham-impact-installed.json').write_bytes(tx.encoded(report))
        tx.atomic(Path('D:/fifaol3/root-current-top.json'),tx.encoded(dict(status=report['status'],observed_at=datetime.datetime.now().isoformat(),top_preflight=report['top_preflight'],top_manifest=report['top_manifest'],top_receipt=report['top_receipt'],files=report['hashes'],composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),handoff=str(R/'bellingham-impact-installed.json'),preflight=result,state_shop_written=False,services_restarted=False,native_verified=False,match_verified=False)))
        print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
