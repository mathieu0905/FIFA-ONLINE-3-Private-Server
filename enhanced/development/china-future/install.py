"""Official additive upstream/LIVE transaction. Active play defers before any write."""
from contextlib import contextmanager
from pathlib import Path
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
SELF='patches/china_future_preflight.py'
MANIFEST='patches/china-future-installed.json'
RECEIPT='patches/china-future-receipt.json'
CERT='gamedata/player-import-validation.json'
DOC='docs/工程经验与修改边界.txt'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


base=load(R.parent/'ai-opponent-progression/install.py','upstream_release_helpers')
base.R=R
sha=base.sha;encoded=base.encoded


class ProcessEntry(ctypes.Structure):
    _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),
              ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
              ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]


def game_running():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];kernel.Process32FirstW.restype=wintypes.BOOL
    kernel.Process32NextW.argtypes=kernel.Process32FirstW.argtypes;kernel.Process32NextW.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry=ProcessEntry();entry.dwSize=ctypes.sizeof(entry)
        more=kernel.Process32FirstW(handle,ctypes.byref(entry))
        while more:
            if entry.szExeFile.casefold()=='fifazf.exe':return True
            more=kernel.Process32NextW(handle,ctypes.byref(entry))
        return False
    finally:kernel.CloseHandle(handle)


def closed():
    if game_running():raise RuntimeError('更新已延后，当前游戏继续运行')


base.closed=closed


@contextmanager
def locks():
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY)
            body=encoded(dict(pid=os.getpid(),owner='china-future-v1',thread='01a1b3ef-a0a3-79f2-9005-989eb5b9669d',handoff=str(R/'installed-handback.json')))
            owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for path,fd,body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==body:path.unlink()


def target(key):
    root,rel=key;directory={'server':S,'client':C}[root];path=(directory/rel).resolve()
    if path==directory or not path.is_relative_to(directory):raise ValueError('Release target escape')
    return path


def payloads():
    files={('server','http_config.py'):(R/'http_config.py').read_bytes(),
      ('server','responses/static_roster.json'):(R/'static_roster.json').read_bytes(),
      ('server','gamedata/china-future-price-extension.json'):(R/'prices.json').read_bytes(),
      ('server','china_future_market.py'):(R/'price_extension.py').read_bytes(),
      ('client','data/data_0.big'):(R/'prepared-v3/data_0.big').read_bytes(),
      ('client','data/ui/components/Label.big'):(R/'Label.big').read_bytes(),
      ('server','patches/Label.big'):(R/'Label.big').read_bytes()}
    for rel in ('fifadb.sqlite','custom_rosters.json','player-imports.json'):
        files[('server','gamedata/'+rel)]=(R/'prepared-v3'/rel).read_bytes()
    for p in sorted((R/'input/portraits').glob('*.png')):
        files[('client','_cache/games/fo3id/externalAssets/players/'+p.name)]=p.read_bytes()
    assert len(files)==42
    return files



def check_inputs():
    review=json.loads((R/'reviewed-payloads.json').read_text('utf8'))
    for path,digest in review['files'].items():
        if sha(path)!=digest:raise RuntimeError('Reviewed payload changed: '+path)
    for path,digest in review['formal_baseline'].items():
        if sha(path)!=digest:raise RuntimeError('Formal baseline advanced; fresh/rebuild '+path)
    if json.loads((R/'tests.json').read_text('utf8'))['status']!='PASS':raise RuntimeError('Regression missing')



def fresh_parent():
    play=(S/'play-local.bat').read_bytes();found=re.search(rb'patches\\(\w+_preflight\.py)',play)
    if not found:raise RuntimeError('Actual launcher gate not found')
    rel='patches/'+found.group(1).decode()
    if rel==SELF:raise RuntimeError('Already installed; verify the current child')
    helper=load(S/rel,'upstream_latest_parent');proof=helper.preflight(S,C);composition=helper.compose_manifest(S,C)
    validator=load(S/'patches/startup_market_preflight.py','upstream_composition_validator');validator.verify_manifest(composition,S,C)
    return dict(play=play,relative=rel,helper=helper,proof=proof,composition=composition,validator=validator)


