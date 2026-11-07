"""Install exact Bellingham mesh deltas and withdraw only our failed UI edits."""
from pathlib import Path
import datetime,json,os,re,shutil,sys,tempfile
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import install_names_route as tx
from reconcile_native_parent import check as parent_check
S,C=tx.S,tx.C
SELF='patches/native_roster_preflight.py';MANIFEST='patches/native-roster-installed.json';RECEIPT='patches/native-roster-receipt.json'
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
    with tx.locks('native-roster'):
        tx.closed();play=S/'play-local.bat';oldplay=play.read_bytes()
        parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parent=tx.load(S/parentrel,'impact_parent');parentproof=parent_check(parent,S,C);composition=parent.compose_manifest(S,C)
        buildrow=json.loads((R/'native-roster/build.json').read_text('utf8'));build=dict(files=[buildrow])
        payloads={Path(f['target']):Path(f['payload']) for f in build['files']}
        for f in build['files']:
            assert tx.sha(f['target'])==f['before_sha256'] and tx.sha(f['payload'])==f['after_sha256'],'Resource baseline drift'
        revision='native-roster-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        work=R/'native-roster/install-input';work.mkdir(exist_ok=True)
        source=(S/'patches/bellingham_impact_preflight.py').read_text('utf8')
        source=source.replace('bellingham-impact','native-roster').replace('bellingham_impact_preflight.py','native_roster_preflight.py').replace('BELLINGHAM_IMPACT','NATIVE_ROSTER').replace('Bellingham-Impact','Native-Roster')
        assert 'native-roster-installed.json' in source and 'data/data_0.big' in source
        compile(source,SELF,'exec')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-001 / FO3-UI-NAMES 原生球员库续（'+revision+'）：\n'
          '实机失败：用户确认前一层能进入首页，切换贝林仍黑屏卡死；01:20:32只读dump PID85916保留，01:20:42 CLIENT_CRASH。骨骼转换未解决此崩溃，不能再据静态mesh校验声称原生修复通过。\n'
          '确认根因路径：崩溃线程保存EXCEPTION_POINTERS=45b44a9c，record C0000005，EIP008fd780，读地址4，EAX0。原生查询解析器当前token=trainingteamplayers，条件playerid=252371；数据库符号表24表中无此表。原生902b40先SELECT players WHERE playerid，空返回后902bcb走trainingteamplayers并在表符号查找空指针崩溃。当前data/db/fifa_ng_db.db的players62081条确实没有贝林，前序只加SQLite/名字/模型不完整。静态函数解码与真实dump逐项对应；不依赖误导性的最近导出符号名。\n'
          '本次只在EA二进制库players追加贝林真实记录，全部102字段逐项编码、位宽/范围/回读验证；整数按meta rangelow偏移，float按IEEE32，日期按EA Gregorian编码（32483条原生生日与SQLite匹配）。原生headtype13bit容不下UI保留30001选择器，原生用正常专属头规则headtype1023/headclass0/headasset252371，直接指向贝林原模型；UI主库与Lua映射保持原样。未用姆巴佩外貌/能力替代贝林，仅借有效原生record布局模板且全部字段覆盖。\n'
          '原62081条raw record逐字节相同，所有其他EA表逐字节相同，players只增1条；修复表与文件CRC、RefPack回读通过。data0按原目录顺序重建，271条成员中270条原压缩payload及size/usize全部相同，正式check_data0_layout PASS。只改data0/新gate/play/本条账本，Module/三份贝林已转换网格/SQLite/语言库/真实state与shop不改，无服务重启。\n'
          '继承实际http_disconnect最新层，保留HTTP断连修复。该owner完成handoff后单独追加本账本而未登记新hash；严格证明原guard字节为本聊天Impact账本完整前缀，当前只增FO3-024段2710字节，owner五文件与handback哈希一致，其余5598物理guards和所有receipt policies通过；新子层登记该精确append与本条，历史manifest/receipt不改。parent-doc-reconciliation.json保留前缀/追加/现值sha256与完整核验范围。\n'
          '证据D:/fifaol3/new-player-models/home-black-screen/native-roster/{build.json,crash-evidence.json}与native-roster-installed.json。回归正式patches/native_roster_preflight.py、tools/check_data0_layout.py --changed-member data/db/fifa_ng_db.db --baseline 本次data0备份；原生首页切贝林及比赛仍PENDING。其余8个原缺失球员同样未入EA库，此轮不盲目批量加入：例如部分源skillmoves5越过原生0..4语义范围，需后续逐项转换，不能宣称全部新增球员通过。\n')
        small={S/SELF:source.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8'),play:oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode())}
        for i,(p,b) in enumerate(small.items()):q=work/('small-'+str(i));q.write_bytes(b);payloads[p]=q
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,q in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:
                if p==doc and parentproof.get('status')=='ALL_PARENT_GUARDS_EXCEPT_EXACT_APPEND_ONLY_NOTE_PASS':assert tx.sha(p)==parentproof['current_doc_sha256']
                else:assert tx.sha(p)==guards[key]['sha256']
            elif p.exists():raise AssertionError('Unregistered target '+str(p))
            guards[key]=dict(root=root,relative=rel,sha256=tx.sha(q))
        composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='native-roster',native_status='PENDING',parent_physical_verification=parentproof))
        receipt=json.loads((S/parent.RECEIPT).read_text('utf8'));composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel))
        for p,b in {S/MANIFEST:tx.encoded(manifest),S/RECEIPT:tx.encoded(dict(status='INSTALLED_NATIVE_ROSTER',manifest_sha256=tx.digest(tx.encoded(manifest)),revision=revision,state_shop_replaced=False,native_status='PENDING'))}.items():
            assert not p.exists();q=work/p.name;q.write_bytes(b);payloads[p]=q
        for p in (S/SELF,S/MANIFEST,S/RECEIPT):assert not p.exists()
        before={p:tx.sha(p) if p.exists() else None for p in payloads};after={p:tx.sha(q) for p,q in payloads.items()}
        backup=S/'backups'/revision;backup.mkdir();saved={}
        for i,p in enumerate(payloads):
            if before[p] is not None:
                q=backup/(str(i)+'-'+p.name);shutil.copyfile(p,q);assert tx.sha(q)==before[p];saved[p]=q
        protected={str(p):tx.sha(p) for p in (S/'http_config.py',S/'gamedata/fifadb.sqlite',C/'data/ui/libs/Module.big',C/'data/data_4.big',C/'data/data_6.big',S/'gamedata/shop.json')}
        # Read-only fresh asset evidence, never restored by this client-only transaction.
        state=(S/'gamedata/state.json').read_bytes();(backup/'state-observed-readonly.json').write_bytes(state)
        snapshot=json.loads(state);assets_before={k:v for k,v in snapshot.items() if not k.startswith('market')}
        (backup/'before.json').write_bytes(tx.encoded({str(p):h for p,h in before.items()}))
        staged={};committed=[]
        try:
            for p,q in payloads.items():staged[p]=stage(p,q)
            tx.closed();parent_check(parent,S,C)
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
        report=dict(status='INSTALLED_NATIVE_ROSTER_NATIVE_PENDING',revision=revision,backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=result,
          hashes={str(p):tx.sha(p) for p in [S/SELF,S/MANIFEST,S/RECEIPT,play]+[Path(f['target']) for f in build['files']]},parent=parentrel,services_restarted=False,gui_used=False,state_shop_written=False,nonmarket_state_equal=assets_before==assets_after,protected=protected,native_verified=False,match_verified=False)
        (R/'native-roster-installed.json').write_bytes(tx.encoded(report))
        tx.atomic(Path('D:/fifaol3/root-current-top.json'),tx.encoded(dict(status=report['status'],observed_at=datetime.datetime.now().isoformat(),top_preflight=report['top_preflight'],top_manifest=report['top_manifest'],top_receipt=report['top_receipt'],files=report['hashes'],composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),handoff=str(R/'native-roster-installed.json'),preflight=result,state_shop_written=False,services_restarted=False,native_verified=False,match_verified=False)))
        print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
