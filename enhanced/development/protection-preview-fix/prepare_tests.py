from pathlib import Path
R=Path(__file__).parent
s=Path(r'D:\fifaol3\enhancement-protection40\test_server.py').read_text('utf8')
s=s.replace("W=Path(r'D:\\fifaol3\\enhancement-protection40')", "W=Path(r'D:\\fifaol3\\protection-preview-fix')")
s=s.replace('import http_config as h', "spec=importlib.util.spec_from_file_location('enhancement_protection40',W/'enhancement_protection40.py');p=importlib.util.module_from_spec(spec);sys.modules['enhancement_protection40']=p;spec.loader.exec_module(p)\nimport http_config as h")
s=s.replace("spec=importlib.util.spec_from_file_location('protection40',W/'enhancement_protection40.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.install(h)", "assert h._protection40_installed")
s=s.replace("assert not preview(a,b)['result'] and Path(h.STATE).read_bytes()==raw", "q=preview(a,b);assert q['result'] and q['protection']['blocked'] and 'token' not in q['protection'] and q['enhancepay']==0 and Path(h.STATE).read_bytes()==raw")
s=s.replace("assert not q['result'] and q['protection']['blocked']", "assert q['result'] and q['protection']['blocked']")
s=s.replace("r['grade']==6", "r['grade']==h.enhancement_failure_grade(pa)")
# Keep updated price/rates checks; add exact failing grade pair, no-token execution,
# invalid target, old restore ownership, and cancellation before report emission.
at=s.index("result={'status':'PASS'")
extra='''
for g,m in ((8,6),(5,1),(10,1),(20,1)):
 a,b=fresh(g,m);raw=Path(h.STATE).read_bytes();q=call(f'/player/{a}/enhance2.5/{b}/preview/0/1000090/1001')
 assert q['result'] and q['protection']['blocked'] and not q['protection']['available'] and 'token' not in q['protection']
 assert q['enhancepay']==0 and q['protection']['fee']==0
 assert not call(f'/player/{a}/enhance2.5/{b}/0/1000090/1001')['result']
 assert Path(h.STATE).read_bytes()==raw
checks.append('Exact failing +8/+6 100% case and safe floors: successful nonpayable preview, no payment token, execution rejects, zero writes')
a,b=fresh();raw=Path(h.STATE).read_bytes();q=preview('000000000000000000000000',b)
assert q['result'] and q['protection']['blocked'] and Path(h.STATE).read_bytes()==raw
a,b=fresh();st=h._state();st['enhance_restore']={'id':a,'grade':8,'price':240};h._save(st);raw=Path(h.STATE).read_bytes();q=preview(a,b)
assert q['result'] and q['reason']=='RESTORE_PENDING' and q['protection']['can_restore'] and q['protection']['restore']['price']==240
assert q['protection']['discard_token'] and 'token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
st=h._state();st['enhance_restore']['id']='another-manager-card';h._save(st);raw=Path(h.STATE).read_bytes();q=preview(a,b)
assert q['result'] and q['reason']=='RESTORE_OTHER_MANAGER' and 'discard_token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
checks.append('Invalid selection and pending/other-manager restore are nonfatal blocked reads; signed explicit discard and original restore quote preserved')
'''
s=s[:at]+extra+s[at:]
(R/'test_server.py').write_text(s,encoding='utf8')


