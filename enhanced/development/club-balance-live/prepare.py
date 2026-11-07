"""Minimal delta on the fresh official source; no service hooks or formal writes."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
SERVER=Path('D:/FO3ID/server')
CLIENT=Path('D:/FO3ID/32795')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def write(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def replace_once(source,old,new):
    if source.count(old)!=1:raise RuntimeError('Fresh source changed; review delta: '+old[:120])
    return source.replace(old,new)


def transform(source):
    if 'TC_ORDINARY_CLUB_BASE' in source:
        raise RuntimeError('Unexpected installed ordinary-only reward; review removal before changing formal source')
    source=replace_once(source,
        'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 2), (8, 9, 3), (10, 11, 4))',
        'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 5), (10, 10, 7), (11, 11, 8))')
    compile(source,'http_config.py','exec')
    return source


def main():
    original=(SERVER/'http_config.py').read_bytes()
    proposed=transform(original.decode('utf8')).encode('utf8')
    (ROOT/'baseline-http.py').write_bytes(original)
    (ROOT/'http_config.prepared.py').write_bytes(proposed)
    result=dict(status='PREPARED_SERVER_DELTA',baseline_sha256=hashlib.sha256(original).hexdigest(),
        proposed_sha256=hashlib.sha256(proposed).hexdigest(),transformer_sha256=sha(Path(__file__)),
        formal_files_written=False,client_resources_changed=False,state_shop_written=False)
    (ROOT/'prepared.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
