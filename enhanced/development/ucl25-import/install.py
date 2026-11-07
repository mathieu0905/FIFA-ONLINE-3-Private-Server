"""Protected direct formal import, latest composition and own-file rollback only."""
from common import *
from transaction import *
import copy,sqlite3
from contextlib import closing
import ucl25_value_extension as extension

SELF='patches/ucl25_final_072_20261107_preflight.py'
MANIFEST='patches/ucl25-final-072-20261107-installed.json'
RECEIPT='patches/ucl25-final-072-20261107-receipt.json'
EVIDENCE='patches/ucl25-final-072-20261107-evidence.json.gz'
MODEL='gamedata/fair-value-25ucl-model.json'
CATALOGUE='gamedata/fair-value-25ucl-catalogue.json.gz'
DOC='docs/工程经验与修改边界.txt'


def expected_certificate(native):
    cert=read(native/'player-import-validation.json');new={p['source_spid'] for p in imported_cards()};hashes={}
    for path,value in cert['portrait_hashes'].items():
        p=Path(path)
        if p.parent.resolve()==(R/'portraits').resolve():
            sid=int(p.stem[1:]);assert sid in new
            for target in (C/'_cache/cdn/externalAssets/players'/p.name,C/'_cache/games/fo3id/externalAssets/players'/p.name,S/'assets/players'/p.name):hashes[str(target)]=value
        else:hashes[path]=value
    cert['portrait_hashes']=hashes
    return cert


