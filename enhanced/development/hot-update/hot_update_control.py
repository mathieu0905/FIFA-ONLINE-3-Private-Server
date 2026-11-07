"""Inspect, disable, or roll back only hot business routes; never restart services."""
import argparse,json,threading,types,urllib.request
from pathlib import Path
from hot_update_release import atomic,body,locks
from hot_update_runtime import Manager

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--rollback',help='Previously published immutable revision')
    group.add_argument('--disable',action='store_true')
    args=parser.parse_args();server=Path(__file__).resolve().parent
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def status():
        with opener.open('http://127.0.0.1:8088/api/hot_update_status',timeout=3) as response:return json.load(response)
    current=status()
    if 'revision' not in current:raise RuntimeError('Hot update bootstrap has not been connected')
    if not args.rollback and not args.disable:print(json.dumps(current,ensure_ascii=False));return
    with locks(server,'hot-business-control'):
        current=status()
        if args.rollback:
            root=(server/'hot_updates/history').resolve();path=(root/(args.rollback+'.json')).resolve()
            if not path.is_relative_to(root):raise ValueError('Invalid rollback revision')
            descriptor=json.loads(path.read_text('utf8'))
        else:
            descriptor=json.loads((server/'hot_updates/active.json').read_text('utf8'))
            descriptor.update(disabled=True,routes=[])
        descriptor['expected_revision']=current['revision']
        Manager(types.SimpleNamespace(STATE_LOCK=threading.RLock()),server).prepare(descriptor)
        atomic(server/'hot_updates/active.json',body(descriptor))
    print('REQUESTED; inspect runtime status to confirm activation')
if __name__=='__main__':main()
