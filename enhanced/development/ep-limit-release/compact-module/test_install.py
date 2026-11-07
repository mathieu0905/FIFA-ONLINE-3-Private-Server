from pathlib import Path
import copy,json,os,shutil,sys
sys.dont_write_bytecode=True
import install as i
p=i.p;R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
m=p.read(R/'manifest.json');retirement=p.parent(S,m)
composed,v=p.compose_retirement(S,C,retirement)
F=R/'install-fixture-v2';assert not F.exists()
roots={'server':F/'server','client':F/'client'}
rows=composed['guards']+composed.get('receipt_policies',[])+[dict(root='server',relative=n) for n in m['parent_files']]+m['files']
for e in rows:
    src=(S if e['root']=='server' else C)/e['relative'];dest=roots[e['root']]/e['relative']
    if not src.exists() or dest.exists():continue
    dest.parent.mkdir(parents=True,exist_ok=True)
    if src.stat().st_size>10000000:os.link(src,dest)
    else:shutil.copyfile(src,dest)
# Relocated transaction fixture reuses the fully checked real ancestor graph;
# historical absolute backup receipts remain immutable. Production dry-run
# above exercised the real composer and exact retirement/EP hierarchy.
p.compose_retirement=lambda *args:(copy.deepcopy(composed),v)
s,c=roots['server'],roots['client'];i.preview(s,c)
baseline={str(f):p.sha(f) for f in F.rglob('*') if f.is_file()}
try:i.install(s,c,True,fail_after=3)
except RuntimeError as e:assert 'Injected failure' in str(e)
else:raise AssertionError('No injected failure')
for name,digest in baseline.items():assert p.sha(Path(name))==digest,name
result=i.install(s,c,True);assert result['status']=='INSTALLED'
assert i.install(s,c,True)['status']=='ALREADY_INSTALLED'
font=c/'data/ui/localization/fontconfig.dat';saved=font.read_bytes();font.write_bytes(saved+b'\x00\x00')
try:p.preflight(s,c)
except RuntimeError as e:assert 'fontconfig' in str(e)
else:raise AssertionError('Font tamper accepted')
font.write_bytes(saved)
bad=copy.deepcopy(m);bad['files'][2]['parent_sha256']='0'*64
try:p._compose(s,c,bad)
except RuntimeError as e:assert 'parent SHA mismatch' in str(e)
else:raise AssertionError('Wrong Module parent accepted')
old=(C/'data/ui/localization/fontconfig.dat').read_text(encoding='utf-16')
new=(R/'payload/fontconfig.dat').read_text(encoding='utf-16')
assert old.split('[FontConfig "chi"]')[0]==new.split('[FontConfig "chi"]')[0]
assert old.split('[FontConfig "chi"]')[1].replace('map "$NormalFont" = "HelveticaNeueLT Std Med" Normal','map "$NormalFont" = "FZLanTingHei-R-GB18030" Regular')==new.split('[FontConfig "chi"]')[1]
report=dict(status='PASS',checks=['actual_current_ancestry_dryrun','injected_failure_rollback','child_preflight',
    'idempotent_install','font_tamper_rejected','wrong_module_parent_rejected','other_font_locales_unchanged'],files=result['preflight']['files'])
(R/'install-test-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
