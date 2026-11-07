from contextlib import contextmanager
from pathlib import Path
import copy,importlib.util,json,tempfile
import install as m
checks=[]
saved={n:getattr(m,n) for n in ['S','C','locks','check_inputs','payloads']}
d_saved={n:getattr(m.d,n) for n in ['S','C','closed','game_running','fresh_parent']}
base_saved={n:getattr(m.d.base,n) for n in ['atomic_cas','stop','start','hot_status']}
try:
 with tempfile.TemporaryDirectory(dir=m.R,prefix='publish-io-test-') as temp:
  m.d.closed=lambda:(_ for _ in ()).throw(RuntimeError('Deferred game running'))
  m.check_inputs=lambda:(_ for _ in ()).throw(AssertionError('Inputs accessed after deferral'))
  m.main();checks.append('Game running defers before locks, reads, writes or stop')
  m.d.closed=lambda:None
  total=len(saved['payloads']())+1
  for at in [1,total//2,total]:
   root=Path(temp)/str(at);root.mkdir();m.S=m.d.S=root/'server';m.C=m.d.C=root/'client';m.S.mkdir();m.C.mkdir()
   files={('server','part-'+str(i)+'.txt'):b'new' for i in range(total)};first=('server','part-0.txt');m.d.target(first).write_bytes(b'old')
   class Validator:
    def table(self,rows):return {first:{}}
   parent=dict(validator=Validator(),composition={'guards':[]})
   count=[0]
   def cas(path,before,after):
    count[0]+=1
    if count[0]==at:raise OSError('Injected payload failure')
    return base_saved['atomic_cas'](path,before,after)
   m.d.base.atomic_cas=cas
   try:m.transact(parent,files,'own-io-fixture')
   except OSError:pass
   else:raise AssertionError('Injected write accepted')
   assert m.d.target(first).read_bytes()==b'old'
   assert all(not m.d.target(k).exists() for k in files if k!=first)
   checks.append('Full payload rollback at '+str(at))
  m.d.base.atomic_cas=base_saved['atomic_cas']
  p=m.S/'later.txt';p.write_bytes(b'later writer')
  try:m.d.restore_files([(('server','later.txt'),b'old',b'our after')])
  except RuntimeError:pass
  else:raise AssertionError('Later write erased')
  assert p.read_bytes()==b'later writer';checks.append('CAS rollback preserves later legitimate writer')
  (m.S/'docs').mkdir();(m.S/m.DOC).write_bytes(b'ledger')
  @contextmanager
  def free():yield
  m.locks=free;m.check_inputs=lambda:None;m.payloads=lambda:{};m.d.fresh_parent=lambda:{}
  m.d.base.hot_status=lambda:{};m.d.base.stop=lambda:(_ for _ in ()).throw(RuntimeError('Protected stop refused'))
  m.d.game_running=lambda:False
  m.d.base.start=lambda:(_ for _ in ()).throw(AssertionError('Duplicate start after refused stop'))
  try:m.main()
  except RuntimeError as e:assert str(e)=='Protected stop refused'
  else:raise AssertionError('Refused stop ignored')
  checks.append('Protected stop refusal cannot continue writing or start duplicate service')
  m.d.game_running=lambda:True
  m.main()
  checks.append('Game opens after preflight: protected stop defers without payload writes or service start')
finally:
 for n,v in saved.items():setattr(m,n,v)
 for n,v in d_saved.items():setattr(m.d,n,v)
 for n,v in base_saved.items():setattr(m.d.base,n,v)
report=dict(status='PASS',case_count=len(checks),cases=checks,formal_files_written=False,services_touched=False)
(m.R/'transaction-tests.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report))