def plan():
    assert_idle()
    coordination=read(R.parent/'coordination-current.json')
    if coordination.get('current_unhanded_writers') or coordination.get('next_formal_writer'):raise RuntimeError('Another formal writer owns the window; hand off first')
    out=Path(read(R/'latest-build.json')['path']);native=out/'native';tests=read(out/'tests.json');price_tests=read(out/'price-tests.json')
    assert tests['status']=='PASS' and price_tests['status']=='ADDITIVE_PRICE_REGRESSION_PASS'
    for name,digest0 in tests['tool_hashes'].items():
        if sha(R/name)!=digest0:raise RuntimeError('Validated import tooling changed: '+name)
    if tests['tool_hashes'].get('install.py')!=sha(Path(__file__)):raise RuntimeError('Installer must be included in latest whole-delta regression')
    for path,digest0 in read(out/'source-baseline.json').items():
        if sha(path)!=digest0:raise RuntimeError('Formal input advanced; refresh the affected build component: '+path)
    if sha(S/'patches/Label.big')!=sha(C/'data/ui/components/Label.big'):
        raise RuntimeError('Launcher Label source differs from current client; compose both changes before installing')
    for name,digest0 in tests['output_hashes'].items():assert sha(native/name)==digest0
    with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        meta=dict(db.execute('select key,value from metadata'))
    cat=extension.packet(out/'25ucl-value-catalogue.json.gz')
    if (meta['fair_revision'],meta['fair_model_sha256'])!=(cat['expected_previous_revision'],cat['expected_previous_model_sha256']):raise RuntimeError('Fair generation changed; rebase valuations')
    play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
    if len(matches)!=1:raise RuntimeError('Ambiguous actual launcher')
    parent_rel='patches/'+matches[0].decode();parent=load(S/parent_rel,'ucl25_fresh_parent')
    prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
    load(S/'patches/startup_market_preflight.py','ucl25_parent_verifier').verify_manifest(composition,S,C)
    guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in composition['guards']}
    oldreceipt=read(S/parent.RECEIPT);helper=(S/parent_rel).read_text('utf8')
    for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),
        (oldreceipt['status'],'INSTALLED_25UCL_FINAL_072'),(prior['status'],'25UCL_FINAL_072_PREFLIGHT_PASS')]:
        if old not in helper:raise RuntimeError('Parent preflight contract changed')
        helper=helper.replace(old,new)
    anchor=' return dict(nostalgia_fair_value='
    extra=(" spec=importlib.util.spec_from_file_location('_ucl25_value_check',server/'ucl25_value_extension.py');ucl25=importlib.util.module_from_spec(spec);spec.loader.exec_module(ucl25)\n"
        " ucl25.verify(server/'gamedata/npc-market-prices.sqlite',server/'"+CATALOGUE+"',server/'"+MODEL+"',server/'gamedata/fifadb.sqlite')\n")
    if helper.count(anchor)!=1:raise RuntimeError('Latest semantic verification anchor changed')
    helper=helper.replace(anchor,extra+anchor);compile(helper,SELF,'exec')
    revision='25ucl-final-072-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    certificate=expected_certificate(native)
    note=('\r\n\r\nFO3-25UCL-FINAL-072-20261107\r\n'
        '新增25UCL 360张；使用Nexon官方2026-11-07已计入最终现实表现的33项基础细项，统一乘0.72、四舍五入一次；总评按本服位置权重生成。'
        '星数显式1-5转FO3等级码0-4，逆足与主脚独立转换；身高/体重不缩放。旧卡属性/模型/强化曲线不变。'
        '普通卡额外奖励为0，不新增25U赛季专属能力奖励；未重复人工叠加冠军/亚军加成。\r\n'
        '保留已移除/屏蔽的姆巴佩，未导回该身份或历史卡。273人沿用现有原生身份（含121人跨来源编号对齐），87人使用登记的内置通用脸型，不冒称真人脸；'
        '保留原有所有UI/原生记录，新增身份按playerid唯一。六语言姓名/头像/注册表/卡框/市场筛选同步；新姓名使用官方拉丁名，原中文名保留。'
        '新增卡只映射FO3已存在的0-29号特性，其余FC新特性留证未伪造效果；无额外金标。\r\n'
        '市场估值复用现行模型参数，仅追加新卡；归档旧估值代际，保留所有已有价格、种子、交易回执及共同球员系数。'
        '保留已售通用卡包卡池与当前业务热包全部路由及定价；未发测试卡、未改真实余额/球队/阵容。'
        '游戏运行则延后，使用共同双锁、最新父层guards/receipt policies、备份/CAS、停服实时快照；player_import独立启动检查保留。'
        '静态/完整校验/接口通过不等于实机；首页、近远景、带球和比赛=PENDING。证据D:/fifaol3/ucl25-import/。\r\n')
    evidence=gzip.compress(encoded(dict(tests=tests,price_tests=price_tests,source=read(R/'source-ready.json'),
        display=read(out/'display/display-validation.json'),coordination='Coordinator chat archived; handoff attempt recorded locally; no other current writer in shared state.')),mtime=0)
    payloads=[]
    def add(root,rel,source):payloads.append((root,rel,source))
    for rel,name in [('gamedata/fifadb.sqlite','fifadb.sqlite'),('gamedata/custom_rosters.json','custom_rosters.json'),('gamedata/player-imports.json','player-imports.json')]:add('server',rel,native/name)
    add('client','data/data_0.big',native/'data_0.big')
    add('server','gamedata/player-import-validation.json',json.dumps(certificate,ensure_ascii=False,indent=2).encode('utf8'))
    for rel,name in [('responses/static_roster.json','static_roster.json'),('server_display_zh.json','server_display_zh.json'),('patches/language_chi.big','language_chi.big'),('patches/验证结果.json','language-check.json'),('http_config.py','http_config.py')]:add('server',rel,out/name)
    add('client','data/ui/libs/Module.big',out/'display/Module.big')
    add('client','data/ui/components/Label.big',out/'display/Label.big')
    # The play launcher reapplies this source; keep its native grade frames plus new badge.
    add('server','patches/Label.big',out/'display/Label.big')
    for lang in LANGS:
        if (out/'localization'/f'{lang}.big').exists():add('client',f'data/ui/localization/{lang}.big',out/'localization'/f'{lang}.big')
        for prefix in ('games/fo3id','cdn'):
            source=out/'languages'/prefix/f'language_{lang}.big'
            if source.exists():add('client',f'_cache/{prefix}/externalAssets/language_{lang}.big',out/'language_chi.big' if lang=='chi' else source)
    for p in imported_cards():
        filename=f"p{p['source_spid']}.png";image=R/'portraits'/filename
        add('server','assets/players/'+filename,image)
        for prefix in ('games/fo3id','cdn'):add('client',f'_cache/{prefix}/externalAssets/players/'+filename,image)
    add('server',MODEL,out/'25ucl-value-model.json');add('server',CATALOGUE,out/'25ucl-value-catalogue.json.gz')
    add('server','ucl25_value_extension.py',R/'ucl25_value_extension.py')
    add('server',DOC,(S/DOC).read_bytes()+note.encode('utf8'));add('server',SELF,helper.encode('utf8'));add('server',EVIDENCE,evidence)
    add('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))
    entries=[]
    for root,rel,source in payloads:
        target=(S if root=='server' else C)/rel;before=current_hash(target);after=sha(source) if isinstance(source,Path) else digest(source);key=(root,rel.casefold())
        if key in guards and before!=guards[key]['sha256']:raise RuntimeError('Fresh guard target drift: '+rel)
        if rel in (SELF,EVIDENCE,MODEL,CATALOGUE,'ucl25_value_extension.py') and target.exists():raise RuntimeError('Immutable import path already exists')
        guards[key]=dict(root=root,relative=rel,sha256=after)
        if before!=after:entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
    policies=list(composition.get('receipt_policies',[]))
    if not any(p['root']=='server' and p['relative']==parent.RECEIPT for p in policies):policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in oldreceipt.items() if k!='native_status'}))
    composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
    composition.setdefault('ancestry',[]).append(dict(layer='25ucl-final-072',revision=revision,native_status='PENDING'))
    manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,
        parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),cards=360,new_native=sum(not p['native_existing'] for p in imported_cards()),multiplier=.72,evidence=EVIDENCE,native_status='PENDING')
    body=encoded(manifest)
    for rel,value in [(MANIFEST,body),(RECEIPT,encoded(dict(status='INSTALLED_25UCL_FINAL_072',revision=revision,manifest_sha256=digest(body),state_shop_replaced=False,native_status='PENDING')))]:
        target=S/rel
        if target.exists():raise RuntimeError('Immutable metadata exists')
        entries.append(dict(root='server',relative=rel,target=target,source=value,before=None,after=digest(value)))
    entries.sort(key=lambda p:p['relative']=='play-local.bat')
    return dict(revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),entries=entries,certificate=certificate,out=out)


