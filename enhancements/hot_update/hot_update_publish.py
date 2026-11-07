"""Publish reviewed exact-route business handlers, without restarting any service."""
import argparse
import json
from pathlib import Path
import re
import sys
import urllib.request
from hot_update_runtime import ABI, compile_handlers, digest
from hot_update_release import atomic, body, commit, locks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--route', action='append', required=True, help='/shop/path=function_name')
    parser.add_argument('--expected-revision', required=True)
    args = parser.parse_args()
    server = Path(__file__).resolve().parent
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.revision):
        parser.error('Invalid revision')
    routes = [dict(zip(('path', 'function'), row.split('=', 1))) for row in args.route]
    source = args.source.read_bytes()
    if len(source) > 131072:
        parser.error('Business payload exceeds 128 KiB')
    compile_handlers(source, str(args.source), routes, allow_templates=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8088/api/hot_update_status', timeout=3) as response:
        status = json.load(response)
    if status.get('abi') != ABI or status.get('revision') != args.expected_revision:
        raise RuntimeError('Hot update is not connected or runtime revision changed; no files published')
    relative = 'hot_updates/revisions/' + args.revision + '/business.py'
    with locks(server, 'hot-business-' + args.revision):
        if (server / relative).exists():
            raise RuntimeError('Revision already exists; immutable payload cannot be overwritten')
        def activate(proof):
            return dict(schema=1, abi=ABI, revision=args.revision, expected_revision=args.expected_revision,
                        code=relative, sha256=digest(source), routes=routes, release=proof)
        result = commit(server, Path('D:/FO3ID/32795'), 'hot_business', {relative: source}, activate)
        atomic(server / ('hot_updates/history/' + args.revision + '.json'),
               (server / 'hot_updates/active.json').read_bytes())
        atomic(server / 'hot_updates/last-publication.json', body(result))
        observation = Path('D:/fifaol3/root-current-top.json')
        if observation.parent.exists():
            atomic(observation, body(result))
    print(json.dumps(dict(status='PUBLISHED_AWAITING_RUNTIME_ACTIVATION', revision=args.revision,
                          note='Check /api/hot_update_status for active revision; publication is not activation'), ensure_ascii=False))

if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
