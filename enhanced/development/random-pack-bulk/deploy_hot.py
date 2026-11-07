"""Publish only after isolated regression, preserve every current business route."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys, time, urllib.request
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent
SERVER=Path(r'D:\FO3ID\server')
sys.path.insert(0,str(ROOT))
import prepare_hot

def status():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8088/api/hot_update_status',timeout=4) as response:
        return json.load(response)

def main():
    tests=json.loads((ROOT/'server-tests.json').read_text('utf8'))
    assert tests['status']=='PASS' and tests['source_sha256']==hashlib.sha256((ROOT/'bulk_business.py').read_bytes()).hexdigest()
    for name in ('.shop-release.lock','.fo3-publish.lock'):
        assert not (SERVER/name).exists(),'Another formal publication is active; do not overwrite its lock'
    coordination=json.loads((ROOT.parent/'coordination-current.json').read_text('utf8'))
    assert not coordination.get('current_unhanded_writers') and coordination.get('next_formal_writer') is None
    prepare_hot.main()
    plan=json.loads((ROOT/'hot-plan.json').read_text('utf8'))
    before=status()
    assert before['abi']==2 and before['watcher_running'] and before['error'] is None
    assert before['revision']==plan['expected_revision']
    revision='random_pack_bulk_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    args=[str(SERVER/'.venv/Scripts/python.exe'),'-B',str(SERVER/'hot_update_publish.py'),
          '--source',str(ROOT/'merged_business.py'),'--revision',revision,'--expected-revision',before['revision']]
    for route in plan['routes']:
        args+=['--route',route['path']+'='+route['function']]
    subprocess.run(args,cwd=SERVER,check=True)
    deadline=time.monotonic()+30
    while True:
        after=status()
        if after['revision']==revision and after['watcher_running'] and after['error'] is None:
            break
        if after.get('error') or time.monotonic()>deadline:
            raise RuntimeError('Published but not activated: '+json.dumps(after))
        time.sleep(.25)
    result=json.loads((SERVER/'hot_updates/last-publication.json').read_text('utf8'))
    result.update(status='BUSINESS_RUNTIME_ACTIVE',revision=revision,hot_status=after,prior_hot_status=before)
    (ROOT/'hot-installed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