def commit(data,snapshot):
    assert_idle();backup=S/'backups'/data['revision'];backup.mkdir(parents=True,exist_ok=False)
    for name,body in snapshot.items():(backup/('fresh-'+name)).write_bytes(body)
    price_path=S/'gamedata/npc-market-prices.sqlite';price_before=sha(price_path);shutil.copyfile(price_path,backup/'market-before.sqlite')
    for i,entry in enumerate(data['entries']):
        if current_hash(entry['target'])!=entry['before']:raise RuntimeError('CAS drift before backup: '+entry['relative'])
        entry['backup']=backup/(str(i)+'-'+entry['target'].name)
        if entry['before'] is not None:shutil.copyfile(entry['target'],entry['backup'])
    journal=dict(status='PREPARED',revision=data['revision'],entries=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='source'} for e in data['entries']],completed=[])
    write(backup/'transaction.json',journal);written=[];price_after=None
    try:
        if sha(S/data['parent'])!=data['parent_hash']:raise RuntimeError('Parent advanced before commit')
        for entry in data['entries']:
            assert_idle()
            if isinstance(entry['source'],Path) and sha(entry['source'])!=entry['after']:raise RuntimeError('Validated input changed')
            entry['target'].parent.mkdir(parents=True,exist_ok=True);cas(entry);written.append(entry);journal['completed'].append(entry['relative'])
        if sha(price_path)!=price_before:raise RuntimeError('Market progressed while stopped; preserve and inspect')
        priceproof=extension.apply(price_path,S/CATALOGUE,S/MODEL,S/'gamedata/fifadb.sqlite')
        price_after=sha(price_path);journal['price_after_sha256']=price_after;write(backup/'transaction.json',journal)
        validation=load(S/'tools/player_import/check.py','ucl25_formal_full_checker').validate(S,C,full=True)
        if validation!=data['certificate']:raise RuntimeError('Formal full certificate differs from prepared formal-path binding')
        gate=load(S/SELF,'ucl25_formal_gate').preflight(S,C)
        for name,body in snapshot.items():
            if (S/'gamedata'/name).read_bytes()!=body:raise RuntimeError('Assets changed while stopped; do not restore them')
        journal['status']='INSTALLED';write(backup/'transaction.json',journal)
        return dict(backup=str(backup),preflight=gate,full_player_import=validation,price_generation=priceproof,assets_identical_while_stopped=True)
    except BaseException:
        if price_after is not None:
            if sha(price_path)==price_after:atomic(backup/'market-before.sqlite',price_path)
            else:journal['later_market_progress_retained']=True
        retained=rollback(written);journal.update(status='ROLLBACK_RETAINED_LATER_CHANGES' if retained else 'ROLLED_BACK',retained=retained)
        write(backup/'transaction.json',journal);raise


