from pathlib import Path
from unittest.mock import patch
import copy,datetime,hashlib,json,os,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import install as i
m=json.loads((R/'elite-chains-release-manifest.json').read_text(encoding='utf8'));rows=m['files'];checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
def rejected(action,part):
    try:action()
    except RuntimeError as error:assert part in str(error),str(error)
    else:raise AssertionError('Expected rejection: '+part)
i.validate_rows(rows);check('Exact four server targets accepted',True)
for bad in ([],rows[:1],rows+rows[:1]):rejected(lambda:i.validate_rows(bad),'four')
check('Zero/one/extra row manifests rejected',True)
for root,path in (('client','data/ui/Module.big'),('server','gamedata/state.json'),('server','gamedata/shop.json'),('server','../product_packs.py')):
    bad=copy.deepcopy(rows);bad[0].update(root=root,relative=path);rejected(lambda:i.validate_rows(bad),'four')
check('Client, save, shop and traversal payloads rejected before writes',True)
bad=copy.deepcopy(rows);bad[1]=copy.deepcopy(bad[0]);rejected(lambda:i.validate_rows(bad),'four')
check('Duplicate resource targets rejected',True)
bad=copy.deepcopy(rows);next(r for r in bad if r['relative']=='gamedata/product_chain_elite.json')['parent_sha256']='a'*64
rejected(lambda:i.validate_rows(bad),'Append-only');check('New addon cannot replace an existing file',True)
def only_game(args,**kwargs):return '49372\n' if 'fifazf.exe' in args[-1] else ''
with patch.object(i.subprocess,'check_output',side_effect=only_game):
    assert i.blocking_processes(rows)==[]
    assert i.blocking_processes([dict(root='client')])==[49372]
check('Running game alone permits server-only boundary; client payload requires game exit',True)
with patch.object(i.subprocess,'check_output',return_value='91324\n77244\n'):
    assert i.blocking_processes(rows)==[91324,77244]
check('Official managed services remain blocking',True)
F=R/'install-fixture'/('boundary-'+datetime.datetime.now().strftime('%H%M%S-%f'));server=F/'server';client=F/'client';server.mkdir(parents=True);client.mkdir()
with i.publish_lock(server):
    original=(server/'.fo3-publish.lock').read_bytes()
    rejected(lambda:i.install(server,client,True),'Another publisher')
    assert (server/'.fo3-publish.lock').read_bytes()==original
check('Exclusive publish lock blocks a second publisher and preserves owner',not (server/'.fo3-publish.lock').exists())
with patch.object(i,'blocking_processes',return_value=[91324]):rejected(lambda:i.install(server,client,False),'services still active')
check('Service blocker releases lock without writing payload',not list(server.iterdir()))
with patch.object(i,'blocking_processes',return_value=[]),patch.object(i,'load') as load:
    validator=load.return_value;validator.TARGETS=i.EXPECTED;validator.MANIFEST='manifest.json';validator.RECEIPT='receipt.json'
    validator.preflight.side_effect=RuntimeError('parent mismatch sentinel')
    rejected(lambda:i.install(server,client,False),'parent mismatch sentinel')
check('Parent mismatch aborts without payload writes and releases lock',not list(server.iterdir()))
sample=F/'atomic.txt';sample.write_bytes(b'original')
with patch.object(i.os,'replace',side_effect=OSError('injected replace failure')):
    try:i.atomic(sample,b'replacement')
    except OSError as error:assert str(error)=='injected replace failure'
    else:raise AssertionError('Replace failure not raised')
check('Atomic replacement failure preserves original bytes and removes temporary file',sample.read_bytes()==b'original' and not sample.with_name(sample.name+'.product-packs-tmp').exists())
live=i.blocking_processes(rows)
check('Actual Windows PowerShell process query returns integer PIDs without touching game',all(type(pid) is int and pid>0 for pid in live))
report=dict(status='PASS',count=len(checks),checks=checks,installer_sha256=hashlib.sha256((R/'install.py').read_bytes()).hexdigest(),actual_blocking_service_PIDs=live)
(R/'server-boundary-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=True))
