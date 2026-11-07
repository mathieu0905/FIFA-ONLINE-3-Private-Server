from pathlib import Path
import json,hashlib
import install as d
R=Path(__file__).parent;ROOT=R/'install-tests';ROOT.mkdir(exist_ok=True)
def fixture(name):
 base=ROOT/(name+'-'+__import__('uuid').uuid4().hex[:8]);s=base/'server';c=base/'client';s.mkdir(parents=True);c.mkdir();(s/'patches').mkdir();(s/'gamedata').mkdir()
 (s/'http_config.py').write_text('original fixture module\n')
 (s/'play-local.bat').write_bytes(b'@echo off\r\npython patches\\fixture_preflight.py\r\n')
 (s/'gamedata/state.json').write_bytes(b'{"real_progress":"preserve"}')
 (s/'gamedata/shop.json').write_bytes(b'{"issued_rights":"preserve"}')
 code='''from pathlib import Path
import json,hashlib
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compose_manifest(server=None,client=None):
 s=Path(server);m=json.loads((s/'patches/base.json').read_text());return dict(schema=1,server=str(s),client=str(client),guards=m['guards']+[dict(root='server',relative='patches/base.json',sha256=sha(s/'patches/base.json'))],receipt_policies=[],ancestry=[])
def preflight(server=None,client=None):
 c=compose_manifest(server,client)
 for r in c['guards']:assert sha(Path(server)/r['relative'])==r['sha256']
 return dict(status='FIXTURE_PARENT_PASS')
'''
 (s/'patches/fixture_preflight.py').write_text(code)
 rows=[dict(root='server',relative=n,sha256=d.sha(s/n)) for n in ['http_config.py','play-local.bat','patches/fixture_preflight.py']]
 (s/'patches/base.json').write_bytes(d.encoded(dict(guards=rows)))
 return s,c
checks=[]
for fail in [1,6,None]:
 s,c=fixture('failure-'+str(fail));before={p.relative_to(s).as_posix():p.read_bytes() for p in s.rglob('*') if p.is_file()}
 with d.locks(s):
  p=d.plan(s,c,fixture=True)
  try:r=d.apply(p,fail_after=fail)
  except OSError:
   assert fail is not None
   assert all((s/n).read_bytes()==b for n,b in before.items())
   assert not(s/d.MANIFEST).exists() and not(s/d.SELF).exists()
  else:
   assert fail is None and r['preflight']['status']=='LEGACY_CHAIN_HIDE_PREFLIGHT_PASS'
   digest={str(p):d.sha(p) for p in s.rglob('*') if p.is_file()}
   assert d.apply(d.plan(s,c,fixture=True))['status']=='ALREADY_CURRENT'
   assert digest=={str(p):d.sha(p) for p in s.rglob('*') if p.is_file()}
  assert (s/'gamedata/state.json').read_bytes()==before['gamedata/state.json'] and (s/'gamedata/shop.json').read_bytes()==before['gamedata/shop.json']
 assert not(s/'.shop-release.lock').exists() and not(s/'.fo3-publish.lock').exists()
 checks.append('Transaction '+str(fail)+' rollback/success, assets preserved, lock release/idempotency')
s,c=fixture('lock');(s/'.shop-release.lock').write_bytes(b'other owner')
try:
 with d.locks(s):raise AssertionError('should not acquire')
except FileExistsError:pass
assert (s/'.shop-release.lock').read_bytes()==b'other owner';checks.append('Other writer lock never removed')
s,c=fixture('drift');p=d.plan(s,c,fixture=True);(s/'http_config.py').write_text('new legal change')
try:d.apply(p);raise AssertionError('should reject drift')
except RuntimeError:pass
assert (s/'http_config.py').read_text()=='new legal change';checks.append('Fresh target drift refused, later change preserved')
try:d.plan(Path(r'D:\FO3ID'),Path(r'D:\FO3ID\32795'),fixture=True);raise AssertionError('should reject fixture escape')
except RuntimeError:pass
checks.append('Fixture path escape refused')
(R/'install-tests.json').write_bytes(d.encoded(dict(status='PASS',checks=checks,count=len(checks),formal_written=False)))
print(json.dumps(dict(status='PASS',count=len(checks))))
