from pathlib import Path
import importlib.util,json,sys,tempfile
from unittest.mock import patch
R=Path(__file__).parent
target=Path(sys.argv[1]) if len(sys.argv)>1 else R/'fo3_control.py'
spec=importlib.util.spec_from_file_location('control',target);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
tests=[]
with tempfile.TemporaryDirectory() as tmp:
    m.S=Path(tmp); lock=m.S/'.shop-release.lock'; other=m.S/'.fo3-publish.lock'
    def forbidden(*a,**k):raise AssertionError('Unexpected validation/resource/service mutation')
    m.validate=forbidden;m.run=forbidden;m.closed=lambda:None;m.ready=lambda:True
    def action(name):
        with patch.object(sys,'argv',['control',name]):m.main()
    for locked in (False,True):
        if locked:lock.write_text('another installer');other.write_text('another publisher')
        with patch.object(m.subprocess,'Popen') as spawn:
            action('client-start');assert spawn.call_count==1
            args,kwargs=spawn.call_args;assert args[0]==[str(m.S/'launcher/fifalauncher.exe')]
            assert kwargs['env']['__COMPAT_LAYER']=='RunAsInvoker'
        if locked:assert lock.read_text()=='another installer' and other.read_text()=='another publisher'
        else:assert not lock.exists()
        tests.append('client-start allowed with '+('both publication locks' if locked else 'no publication lock')+'; only client spawned')
    with patch.object(m.subprocess,'Popen') as spawn:
        action('server-start');assert not spawn.called
    assert lock.read_text()=='another installer';tests.append('ready server-start succeeds despite release lock')
    m.ready=lambda:False
    with patch.object(m.subprocess,'Popen') as spawn:
        try:action('client-start');raise AssertionError('offline launch allowed')
        except RuntimeError as e:assert '服务端尚未就绪' in str(e)
        assert not spawn.called
    tests.append('offline client refused without starting services')
    for name in ('server-start','server-stop'):
        try:action(name);raise AssertionError('service mutation bypassed lock')
        except RuntimeError as e:assert '正在发布更新' in str(e)
        assert lock.read_text()=='another installer';tests.append(name+' respects owner lock')
    m.ready=lambda:True
    def playing():raise RuntimeError('already playing')
    m.closed=playing
    with patch.object(m.subprocess,'Popen') as spawn:
        try:action('client-start');raise AssertionError('duplicate launch')
        except RuntimeError as e:assert str(e)=='already playing'
        assert not spawn.called
    tests.append('running game prevents duplicate client')
    m.closed=lambda:None
    with patch.object(m.subprocess,'Popen',side_effect=OSError('spawn failed')):
        try:action('client-start');raise AssertionError('error hidden')
        except OSError:pass
    assert lock.read_text()=='another installer' and other.read_text()=='another publisher';tests.append('spawn failure preserves both publication locks')
result=dict(status='PASS',target=str(target),tests=tests,actual_client_launched=False,production_services_changed=False)
(R/'tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print(json.dumps(result,ensure_ascii=True))
