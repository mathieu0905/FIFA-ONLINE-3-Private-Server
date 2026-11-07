"""Single official transaction for complete player imports and the prevention gate."""
import datetime,importlib.util,json,os,pathlib,re,shutil,socket,ssl,subprocess,sys,time,urllib.request
sys.dont_write_bytecode=True
R=pathlib.Path(__file__).resolve().parent;W=R.parent/'home-black-screen';sys.path.insert(0,str(W))
import install_names_route as tx
from install_bellingham_impact import stage
S,C=tx.S,tx.C;SELF='patches/player_import_preflight.py';MANIFEST='patches/player-import-installed.json';RECEIPT='patches/player-import-receipt.json'
def listening(port):
    try:
        with socket.create_connection(('127.0.0.1',port),.3):return True
    except OSError:return False
def stop():
    subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],cwd=S,check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    until=time.monotonic()+30
    while any(listening(p) for p in [443,8088,28002]):
        if time.monotonic()>until:raise RuntimeError('Managed services did not stop')
        time.sleep(.2)
def start():
    with (S/'captures/player-import-restart.log').open('ab') as out:
        subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env={**os.environ,'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'},stdin=subprocess.DEVNULL,stdout=out,stderr=out,creationflags=subprocess.CREATE_NO_WINDOW)
    until=time.monotonic()+55
    while not all(listening(p) for p in [443,8088,28002]):
        if time.monotonic()>until:raise RuntimeError('Managed services recovery timed out')
        time.sleep(.2)