def helper_source(parent):
    h=parent['helper'];source=(S/parent['relative']).read_text('utf8')
    receipt=json.loads((S/h.RECEIPT).read_text('utf8'))
    for old,new in ((h.MANIFEST,MANIFEST),(h.RECEIPT,RECEIPT),(h.SELF,SELF),(receipt['status'],'INSTALLED_CHINA_FUTURE'),(parent['proof']['status'],'CHINA_FUTURE_PREFLIGHT_PASS')):
        if old not in source:raise RuntimeError('Fresh parent shape changed '+old)
        source=source.replace(old,new)
    anchor='\n if not required<=seen:'
    assert source.count(anchor)==1
    source=source.replace(anchor,"\n required.update({('server','china_future_market.py'),('server','gamedata/china-future-price-extension.json'),('server','gamedata/player-import-validation.json'),('server','responses/static_roster.json')})"+anchor)
    anchor=' return dict('
    assert source.count(anchor)==1
    verification=" spec=importlib.util.spec_from_file_location('_china_future_guard',server/'china_future_market.py');china_ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(china_ext)\n china_prices=china_ext.verify(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/china-future-price-extension.json')\n"
    source=source.replace(anchor,verification+' return dict(china_future_prices=china_prices,',1)
    compile(source,SELF,'exec');return source.encode('utf8')



def commit_file(key,before,after,committed):
    closed();base.atomic_cas(target(key),before,after);committed.append((key,before,after))


def restore_files(committed):
    conflicts=[]
    for key,before,after in reversed(committed):
        try:base.atomic_cas(target(key),after,before)
        except RuntimeError:conflicts.append(key)
    if conflicts:raise RuntimeError('Later legitimate changes retained during rollback: '+repr(conflicts))


