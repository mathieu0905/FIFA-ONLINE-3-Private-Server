"""Prepare one-click save on current source; no production writes."""
from pathlib import Path
import hashlib,json
S=Path('D:/FO3ID/server');OUT=Path(__file__).parent/'pending-direct-save';OUT.mkdir(exist_ok=True)
sources=['player_editor/__init__.py','player_editor/player_database.py','player_editor/index.html','player_editor/publish_database.py','player_editor/database_preflight.py']
snapshot={rel:hashlib.sha256((S/rel).read_bytes()).hexdigest() for rel in sources}
py=(S/sources[1]).read_text('utf-8')
start=py.index('    def queue(self, p):');end=py.index('    def publish(self, p):',start)
py=py[:start]+'''    def save(self, p):
        with self.lock:
            if self.building:
                raise ValueError('正在保存，请等待完成')
            publisher = module(HERE / 'publish_database.py', 'direct_save_gate')
            publisher.game_closed()
            d = self.draft()
            if p.get('revision') != d['revision']:
                raise ValueError('修改记录已变化，请刷新后重试')
            if p.get('changes'):
                d = self.stage(p)['draft']
            if not d['cards']:
                raise ValueError('没有需要保存的修改')
            # Reuse the user's already generated file when its exact cells and baseline still match.
            for path in sorted((self.work / 'jobs').glob('*.json'), reverse=True):
                record = read(path)
                if record.get('status') not in ('built', 'apply_failed'):
                    continue
                candidate = Path(record['candidate'])
                m = read(candidate / 'manifest.json')
                same_changes = sorted(m['changes'], key=lambda r:r['spid']) == sorted(d['cards'].values(), key=lambda r:r['spid'])
                if same_changes and sha(self.db) == m['source_hashes']['database'] and sha(self.client / 'data/data_0.big') == m['source_hashes']['client']:
                    return self.publish(dict(id=record['id'], manifest_sha256=record['manifest_sha256']))
            return self.queue(dict(revision=d['revision'], auto_apply=True))

    def queue(self, p):
        with self.lock:
            if self.building:
                raise ValueError('正在保存，请等待完成')
            d = self.draft()
            if p.get('revision') != d['revision'] or not d['cards']:
                raise ValueError('修改为空或已变化，请刷新')
            job = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
            record = dict(id=job, status='building', cards=len(d['cards']), revision=d['revision'], auto_apply=p.get('auto_apply') is True)
            path = self.work / 'jobs' / (job + '.json')
            write(path, record)
            self.building = True
            def run():
                try:
                    out = self.work / 'builds' / job
                    m = self.build(d, out)
                    record.update(status='built', candidate=str(out), manifest_sha256=sha(out / 'manifest.json'), changed_cards=len(m['changes']))
                    with self.lock:
                        write(path, record)
                        self.building = False
                        if record['auto_apply']:
                            self.publish(dict(id=job, manifest_sha256=record['manifest_sha256']))
                except Exception as e:
                    record.update(status='failed', error=str(e))
                    write(path, record)
                    with self.lock:
                        self.building = False
            threading.Thread(target=run, daemon=True).start()
            return record

'''+py[end:]
(OUT/'player_database.py').write_text(py,'utf-8')
init=(S/sources[0]).read_text('utf-8').replace("'build', 'publish')", "'build', 'publish', 'save')")
(OUT/'__init__.py').write_text(init,'utf-8')
ui=(S/sources[2]).read_text('utf-8')
ui=ui.replace('流程：搜索球员 → 暂存修改 → 核对差异 → 生成双端数据库 → 正式应用。暂存和生成不会改变游戏数据；正式应用会备份并同步服务端和客户端，服务会短暂重启，需先退出游戏。','修改球员后点击“保存并应用”即可。请先退出游戏，保存完成后重新启动游戏生效。')
ui=ui.replace('暂存修改</button>','保存并应用</button>').replace('待应用的全局修改','尚未完成的修改').replace('生成双端数据库</button>','保存并应用这些修改</button>')
ui=ui.replace('构建与应用记录','保存记录').replace('构建会检查 SQLite 完整性、客户端加解密回读、BIG 成员顺序以及所有非目标数据。正式应用前再次检查当前版本，发现并发修改会拒绝覆盖。','保存会自动同步游戏数据并保留备份，无需再次点击应用。')
ui=ui.replace("let r=await api('stage',", "let r=await api('save',")
ui=ui.replace('message(`已暂存 ${r.affected} 张卡，尚未修改正式数据库。`)', "message('正在保存并同步游戏数据，完成后会自动显示结果。')")
start=ui.index("$('#build').onclick=");end=ui.index("$('#jobs').onclick",start)
ui=ui[:start]+"$('#build').onclick=()=>action(async()=>{await api('save',{revision:state.draft.revision});await refresh();message('正在保存并同步游戏数据，完成后会自动显示结果。')});\n"+ui[end:]
ui=ui.replace("building:'正在生成',built:'双端数据库已生成，待应用',failed:'生成失败',applying:'正在应用',installed:'已应用，实机待验证',apply_failed:'应用失败'", "building:'正在保存：同步游戏资源',built:'尚未应用',failed:'保存失败',applying:'正在保存：写入数据',installed:'已保存并应用，重新启动游戏生效',apply_failed:'保存失败'")
ui=ui.replace('还没有构建记录','还没有保存记录').replace('构建目录与校验值','备份与处理详情')
ui=ui.replace("if(!busy)refresh().catch(e=>message(e.message,true))", "if(!busy)refresh().then(()=>{const j=state.jobs[0];if(j?.status==='installed')message('已保存并应用，重新启动游戏即可生效。');else if(j?.status==='failed'||j?.status==='apply_failed')message('保存失败：'+j.error,true)}).catch(e=>message('服务正在重启，正在等待保存结果…'))")
(OUT/'index.html').write_text(ui,'utf-8')
(OUT/'check.js').write_text(ui.split('<script>')[1].split('</script>')[0],'utf-8')
# Preserve the current parent composition so future releases can compose over saved player data.
gate=(S/sources[4]).read_text('utf-8')
gate=gate.replace('import hashlib,json','import hashlib,json\nMANIFEST="patches/player-database-installed.json"\nRECEIPT="patches/player-database-receipt.json"\nSELF="patches/player_database_preflight.py"')
gate=gate.replace("    if m.get('schema')", "    receipt=json.loads((server/RECEIPT).read_text('utf-8'))\n    if receipt.get('status')!='INSTALLED_PLAYER_DATABASE' or receipt.get('manifest_sha256')!=sha(server/MANIFEST) or receipt.get('revision')!=m['revision']:raise RuntimeError('Database receipt mismatch')\n    if m.get('schema')")
gate=gate.replace("    return dict(status='PLAYER_DATABASE_PREFLIGHT_PASS'", "    for policy in m.get('composition',{}).get('receipt_policies',[]):\n        root=roots[policy['root']];path=(root/policy['relative']).resolve()\n        if not path.is_relative_to(root):raise RuntimeError('Receipt path escape')\n        receipt=json.loads(path.read_text('utf-8-sig'))\n        if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')\n    return dict(status='PLAYER_DATABASE_PREFLIGHT_PASS'")
gate += '''
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/'patches/player-database-installed.json').read_text('utf-8'))
    c=dict(m.get('composition') or {})
    guards=list(m['guards'])
    for name in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=name,sha256=sha(server/name)))
    c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards)
    c.setdefault('ancestry',[])
    c.setdefault('receipt_policies',[])
    return c
'''
(OUT/'database_preflight.py').write_text(gate,'utf-8')
pub=(S/sources[3]).read_text('utf-8')
pub=pub.replace("    try:\n        os.write(descriptor,str(os.getpid()).encode());os.close(descriptor)\n        return _apply(candidate,expected_sha,manage_services)\n    finally:\n        lock.unlink(missing_ok=True)", "    os.write(descriptor,str(os.getpid()).encode());os.close(descriptor)\n    release_lock=Path(m['server'])/'.shop-release.lock'\n    release_descriptor=None\n    try:\n        try:release_descriptor=os.open(release_lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)\n        except FileExistsError:raise RuntimeError('另一个更新正在应用，请稍后重试保存')\n        return _apply(candidate,expected_sha,manage_services)\n    finally:\n        if release_descriptor is not None:\n            os.close(release_descriptor);release_lock.unlink(missing_ok=True)\n        lock.unlink(missing_ok=True)")
pub=pub.replace("    check_sources();guards=baseline(server,client);game_closed();was_running=listening(443)", "    check_sources();guards=baseline(server,client)\n    import re\n    entry=re.findall(r'patches[\\\\/][a-z_]+_preflight\\.py',(server/'play-local.bat').read_text('utf-8-sig'))\n    if len(entry)!=1:raise RuntimeError('未知启动检查器')\n    parent=module(server/entry[0].replace('\\\\','/'),'save_composition_parent')\n    composition=parent.compose_manifest(server,client)\n    game_closed();was_running=listening(443)")
pub=pub.replace("installed=dict(schema=1,revision=revision,client=str(client),guards=list(table.values()),state_shop_replaced=False,native_status='PENDING',candidate_manifest_sha256=expected_sha)", "composition['guards']=list(table.values())\n        installed=dict(schema=1,revision=revision,client=str(client),guards=list(table.values()),composition=composition,state_shop_replaced=False,native_status='PENDING',candidate_manifest_sha256=expected_sha)")
pub=pub.replace("        composition['guards']=list(table.values())", "        for name in ('patches/player-database-installed.json','patches/player-database-receipt.json'):table.pop(('server',name),None)\n        composition['guards']=list(table.values())")
pub=pub.replace("write(stage/'player-database-installed.json',installed);pairs += [(stage/'player-database-installed.json',server/'patches/player-database-installed.json')]", "write(stage/'player-database-installed.json',installed);pairs += [(stage/'player-database-installed.json',server/'patches/player-database-installed.json')]\n        write(stage/'player-database-receipt.json',dict(status='INSTALLED_PLAYER_DATABASE',manifest_sha256=sha(stage/'player-database-installed.json'),revision=revision,state_shop_replaced=False))\n        pairs += [(stage/'player-database-receipt.json',server/'patches/player-database-receipt.json')]")
(OUT/'publish_database.py').write_text(pub,'utf-8')
(OUT/'source-hashes.json').write_text(json.dumps(snapshot,indent=2),'utf-8')
print(OUT)