def main():
    tx.closed();coord=json.loads(pathlib.Path('D:/fifaol3/coordination-current.json').read_text('utf8'))
    assert not coord.get('queue') and not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
    build=json.loads((R/'built/build.json').read_text('utf8'));test=json.loads((R/'tool-tests.json').read_text('utf8'));bad=json.loads((R/'original-rejection.json').read_text('utf8'));assert test['status']==bad['status']=='PASS'
    cert=json.loads((R/'built/player-import-validation.json').read_text('utf8'));assert cert['status']=='PLAYER_IMPORT_FULL_PASS'
    with tx.locks('player-import-complete'):
        tx.closed();play=S/'play-local.bat';oldplay=play.read_bytes();parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parent=tx.load(S/parentrel,'complete_player_parent');parent.preflight(S,C);composition=parent.compose_manifest(S,C)
        revision='player-import-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S');work=R/'install-input';work.mkdir(exist_ok=True)
        payloads={};buildfiles=build['archives']+[build['database']]
        for f in buildfiles:
            assert tx.sha(f['target'])==f['before_sha256'] and tx.sha(f['payload'])==f['after_sha256'],'Build source drift: '+f['target']
            payloads[pathlib.Path(f['target'])]=pathlib.Path(f['payload'])
        for p in (R/'tooling').iterdir():
            if p.is_file():payloads[S/'tools/player_import'/p.name]=p
        for name in ['player-imports.json','player-import-validation.json']:payloads[S/'gamedata'/name]=R/'built'/name
        source=(S/'patches/native_roster_preflight.py').read_text('utf8').replace('native-roster','player-import').replace('native_roster_preflight.py','player_import_preflight.py').replace('NATIVE_ROSTER','PLAYER_IMPORT').replace('Native-Roster','Player-Import')
        source=source.replace("('client','data/data_6.big')}","('client','data/data_6.big'),('server','tools/player_import/check.py'),('server','gamedata/player-imports.json'),('server','gamedata/player-import-validation.json')}")
        assert 'tools/player_import/check.py' in source;compile(source,SELF,'exec')
        newplay=oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode());lines=newplay.splitlines(keepends=True);anchor=next(line for line in lines if b' -File patches\\install-zh.ps1' in line)
        checkline=b'.venv\\Scripts\\python.exe tools\\player_import\\check.py\nif errorlevel 1 (\n pause\n exit /b 1\n)\n'
        assert b'tools\\player_import\\check.py' not in newplay;newplay=newplay.replace(anchor,checkline+anchor)
        instructions=('\n\n## 新球员导入强制检查\n\n'
          '- 修改/新增球员、赛季或模型前，先读 `tools/player_import/README.md`。UI SQLite、六语言姓名和原生 EA players 必须一起核对；原生主键是 playerid，不是 SPID。禁止用空训练表、删除卡或换成他人模型规避错误。\n'
          '- 新导入专属资源使用 `tools/player_import/prepare.py` 完成原生记录/骨骼/五件套与路由，再以 `check.py --full` 校验。来源星数必须显式转 FO3 0..4，不猜测；未知 rig、缺资源、缺原生记录、选择器冲突、未登记的新身份直接拒绝。\n'
          '- 保留 play-local.bat 的独立 player_import 检查行。更新导入数据时，正式文件的完整校验证书须随新子层一起登记；继承所有父 guards/receipt policies，不能改旧哈希或绕过检查。资产保护及游戏退出时机继续按上文执行。\n'
          '- 静态/接口通过不能当实机/比赛通过；记录每个球员的验证范围，原生失败样本与本故障经验必须回填同一账本。\n')
        agent=S/'AGENTS.md';assert '## 新球员导入强制检查' not in agent.read_text('utf8')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-001 全量修复与导入防回归（'+revision+'）：\n'
          '人类已确认 native-roster-20261107-013154 贝林首页正常显示并能带球，独立证据new-player-models/home-black-screen/native-roster/human-home-validation.json；未声称比赛通过。用户进一步要求覆盖其它新球员并沉淀经验。\n'
          '全量632自定义卡/446身份核对：原生还缺11身份（8个现代新面孔+Beckham250/Carragher5467/Cantona167198），故不是全员必崩，但这些缺项确实会走同一危险训练表fallback。正式EA players新增11条至62093；19个已登记专属面孔统一绑定本人assetID/class0/type1023；原生新记录逐字段偏移、浮点、日期、位宽、CRC/行数检查；Cantona仅引擎基底potential按schema99，UI卡118保留。其余非目标旧记录和全部其它EA表字节保持。\n'
          '18套余下导入模型255→252逐名/作者别名retarget，57个网格逐项范围/权重和remap/索引/有限数值检查；贝林已通过的3个网格字节保持。新换54个网格只改bindings/skin/remap，不改脸型/发型/位置/法线/UV/三角/贴图和内层offset。完整19套五件套都有明确回执，未知rig和加权骨骼拒绝。\n'
          '另确认旧build24/build_bulk_seasons直接把HTML★数写skillmoves，未转FO3 0..4；按原始hash绑定的官方快照修正255张FC卡的星数编码，主库其它字段保持。另修Beckham4条UI记录的已有preset1505类别0→1，实际资源只有head_1505_1，保留同一已配置脸型，不替换为其它人。合计259目标行，其它表/行/字段逐项EXCEPT/精确delta证明；server/client主库加密回读一致，六语言库原字节保持。历史Pogba48继承91195864的5原值无FC星数来源，不猜测下调，以显式历史例外保留。\n'
          '新增tools/player_import/{prepare.py,check.py,native_db.py,rx3.py,ordered_big.py,rig-map.json,README.md}、gamedata/player-imports.json及语义证书，play每次启动先独立检查。覆盖双端库、原生身份/新增row回执、六语言姓名、登记资源/来源星数单位/选择器和Lua路由；证书绑定全部输入和checker SHA，变化后不能复用；新身份未知来源/缺五件套/错rig/错palette/错CRC拒绝。server AGENTS增加强制流程，工作区AGENTS同样补充链接。\n'
          '验证：18套转换和所有非目标压缩payload逐字节保持，data0只改两个DB成员、目录有序；11项有界格式/错误骨骼/坏CRC/缺字段/新BIG成员/I-O拒绝回归PASS；旧正式输入作为失败控制稳定被新检查拒绝缺原生记录及255骨骼，修复输入632/446/19及六语言66280行FULL_PASS。未写任何fixture到真实state/shop，没有新增测试经理或卡。两张既存曼联卡48000249/48000245缺头像来源、官方CDN403，显式旧缺项保留默认头像，不伪称已补真人图片，不允许新导入使用此例外。\n'
          '正式发布继承当前最新父层，保留其它聊天曼联筛选/名称/HTTPS和费率等改动；共同双锁、正常游戏关闭、停受管服务fresh资产快照、备份、CAS原子替换、play最后、只回退自己后版本、Hidden恢复服务。历史回执不改、不恢复旧state/shop。\n'
          '工作证据D:/fifaol3/new-player-models/bulk-repair/{current-audit.json,missing-and-meshes.json,built/build.json,built/mesh-conversions.json,built/native-changes.json,tool-tests.json,original-rejection.json,installed.json}。正式验证命令.venv/Scripts/python.exe -B tools/player_import/check.py --full、patches/player_import_preflight.py；check_data0_layout与本次备份比较只允许两个DB成员变化。原生其它球员/近远景/比赛仍待逐项验收，不能从贝林推定全员。\n')
        small={S/SELF:source.encode('utf8'),play:newplay,agent:agent.read_bytes()+instructions.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8')}
        for i,(p,b) in enumerate(small.items()):q=work/('small-'+str(i));q.write_bytes(b);payloads[p]=q
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,q in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert tx.sha(p)==guards[key]['sha256'],'Registered target drift '+str(p)
            elif p.exists():assert p==agent,'Unexpected existing unregistered target '+str(p)
            guards[key]=dict(root=root,relative=rel,sha256=tx.sha(q))
        composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='player-import',native_scope='Bellingham home HUMAN_CONFIRMED; others PENDING'))
        parentreceipt=json.loads((S/parent.RECEIPT).read_text('utf8'));composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in parentreceipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel))
        extra={S/MANIFEST:tx.encoded(manifest),S/RECEIPT:tx.encoded(dict(status='INSTALLED_PLAYER_IMPORT',manifest_sha256=tx.digest(tx.encoded(manifest)),revision=revision,state_shop_replaced=False,native_status='PENDING'))}
        for p,b in extra.items():assert not p.exists();q=work/p.name;q.write_bytes(b);payloads[p]=q
        before={p:tx.sha(p) if p.exists() else None for p in payloads};after={p:tx.sha(q) for p,q in payloads.items()};backup=S/'backups'/revision;backup.mkdir();saved={}
        for i,p in enumerate(payloads):
            if before[p] is not None:q=backup/(str(i)+'-'+p.name);shutil.copyfile(p,q);assert tx.sha(q)==before[p];saved[p]=q
        (backup/'before.json').write_bytes(tx.encoded({str(p):v for p,v in before.items()}));staged={};committed=[];was_running=listening(443);stopped=False
        try:
            for p,q in payloads.items():p.parent.mkdir(parents=True,exist_ok=True);staged[p]=stage(p,q)
            tx.closed();parent.preflight(S,C)
            if was_running:stopped=True;stop()
            state=(S/'gamedata/state.json').read_bytes();shop=(S/'gamedata/shop.json').read_bytes();(backup/'state-stop-observed-readonly.json').write_bytes(state);(backup/'shop-stop-observed-readonly.json').write_bytes(shop)
            protected={str(p):tx.sha(p) for p in [S/'http_config.py',S/'gamedata/custom_rosters.json',C/'data/ui/libs/Module.big',C/'data/data_3.big',S/'gamedata/pack_cadence.json',S/'gamedata/pack_catalogue.json']}
            for p in [p for p in payloads if p!=play]+[play]:
                tx.closed();assert (tx.sha(p) if p.exists() else None)==before[p],'Concurrent target changed '+str(p);os.replace(staged[p],p);committed.append(p)
            result=tx.load(S/SELF,'complete_player_installed').preflight(S,C)
            validation=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py'),'--full'],cwd=S,capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);semantic=json.loads(validation.stdout)
            assert semantic['status']=='PLAYER_IMPORT_FULL_PASS'
            assert (S/'gamedata/state.json').read_bytes()==state and (S/'gamedata/shop.json').read_bytes()==shop
            assert all(tx.sha(p)==h for p,h in protected.items())
        except BaseException:
            for p in reversed(committed):
                if tx.sha(p)!=after[p]:raise RuntimeError('Later edit retained; rollback refused '+str(p))
                if before[p] is None:p.unlink()
                else:os.replace(stage(p,saved[p]),p)
            raise
        finally:
            for q in staged.values():q.unlink(missing_ok=True)
            if stopped:start()
        current=json.loads((S/'gamedata/state.json').read_bytes());old=json.loads(state);nonmarket=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
        report=dict(status='INSTALLED_PLAYER_IMPORT_STATIC_PASS_NATIVE_PARTIAL',revision=revision,parent=parentrel,backup=str(backup),preflight=result,semantic={k:v for k,v in semantic.items() if k not in ['input_hashes','portrait_hashes']},top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
          hashes={str(p):tx.sha(p) for p in [S/SELF,S/MANIFEST,S/RECEIPT,play]+[pathlib.Path(f['target']) for f in buildfiles]},protected=protected,state_shop_written=False,coaches_equal=old.get('coaches')==current.get('coaches'),teams_equal=old.get('teams')==current.get('teams'),nonmarket_state_equal=nonmarket(old)==nonmarket(current),shop_unchanged=(S/'gamedata/shop.json').read_bytes()==shop,services_restarted=stopped,services_restored=all(listening(p) for p in [443,8088,28002]),gui_used=False,native_home_verified=[252371],other_players_native_verified=False,match_verified=False)
        (R/'installed.json').write_bytes(tx.encoded(report));tx.atomic(pathlib.Path('D:/fifaol3/root-current-top.json'),tx.encoded(dict(status=report['status'],observed_at=datetime.datetime.now().isoformat(),top_preflight=report['top_preflight'],top_manifest=report['top_manifest'],top_receipt=report['top_receipt'],files=report['hashes'],composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),handoff=str(R/'installed.json'),preflight=result,state_shop_written=False,services_restored=report['services_restored'],native_verified=False,match_verified=False)))
        print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