def transact(parent,files,revision):
    closed()
    backup=S/'backups'/revision;closed();backup.mkdir(parents=True)
    guards=parent['validator'].table(parent['composition']['guards'])
    for key in files:
        canonical=(key[0],key[1].casefold())
        if target(key).exists() and canonical not in guards:raise RuntimeError('Existing unregistered target retained: '+str(key))
    before={key:target(key).read_bytes() if target(key).exists() else None for key in files}
    for key in (("server",CERT),("server",SELF),("server",MANIFEST),("server",RECEIPT),("server","play-local.bat")):
        before.setdefault(key,target(key).read_bytes() if target(key).exists() else None)
    for key,body in before.items():
        if body is not None:
            closed();path=backup/key[0]/key[1];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    journal=[];seed_attempted=False;extension=load(R/'price_extension.py','upstream_price_transaction')
    try:
        for key,body in files.items():commit_file(key,before[key],body,journal)
        # Revalidate actual formal paths; never publish a workspace-bound certificate.
        check=load(S/'tools/player_import/check.py','upstream_formal_import_checker')
        sys.path[:0]=[str(S/'tools/player_import'),str(S/'tools/re'),str(S)]
        full=check.validate(S,C,full=True)
        if full['status']!='PLAYER_IMPORT_FULL_PASS':raise RuntimeError('Formal full player import failed')
        cert=encoded(full);commit_file(('server',CERT),before[('server',CERT)],cert,journal);files[('server',CERT)]=cert
        packet=extension.packet(S/'gamedata/china-future-price-extension.json')
        with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as con:
            if any(con.execute('select 1 from seeds where spid=?',(sid,)).fetchone() for sid,_ in packet['rows']):
                raise RuntimeError('Preexisting new-season seeds retained; refusing ownership/rollback')
        con.close()
        seed_attempted=True
        extension.apply(S/'gamedata/npc-market-prices.sqlite',S/'gamedata/china-future-price-extension.json')
        helper=helper_source(parent);files[('server',SELF)]=helper
        play=parent['play'].replace(parent['relative'].replace('/','\\').encode(),SELF.replace('/','\\').encode())
        files[('server','play-local.bat')]=play
        composed=parent['composition'];guards=parent['validator'].table(composed['guards'])
        for key,body in files.items():
            guards[(key[0],key[1].casefold())]=dict(root=key[0],relative=key[1],sha256=hashlib.sha256(body).hexdigest())
        composed.update(guards=list(guards.values()),files_verified=False)
        composed.setdefault('ancestry',[]).append(dict(layer='china-future-v1',native_status='PENDING'))
        manifest=encoded(dict(schema=1,revision=revision,client=str(C),guards=composed['guards'],composition=composed,
            parent_preflight=parent['relative'],parent_preflight_sha256=sha(S/parent['relative']),state_shop_replaced=False,
            card_edition='China Future custom potential v1',new_cards=32,new_generic_identities=32))
        receipt=encoded(dict(status='INSTALLED_CHINA_FUTURE',revision=revision,manifest_sha256=hashlib.sha256(manifest).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
        for rel,body in ((SELF,helper),(MANIFEST,manifest),(RECEIPT,receipt),('play-local.bat',play)):
            commit_file(('server',rel),before[('server',rel)],body,journal)
        proof=load(S/SELF,'upstream_installed_gate').preflight(S,C)
        return dict(status='INSTALLED',revision=revision,backup=str(backup),preflight=proof,full_player_import=full['status'],
            top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),
            composition_api='compose_manifest(server=None,client=None)',state_shop_written=False)
    except BaseException:
        if seed_attempted:
            packet=extension.packet(R/'prices.json')
            with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as con:
                appended=con.execute('select count(*) from seeds where spid=?',(packet['rows'][0][0],)).fetchone()[0]
            con.close()
            if appended:extension.rollback(S/'gamedata/npc-market-prices.sqlite',R/'prices.json')
        restore_files(journal)
        raise


LEDGER='\n\nFO3-CHINA-FUTURE-001（2026-11-07）：新增327中国明日之星32名真实身份，王钰栋92/李昊炎92等，+1/LV1/无套装加成主位置显示85–92。能力为用户授权的自定义潜力设定，按真实位置权重计算，不能只填overallrating。出生日期逐人来源记录在registry；依木兰采用新疆体育局2005-05-03，李昊炎采用原达姆官网2012-01-28；体型数值是游戏建模参数，不冒称官方当前测量。32新身份明确内置通用脸+实名剪影，native playerid唯一、六语姓名/双端UI/原生身份/技能码/资源回执经正式prepare与full check；不改变已有模型或同人身份。新卡加入现有传奇系列及传奇时刻额外加成成员，混搭首发人数累计，原加成参数/取最高/替补排除规则不变；旧卡包原池排除327，新卡可市场检索并按已有v11模型仅追加新种子。保留此前上游688卡、双卡强化保护、五档六人、AI+10/LV30及所有旧guards/policies/校准事件。安装依实际游戏状态在写前延期，fresh停服快照，不写测试卡/经理/余额；静态、首页近远景及比赛验收分别记录，无GUI/实机不得冒称通过。证据D:/fifaol3/china-future/tests.json及installed-handback.json。\n用户随后明确加入更年轻一批并提高李昊炎：最终32人，原16人另补2009/2010年出生的邝兆镭、万项、谢晋、周雨诺、帅惟浩、吕孟洋、金昱成、南子勋、李钧鹏、张旭尧、秦子牛、江承恩、潘朝伟、徐正鹏、赵松源、顾博宇。李昊炎最终92，与王钰栋同第一档；旧16人/91工作产物已废弃，最终完整产物prepared-v3。\n'


def main():
    # This must remain the first operation: no release locks or file writes while gaming.
    try:closed()
    except RuntimeError as error:
        print(str(error));return
    check_inputs()
    with locks():
        closed();check_inputs();parent=fresh_parent();files=payloads()
        if any((S/rel).exists() for rel in (SELF,MANIFEST,RECEIPT)):raise RuntimeError('Immutable child metadata already exists')
        files[('server',DOC)]=(S/DOC).read_bytes()+LEDGER.encode('utf8')
        hot_before=base.hot_status()
        base.stop()  # Protected stop failure aborts without any formal payload write/start.
        snapshot={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
        for name,body in snapshot.items():(R/('stopped-'+name)).write_bytes(body)
        revision='china-future-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        result=None;error=None
        try:result=transact(parent,files,revision)
        except BaseException as exc:error=exc
        launcher,readiness=base.start()
        if error:raise error
        result.update(launcher_pid=launcher,readiness=readiness,services_restarted=True,services_restored=True)
    # Business watcher restores only after publisher locks are released.
    import time
    deadline=time.monotonic()+20
    while True:
        hot=base.hot_status()
        if hot['revision']==hot_before['revision'] and hot['watcher_running'] and hot['error'] is None:break
        if time.monotonic()>deadline:raise RuntimeError('Business hot routes have not restored; inspect without replaying transactions')
        time.sleep(.2)
    assert hot['routes']==hot_before['routes']
    with locks():
        if SELF.replace('/','\\').encode() not in (S/'play-local.bat').read_bytes():raise RuntimeError('Newer top retained; refusing stale descriptor overwrite')
        business=lambda state:{k:v for k,v in state.items() if k!='market_simulation'}
        assert business(json.loads(snapshot['state.json']))==business(json.loads((S/'gamedata/state.json').read_bytes())), 'New progress retained; never restore state'
        assert (S/'gamedata/shop.json').read_bytes()==snapshot['shop.json']
        result.update(status='INSTALLED_AND_RUNTIME_ACTIVE',runtime_active=True,hot_update_status=hot,
            native_game_verified=False,match_verified=False,new_cards=32,new_generic_identities=32,
            state_business_exact=True,shop_exact=True,observed_at=datetime.datetime.now().astimezone().isoformat(),
            files={str(S/rel):sha(S/rel) for rel in (SELF,MANIFEST,RECEIPT,'play-local.bat')},
            handoff=str(R/'installed-handback.json'))
        (R/'installed-handback.json').write_bytes(encoded(result))
        (R.parent/'root-current-top.json').write_bytes(encoded(result))
        print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
