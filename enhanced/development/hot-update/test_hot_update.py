from pathlib import Path
import hashlib,json,socket,tempfile,threading,time,types
from hot_update_runtime import Manager,compile_handlers,digest
from hot_update_release import body,commit,locks

checks=[]
def record(name):checks.append(name)
def package(root,revision,value,expected='bootstrap',source=None,routes=None):
    source=source or ('def handle(host, query, body):\n    return host.reply('+repr(value)+')\n').encode()
    relative='hot_updates/revisions/'+revision+'/business.py';p=root/relative;p.parent.mkdir(parents=True);p.write_bytes(source)
    m=body(dict(schema=1,revision=revision,state_shop_replaced=False,guards=[dict(root='server',relative=relative,sha256=digest(source))]))
    r=body(dict(revision=revision,manifest_sha256=digest(m)))
    (root/(revision+'-manifest.json')).write_bytes(m);(root/(revision+'-receipt.json')).write_bytes(r)
    desc=dict(schema=1,abi=1,revision=revision,expected_revision=expected,code=relative,sha256=digest(source),routes=routes or [dict(path='/shop/hot-test',function='handle')],release=dict(manifest=revision+'-manifest.json',manifest_sha256=digest(m),receipt=revision+'-receipt.json',receipt_sha256=digest(r)))
    (root/'hot_updates/active.json').write_bytes(body(desc));return desc

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);host=types.SimpleNamespace(STATE_LOCK=threading.RLock(),reply=lambda x:('application/json',json.dumps(x).encode()))
    manager=Manager(host,root);assert not manager.poll()
    package(root,'one',1);assert manager.poll();assert manager.handler('/shop/hot-test')('',b'')==host.reply(1)
    assert manager.handler('/account') is None;record('valid version selected; untouched core routes fall through')
    old=manager.handler('/shop/hot-test')
    package(root,'two',2,'one');assert manager.poll();assert old('',b'')==host.reply(1);assert manager.handler('/shop/hot-test')('',b'')==host.reply(2)
    record('in-flight handler remains on its original version')
    package(root,'stale',3,'one');assert not manager.poll() and manager.revision=='two';record('stale revision rejected without losing current version')
    desc=package(root,'corrupt',4,'two');(root/desc['code']).write_text('bad bytes')
    assert not manager.poll() and manager.revision=='two';record('changed payload hash rejected')
    package(root,'badsyntax',4,'two',source=b'def broken(: pass');assert not manager.poll();assert manager.revision=='two';record('syntax failure retains previous generation')
    package(root,'core',4,'two',routes=[dict(path='/account',function='handle')]);assert not manager.poll();record('core session route cannot be hot replaced')
    for source in (b'import os\n',b'raise RuntimeError()\n',b'def handle(host,q,b=print("side effect")): pass\n',b'@print\ndef handle(host,q,b): pass\n'):
        try:compile_handlers(source,'bad.py',[dict(path='/shop/a',function='handle')]);raise AssertionError('Unsafe top-level accepted')
        except ValueError:pass
    record('loading cannot execute top-level install hooks, imports, decorators or defaults')
    desc=package(root,'proof',5,'two');(root/desc['release']['manifest']).write_text('{}')
    assert not manager.poll() and manager.revision=='two';record('release proof tampering rejected')
    desc=package(root,'escape',5,'two');desc['code']='../outside.py';(root/'hot_updates/active.json').write_bytes(body(desc))
    assert not manager.poll();record('payload path escape rejected')
    # A request holds exactly the production host's transaction lock.
    package(root,'three',3,'two');swapped=threading.Event()
    def update():assert manager.poll();swapped.set()
    with host.STATE_LOCK:
        worker=threading.Thread(target=update);worker.start();assert not swapped.wait(.05)
        assert manager.handler('/shop/hot-test')('',b'')==host.reply(2)
    worker.join(2);assert swapped.is_set();record('switch waits for current transaction to finish')
    state={'balance':100,'cards':[1,2]};before=json.dumps(state,sort_keys=True);host.state=state
    left,right=socket.socketpair()
    try:
        package(root,'four',4,'three');assert manager.poll();left.sendall(b'ping');assert right.recv(4)==b'ping'
        assert json.dumps(state,sort_keys=True)==before;record('switch leaves shared assets and an existing socket untouched')
    finally:left.close();right.close()
    restarted=Manager(host,root);assert restarted.poll() and restarted.revision=='four';record('active version restored from guarded descriptor after normal restart')
    # An older installed generation can be selected again with a fresh expected revision.
    saved=json.loads((root/'hot_updates/active.json').read_text());saved.update(revision='one',expected_revision='four',code='hot_updates/revisions/one/business.py')
    source=(root/saved['code']).read_bytes();saved['sha256']=digest(source);m=(root/'one-manifest.json').read_bytes();r=(root/'one-receipt.json').read_bytes();saved['release']=dict(manifest='one-manifest.json',manifest_sha256=digest(m),receipt='one-receipt.json',receipt_sha256=digest(r))
    (root/'hot_updates/active.json').write_bytes(body(saved));assert manager.poll() and manager.revision=='one';record('explicit rollback selects preserved immutable generation')
    package(root,'raises',None,'one',source=b'def handle(host,q,b):\n    host.state["balance"] -= 1\n    raise RuntimeError("after mutation")\n')
    assert manager.poll()
    try:manager.handler('/shop/hot-test')('',b'');raise AssertionError('Error swallowed')
    except RuntimeError:pass
    assert state['balance']==99;record('failed request is not replayed through old handler')
    descriptor=json.loads((root/'hot_updates/active.json').read_text())
    descriptor.update(disabled=True,routes=[],expected_revision='raises')
    (root/'hot_updates/active.json').write_bytes(body(descriptor));assert manager.poll()
    assert manager.handler('/shop/hot-test') is None;record('disable restores original host dispatch without restart or asset rollback')
    # Worker does not consume a descriptor while another publisher owns the lock.
    (root/'.shop-release.lock').write_text('owner');package(root,'five',5,'raises');manager.start();time.sleep(.6);assert manager.revision=='raises'
    (root/'.shop-release.lock').unlink();deadline=time.monotonic()+2
    while manager.revision!='five' and time.monotonic()<deadline:time.sleep(.02)
    manager.stop();assert manager.revision=='five' and not manager.status()['watcher_running'];record('watcher respects publication lock and stops cleanly')