def main():
    if not idle():
        write(R/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,service_actions=False,validated_build=read(R/'latest-build.json')['path']))
        print('更新已延后，当前游戏继续运行');return
    check=read(R/'transaction-tests.json')
    if check['status']!='PASS' or check['installer_sha256']!=sha(Path(__file__)):raise RuntimeError('Transaction checks missing or stale')
    with locks():
        assert_idle();data=plan();write(R/'install-plan.json',{k:str(v) if isinstance(v,Path) else v for k,v in data.items() if k not in ('entries','certificate')})
        top=R.parent/'root-current-top.json';top_before=top.read_bytes();old_hot=get('http://127.0.0.1:8088/api/hot_update_status')
        stopped=False
        if listening():
            assert_idle();run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
            deadline=time.monotonic()+15
            while listening():
                if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no writes or duplicate start')
                time.sleep(.2)
            stopped=True
        snapshot={n:(S/'gamedata'/n).read_bytes() for n in ('state.json','shop.json')}
        try:result=commit(data,snapshot)
        except BaseException:
            if stopped:restart()
            raise
        result['launcher_pid'],result['readiness']=restart();result['services_restarted']=True
    finish(data,result,snapshot,old_hot,top,top_before)


def finish(data,result,snapshot,old_hot,top,top_before):
    deadline=time.monotonic()+30
    while True:
        hot=get('http://127.0.0.1:8088/api/hot_update_status')
        if hot['revision']==old_hot['revision'] and hot['watcher_running']:break
        if time.monotonic()>deadline:raise RuntimeError('Previous hot package did not recover; preserve installed assets')
        time.sleep(.25)
    assert hot['routes']==old_hot['routes'] and hot['error'] is None
    roster=get('https://127.0.0.1/static/roster');assert any(p.get('value')==[856] for p in roster['seasons'])
    colors=get('https://127.0.0.1/static/info/teamcolor')
    assert not any('普通赛季额外奖励' in p.get('name','') for p in colors['teamColors'])
    samples=[]
    for sid in (imported_cards()[0]['source_spid'],next(p['source_spid'] for p in imported_cards() if not p['native_existing'])):
        response=get('http://127.0.0.1:8088/api/market_price_store?spid='+str(sid)+'&grade=1')
        if response.get('value',0)<=0:raise RuntimeError('New card runtime valuation missing')
        samples.append(dict(spid=sid,current_price=response.get('current_price'),value=response['value']))
    result.update(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',revision=data['revision'],cards_imported=360,new_native=sum(not p['native_existing'] for p in imported_cards()),
        multiplier=.72,blocked_playerids=sorted(BLOCKED_PIDS),ordinary_extra_reward=0,
        hot_update_status=hot,services_restored=listening()==[443,8088,28002],runtime_samples=samples,
        state_shop_written=False,shop_equal=(S/'gamedata/shop.json').read_bytes()==snapshot['shop.json'],
        GUI_used=False,native_verified=False,match_verified=False,locks_released=True,composition_api='compose_manifest(server=None,client=None)',
        handoff=str(R/'installed-handback.json'),observed_at=datetime.datetime.now().astimezone().isoformat())
    with locks():
        play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
        if len(matches)!=1:raise RuntimeError('Ambiguous final current launcher')
        rel='patches/'+matches[0].decode();current=load(S/rel,'ucl25_actual_top')
        proof=current.preflight(S,C)
        result.update(preflight=proof,top_preflight=str(S/rel),top_manifest=str(S/current.MANIFEST),top_receipt=str(S/current.RECEIPT),
            files={str(S/p):sha(S/p) for p in (rel,current.MANIFEST,current.RECEIPT,'play-local.bat','http_config.py','gamedata/fifadb.sqlite','gamedata/player-import-validation.json')},
            client_files={str(C/'data/data_0.big'):sha(C/'data/data_0.big')},later_top_preserved=rel!=SELF)
        if top.read_bytes()==top_before:atomic(encoded(result),top)
        else:result['later_top_descriptor_preserved']=True
    write(R/'installed-handback.json',result);write(R/'install-status.json',dict(status=result['status'],formal_writer=False,handback=result['handoff']))
    print('INSTALLED_AND_RUNTIME_ACTIVE: 360 25UCL cards, multiplier 0.72, ordinary extra=0; native home/match=PENDING')


if __name__=='__main__':main()
