"""Small temporary-file regression of the actual installer transaction."""
from pathlib import Path
import tempfile,json
import install as m
from prepare import R,sha,write
checks=[]
with tempfile.TemporaryDirectory(prefix='transaction-',dir=R) as temp:
 root=Path(temp)
 def setup(name):
  p=root/name;p.mkdir();a=p/'a';a.write_bytes(b'old');b=p/'b'
  entries=[dict(target=a,source=b'new',before=sha(a),after=m.digest(b'new')),dict(target=b,source=b'added',before=None,after=m.digest(b'added'))]
  return p,a,b,entries
 for n in (1,2):
  p,a,b,entries=setup('fail'+str(n))
  try:m.commit(entries,p/'backup',lambda:None,fail_after=n)
  except OSError:pass
  else:raise AssertionError('Expected failure')
  assert a.read_bytes()==b'old' and not b.exists();checks.append('rollback-after-'+str(n))
 p,a,b,entries=setup('success');m.commit(entries,p/'backup',lambda:None);assert a.read_bytes()==b'new' and b.read_bytes()==b'added';checks.append('commit')
 p,a,b,entries=setup('concurrent')
 def hook(i,e):
  if i==1:a.write_bytes(b'later-legal-change');b.write_bytes(b'external')
 try:m.commit(entries,p/'backup',lambda:None,hook=hook)
 except AssertionError:pass
 else:raise AssertionError('Must reject drift')
 assert a.read_bytes()==b'later-legal-change' and b.read_bytes()==b'external';checks.append('preserve-concurrent-writes-and-rollback')
 p,a,b,entries=setup('verify-fail')
 def fail():raise RuntimeError('Verification failed')
 try:m.commit(entries,p/'backup',fail)
 except RuntimeError:pass
 else:raise AssertionError('Must reject verify failure')
 assert a.read_bytes()==b'old' and not b.exists();checks.append('rollback-final-verification-failure')
write(R/'transaction-tests.json',dict(status='PASS',checks=checks,temporary_files_only=True));print(json.dumps(checks))
