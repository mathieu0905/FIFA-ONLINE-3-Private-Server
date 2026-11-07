from pathlib import Path
import json,tempfile
import install as m
checks=[];saved=(m.S,m.C,m.d.S,m.d.C,m.d.closed,m.check_inputs,m.d.base.atomic_cas)
try:
 with tempfile.TemporaryDirectory(dir=m.R,prefix='photo-io-') as temp:
  m.d.closed=lambda:(_ for _ in ()).throw(RuntimeError('Game running; deferred'))
  m.check_inputs=lambda:(_ for _ in ()).throw(AssertionError('Read inputs after game deferral'))
  m.main();checks.append('Active game defers before locks, writes or resource replacement')
  m.d.closed=lambda:None
  for at in [1,34,67]:
   root=Path(temp)/str(at);m.S=m.d.S=root/'server';m.C=m.d.C=root/'client';m.S.mkdir(parents=True);m.C.mkdir()
   files={('server','part-'+str(i)+'.txt'):b'new-photo' for i in range(67)};first=('server','part-0.txt');m.d.target(first).write_bytes(b'old-photo')
   class V:
    def table(self,rows):return {first:{}}
   parent=dict(validator=V(),composition={'guards':[]});count=[0]
   def cas(path,before,after):
    count[0]+=1
    if count[0]==at:raise OSError('Synthetic portrait transaction failure')
    return saved[-1](path,before,after)
   m.d.base.atomic_cas=cas
   try:m.transact(parent,files,'photo-io-fixture')
   except OSError:pass
   else:raise AssertionError('Synthetic failure accepted')
   assert m.d.target(first).read_bytes()==b'old-photo' and all(not m.d.target(k).exists() for k in files if k!=first)
   checks.append('Portrait CAS full rollback at '+str(at))
  m.d.base.atomic_cas=saved[-1];p=m.S/'later.txt';p.write_bytes(b'newer legitimate photo')
  try:m.d.restore_files([(('server','later.txt'),b'old',b'our-after')])
  except RuntimeError:pass
  else:raise AssertionError('Later photo replaced')
  assert p.read_bytes()==b'newer legitimate photo';checks.append('Rollback retains later legitimate asset changes')
finally:m.S,m.C,m.d.S,m.d.C,m.d.closed,m.check_inputs,m.d.base.atomic_cas=saved
report=dict(status='PASS',case_count=len(checks),cases=checks,formal_files_written=False,services_touched=False)
(m.R/'transaction-tests.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report))
