"""Client-only three-way pack controls, current-parent CAS transaction, no service actions."""
from pathlib import Path
import copy, datetime, hashlib, importlib.util, json, re, subprocess, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
CLIENT = Path(r'D:\FO3ID\32795')
sys.path[:0] = [str(SERVER), str(ROOT.parent)]
import install_bulk_seasons as tx
from hot_update_release import locks

def read(path):
    return json.loads(Path(path).read_text('utf8'))

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def closed():
    output=subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace')
    if 'fifazf.exe' in output.lower():
        raise RuntimeError('更新已延后，当前游戏继续运行')

def check_payloads(build):
    assert read(ROOT/'client/client-tests.json')['status']=='PASS'
    fonts=read(ROOT/'client/stacks-fonts.json')
    assert fonts['status']=='PASS'
    for row in build['files']:
        assert row['root']=='client' and row['relative']=='data/ui/TeamManagementPlayerCardScreen.big'
        assert tx.sha(row['source'])==row['after']
        assert tx.sha(CLIENT/row['relative'])==row['before'],'Client changed; rebuild from current file'
    for absolute,expected in fonts.get('dependencies',{}).items():
        assert tx.sha(absolute)==expected,'Client dependency changed'
    return fonts

def install(build):
    # Before locks, backups, staging metadata or any other formal write.
    closed()
    fonts=check_payloads(build)
    with locks(SERVER,'random-pack-dual-client'):
        closed()
        coord=read(ROOT.parent/'coordination-current.json')
        assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None
        play=(SERVER/'play-local.bat').read_bytes()
        matches=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play)
        assert len(matches)==1 and b'tools\\player_import\\check.py' in play
        parent_rel=matches[0].decode().replace('\\','/')
        parent=load(SERVER/parent_rel,'pack_dual_parent')
        prior=parent.preflight(SERVER,CLIENT)
        composition=copy.deepcopy(parent.compose_manifest(SERVER,CLIENT))
        guards={(row['root'],row['relative'].replace('\\','/').casefold()):copy.deepcopy(row) for row in composition['guards']}
        assert len(guards)==len(composition['guards'])
        revision='random-pack-dual-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        helper='patches/'+revision.replace('-','_')+'_preflight.py'
        manifest='patches/'+revision+'-installed.json'
        receipt='patches/'+revision+'-receipt.json'
        old_receipt=read(SERVER/parent.RECEIPT)
        code=(SERVER/parent_rel).read_text('utf8')
        for old,new in [(parent.SELF,helper),(parent.MANIFEST,manifest),(parent.RECEIPT,receipt),
                        (old_receipt['status'],'INSTALLED_RANDOM_PACK_DUAL'),(prior['status'],'RANDOM_PACK_DUAL_PREFLIGHT_PASS')]:
            code=code.replace(old,new)
        needle=' if not required<=seen:'
        assert code.count(needle)==1
        required={('server',helper.casefold()),('client','data/ui/teammanagementplayercardscreen.big')}
        code=code.replace(needle,' required.update('+repr(required)+')\n'+needle)
        compile(code,helper,'exec')
        staged=ROOT/'install-staging'/revision
        staged.mkdir(parents=True)
        entries=[]
        def entry(root,relative,data,guarded=True):
            target=(SERVER if root=='server' else CLIENT)/relative
            before=tx.digest(target)
            source=staged/(str(len(entries))+'.payload')
            source.write_bytes(data)
            after=tx.sha(source)
            key=(root,relative.casefold())
            if guarded:
                if key in guards: assert guards[key]['sha256']==before,('Guard drift',relative)
                else: assert before is None,('Unregistered target',relative)
                guards[key]=dict(root=root,relative=relative,sha256=after)
            entries.append(dict(root=root,relative=relative,source=str(source),parent_sha256=before,sha256=after))
        for row in build['files']:
            assert tx.sha(CLIENT/row['relative'])==row['before']
            entry(row['root'],row['relative'],Path(row['source']).read_bytes())
        for absolute,expected in fonts.get('dependencies',{}).items():
            relative=Path(absolute).relative_to(CLIENT).as_posix()
            assert tx.sha(absolute)==expected
            key=('client',relative.casefold())
            if key in guards: assert guards[key]['sha256']==expected
            guards[key]=dict(root='client',relative=relative,sha256=expected)
        entry('server',helper,code.encode('utf8'))
        doc='docs/工程经验与修改边界.txt'
        addition=('\r\n\r\nFO3-RANDOM-PACK-DUAL-001（2026-11-07）\r\n'
                  '随机球员包保留单张开启、原生连续逐张翻开，并单列一键全开。原生连续翻开方法按已绑定历史基线仅恢复目标方法，不回滚整个BIG；批量请求/回执/集中滚动结果展示及服务端全部热业务不变。'
                  '自选包/draft沿原逻辑，按钮按库存/球队空位与忙状态控制；客户端资源必须在游戏关闭且共同双锁空闲时fresh最新父层、完整guards/policies、备份/CAS安装，不启停服务、不写state/shop。'
                  '字节码定向回归、栈流和中文字形证据见D:/fifaol3/random-pack-dual/client；未操作游戏GUI，实机显示待验收。\r\n')
        entry('server',doc,(SERVER/doc).read_bytes()+addition.encode('utf8'))
        entry('server','play-local.bat',play.replace(matches[0],helper.replace('/','\\').encode()))
        composition.update(guards=list(guards.values()),files_verified=False)
        composition.setdefault('ancestry',[]).append(dict(layer='random-pack-dual',native_status='PENDING'))
        policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'})
        if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in composition.setdefault('receipt_policies',[])):
            composition['receipt_policies'].append(policy)
        m=dict(schema=1,revision=revision,client=str(CLIENT),state_shop_replaced=False,
               guards=composition['guards'],composition=composition,parent_preflight=parent_rel)
        mb=encoded(m)
        rb=encoded(dict(status='INSTALLED_RANDOM_PACK_DUAL',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
        entry('server',manifest,mb,False)
        entry('server',receipt,rb,False)
        entries.sort(key=lambda row:row['relative']=='play-local.bat')
        frozen={p:tx.sha(SERVER/p) for p in (parent_rel,parent.MANIFEST,parent.RECEIPT,'hot_updates/active.json')}
        def validate():
            closed()
            assert all(tx.sha(SERVER/p)==sha for p,sha in frozen.items()),'Parent or business changed; fresh before install'
            parent.preflight(SERVER,CLIENT)
            check_payloads(build)
        validate()
        backup=SERVER/'backups'/revision
        backup.mkdir()
        for name in ('state.json','shop.json'):
            (backup/('audit-'+name)).write_bytes((SERVER/'gamedata'/name).read_bytes())
        transaction=tx.commit_transaction({'server':SERVER,'client':CLIENT},entries,backup,validate)
        try:
            proof=load(SERVER/helper,'pack_dual_installed').preflight(SERVER,CLIENT)
            subprocess.run([str(SERVER/'.venv/Scripts/python.exe'),'-B',str(SERVER/'tools/player_import/check.py')],cwd=SERVER,check=True,capture_output=True)
            assert tx.sha(SERVER/'hot_updates/active.json')==frozen['hot_updates/active.json']
        except BaseException:
            tx.restore_completed({'server':SERVER,'client':CLIENT},transaction,backup)
            raise
        transaction['status']='installed'
        tx.atomic_json(backup/'transaction.json',transaction)
        result=dict(status='INSTALLED_CLIENT_RESOURCES_NATIVE_PENDING',revision=revision,preflight=proof,
                    backup=str(backup),top_preflight=str(SERVER/helper),top_manifest=str(SERVER/manifest),top_receipt=str(SERVER/receipt),
                    composition_api='compose_manifest(server=None,client=None)',
                    files={str(SERVER/p):tx.sha(SERVER/p) for p in (helper,manifest,receipt,'play-local.bat')},
                    state_shop_written=False,hot_business_unchanged=True,services_action='No service start/stop/restart',
                    player_import_check='PASS',native_verified=False)
        tx.atomic_json(ROOT/'installed-handback.json',result)
        tx.atomic_json(ROOT.parent/'root-current-top.json',result)
        return result

if __name__=='__main__':
    try:
        build=read(ROOT/'client/install-build.json')
        print(json.dumps(install(build),ensure_ascii=False))
    except RuntimeError as exc:
        if str(exc)!='更新已延后，当前游戏继续运行': raise
        result=dict(status='DEFERRED_GAME_RUNNING',message=str(exc),formal_files_written=False,service_actions=False)
        (ROOT/'deferred.json').write_bytes(encoded(result))
        print(json.dumps(result,ensure_ascii=False))