# Exercise the real CAS transaction on temporary files with a minimal composed gate.
for fail in (1,3,None):
    with tempfile.TemporaryDirectory() as tmp:
        s=Path(tmp)/'server';c=Path(tmp)/'client';s.mkdir();c.mkdir();(s/'patches').mkdir()
        helper="""from pathlib import Path
import json,hashlib
SELF='patches/base_preflight.py'
MANIFEST='patches/base-installed.json'
RECEIPT='patches/base-receipt.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def preflight(server=None,client=None):
 s=Path(server);m=json.loads((s/MANIFEST).read_text());r=json.loads((s/RECEIPT).read_text());assert r['status']=='BASE_INSTALLED' and r['manifest_sha256']==sha(s/MANIFEST)
 for g in m['guards']:assert sha(s/g['relative'])==g['sha256']
 return dict(status='BASE_PASS')
def compose_manifest(server=None,client=None):
 s=Path(server);m=json.loads((s/MANIFEST).read_text());g=list(m['guards'])
 for rel in (MANIFEST,RECEIPT):g.append(dict(root='server',relative=rel,sha256=sha(s/rel)))
 return dict(guards=g,receipt_policies=[])
"""
        (s/'patches/base_preflight.py').write_text(helper)
        play=b'.venv\\Scripts\\python.exe patches\\base_preflight.py\r\n';(s/'play-local.bat').write_bytes(play)
        mb=body(dict(schema=1,revision='base',guards=[dict(root='server',relative=rel,sha256=digest((s/rel).read_bytes())) for rel in ('patches/base_preflight.py','play-local.bat')]))
        (s/'patches/base-installed.json').write_bytes(mb);(s/'patches/base-receipt.json').write_bytes(body(dict(status='BASE_INSTALLED',manifest_sha256=digest(mb))))
        before={p.relative_to(s).as_posix():p.read_bytes() for p in s.rglob('*') if p.is_file()}
        try:
            with locks(s,'test'):
                result=commit(s,c,'test_hot',{'new.py':b'x=1\n'},fail_after=fail)
        except OSError:
            assert fail is not None
            for rel,data in before.items():assert (s/rel).read_bytes()==data
            assert not (s/'new.py').exists()
        else:assert fail is None and result['status']=='INSTALLED_HOT_BUSINESS'
        assert not (s/'.shop-release.lock').exists() and not (s/'.fo3-publish.lock').exists()
record('real publication commits and injected failures restore exact prior files')
with tempfile.TemporaryDirectory() as tmp:
    s=Path(tmp);(s/'.shop-release.lock').write_bytes(b'other owner')
    try:
        with locks(s,'test'):raise AssertionError('Lock bypassed')
    except FileExistsError:pass
    assert (s/'.shop-release.lock').read_bytes()==b'other owner'
record('another publishers lock is never removed')
report=dict(status='PASS',checks=checks,production_services_started=False,production_assets_written=False,native_game_verified=False)
(Path(__file__).parent/'tests.json').write_bytes(body(report));print(json.dumps(report))
