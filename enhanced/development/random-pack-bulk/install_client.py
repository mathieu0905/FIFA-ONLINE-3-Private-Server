"""Install current-baseline client resources only while the game is closed, no restarts."""
from pathlib import Path
import copy, datetime, hashlib, importlib.util, json, re, subprocess, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
CLIENT = Path(r'D:\FO3ID\32795')
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(ROOT.parent))
import install_bulk_seasons as tx
from hot_update_release import locks

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def closed():
    result = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq fifazf.exe', '/FO', 'CSV', '/NH'], text=True, errors='replace')
    if 'fifazf.exe' in result.lower():
        raise RuntimeError('更新已延后，当前游戏继续运行')

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf8')

def install(build):
    closed()  # Before every formal write, including locks and backups.
    tests = json.loads((ROOT/'server-tests.json').read_text('utf8'))
    assert tests['status'] == 'PASS' and tests['source_sha256'] == tx.sha(ROOT/'bulk_business.py')
    assert json.loads((ROOT/'client'/'client-tests.json').read_text('utf8'))['status'] == 'PASS'
    font_proof = json.loads((ROOT/'client'/'stacks-fonts.json').read_text('utf8'))
    assert font_proof['status'] == 'PASS'
    contract = json.loads((ROOT/'client'/'player-list-contract.json').read_text('utf8'))
    assert contract['status'] == 'PASS' and contract['requires_expandme'] is False
    with locks(SERVER, 'random-pack-bulk-client'):
        closed()
        active = json.loads((SERVER/'hot_updates/active.json').read_text('utf8'))
        hot = json.loads((ROOT/'hot-installed.json').read_text('utf8'))
        assert active['revision'] == hot['revision'], 'Bulk business must be activated before client installation'
        coord = json.loads((ROOT.parent/'coordination-current.json').read_text('utf8'))
        assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
        play = (SERVER/'play-local.bat').read_bytes()
        match = re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py', play)
        assert len(match) == 1 and b'tools\\player_import\\check.py' in play
        parent_rel = match[0].decode().replace('\\', '/')
        parent = load(SERVER/parent_rel, 'bulk_client_parent')
        prior = parent.preflight(SERVER, CLIENT)
        composition = copy.deepcopy(parent.compose_manifest(SERVER, CLIENT))
        guards = {(g['root'], g['relative'].replace('\\','/').casefold()): copy.deepcopy(g) for g in composition['guards']}
        assert len(guards) == len(composition['guards'])
        revision = 'random-pack-bulk-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        helper = 'patches/'+revision.replace('-','_')+'_preflight.py'
        manifest = 'patches/'+revision+'-installed.json'
        receipt = 'patches/'+revision+'-receipt.json'
        old_receipt = json.loads((SERVER/parent.RECEIPT).read_text('utf8'))
        code = (SERVER/parent_rel).read_text('utf8')
        for old, new in [(parent.SELF,helper), (parent.MANIFEST,manifest), (parent.RECEIPT,receipt),
                         (old_receipt['status'],'INSTALLED_RANDOM_PACK_BULK'), (prior['status'],'RANDOM_PACK_BULK_PREFLIGHT_PASS')]:
            code = code.replace(old,new)
        required = {(row['root'],row['relative'].casefold()) for row in build['files']}
        required.add(('server',helper.casefold()))
        needle = ' if not required<=seen:'
        assert code.count(needle) == 1
        code = code.replace(needle, ' required.update('+repr(required)+')\n'+needle)
        compile(code,helper,'exec')
        staged = ROOT/'install-staging'/revision
        entries = []
        def entry(root, relative, source, guarded=True, pinned_existing=False):
            target = (SERVER if root == 'server' else CLIENT)/relative
            before = tx.digest(target)
            after = tx.sha(source)
            key = (root, relative.casefold())
            if guarded:
                if key in guards:
                    assert guards[key]['sha256'] == before, ('Guard baseline drift',relative)
                else:
                    assert before is None or pinned_existing, ('Unregistered existing target',relative)
                guards[key] = dict(root=root, relative=relative, sha256=after)
            entries.append(dict(root=root,relative=relative,source=str(source),parent_sha256=before,sha256=after))
        for row in build['files']:
            target = (SERVER if row['root']=='server' else CLIENT)/row['relative']
            assert tx.digest(target) == row['before'], ('Rebuild latest client',str(target))
            assert tx.sha(row['source']) == row['after']
            entry(row['root'],row['relative'],Path(row['source']),pinned_existing=True)
        dependencies = dict(font_proof['dependencies'])
        dependencies[contract['module_path']] = contract['module_sha256']
        for absolute, expected in dependencies.items():
            path = Path(absolute)
            relative = path.relative_to(CLIENT).as_posix()
            assert tx.sha(path) == expected, 'Client font dependency changed'
            key = ('client',relative.casefold())
            if key in guards:
                assert guards[key]['sha256'] == expected
            guards[key] = dict(root='client',relative=relative,sha256=expected)
        entry('server',helper,write(staged/'preflight.py',code.encode('utf8')))
        entry('server','play-local.bat',write(staged/'play-local.bat',play.replace(match[0],helper.replace('/','\\').encode())))
        doc = 'docs/工程经验与修改边界.txt'
        addition = ('\r\n\r\nFO3-RANDOM-PACK-BULK-001（2026-11-07）\r\n'
                    '同类型随机球员包一键全开，以同itemid背包数量和实际球员空位取最小值；不动仓库、自选包及单开流程。'
                    '一次STATE_LOCK/原子_save提交发卡、扣包、原概率/保底/积分兑换及经理绑定防重回执。客户端复用原生滚动球员结果列表一次展示全部结果。'
                    '业务使用ABI2模板热更新，不reload模块/不重启服务。客户端仅在游戏关闭时备份/CAS安装。'
                    '临时存档回归与BIG/ABC静态检查见D:/fifaol3/random-pack-bulk；未写真实测试资产，未操作游戏GUI，实机显示和比赛待验收。\r\n')
        entry('server',doc,write(staged/'engineering.txt',(SERVER/doc).read_bytes()+addition.encode('utf8')))
        composition.update(guards=list(guards.values()),files_verified=False)
        composition.setdefault('ancestry',[]).append(dict(layer='random-pack-bulk',native_status='PENDING'))
        policy = dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'})
        if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in composition.setdefault('receipt_policies',[])):
            composition['receipt_policies'].append(policy)
        m = dict(schema=1,revision=revision,client=str(CLIENT),state_shop_replaced=False,
                 guards=composition['guards'],composition=composition,parent_preflight=parent_rel)
        mb = encoded(m)
        rb = encoded(dict(status='INSTALLED_RANDOM_PACK_BULK',revision=revision,
                          manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
        entry('server',manifest,write(staged/'manifest.json',mb),False)
        entry('server',receipt,write(staged/'receipt.json',rb),False)
        entries.sort(key=lambda row: row['relative']=='play-local.bat')
        baseline = {p:tx.sha(SERVER/p) for p in (parent_rel,parent.MANIFEST,parent.RECEIPT)}
        def validate():
            closed()
            assert all(tx.sha(SERVER/p)==sha for p,sha in baseline.items())
            parent.preflight(SERVER,CLIENT)
        validate()
        backup = SERVER/'backups'/revision
        backup.mkdir()
        # Audit snapshot only; live state is never restored or used as an install payload.
        protected = {n:tx.sha(SERVER/'gamedata'/n) for n in ('state.json','shop.json')}
        for n in protected:
            (backup/('audit-'+n)).write_bytes((SERVER/'gamedata'/n).read_bytes())
        transaction = tx.commit_transaction({'server':SERVER,'client':CLIENT},entries,backup,validate)
        try:
            proof = load(SERVER/helper,'bulk_client_installed').preflight(SERVER,CLIENT)
            subprocess.run([str(SERVER/'.venv/Scripts/python.exe'),'-B',str(SERVER/'tools/player_import/check.py')],cwd=SERVER,check=True,capture_output=True)
        except BaseException:
            tx.restore_completed({'server':SERVER,'client':CLIENT},transaction,backup)
            raise
        transaction['status']='installed'
        tx.atomic_json(backup/'transaction.json',transaction)
        result = dict(status='INSTALLED_CLIENT_RESOURCES',revision=revision,preflight=proof,
                      backup=str(backup),top_preflight=str(SERVER/helper),top_manifest=str(SERVER/manifest),
                      top_receipt=str(SERVER/receipt),composition_api='compose_manifest(server=None,client=None)',
                      files={str(SERVER/p):tx.sha(SERVER/p) for p in (helper,manifest,receipt,'play-local.bat')},
                      state_shop_written=False,services_action='No service start/stop/restart',
                      player_import_check='PASS',native_verified=False,audit_before=protected)
        tx.atomic_json(ROOT/'installed-handback.json',result)
        tx.atomic_json(ROOT.parent/'root-current-top.json',result)
        return result

if __name__ == '__main__':
    try:
        build = json.loads((ROOT/'client'/'install-build.json').read_text('utf8'))
        print(json.dumps(install(build),ensure_ascii=False))
    except RuntimeError as exc:
        if str(exc) != '更新已延后，当前游戏继续运行': raise
        result = dict(status='DEFERRED_GAME_RUNNING',message=str(exc),formal_files_written=False,service_actions=False)
        (ROOT/'deferred.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False))
