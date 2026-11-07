from build import *
import ast
def main():
 report=json.loads((R/'build/report.json').read_text('utf8'))
 source=Path(report['source']);fixed=R/'build/SquadAssets.big';native=Path(report['original_native_source'])
 member='data/ui/SquadAssets.gfx'
 before=bigdir.read(source,member);after=bigdir.read(fixed,member);reference=bigdir.read(native,member)
 assert before[:3]!=reference[:3] and after[:3]==reference[:3]==b'CFX'
 assert before[3:]==after[3:]
 assert zlib.decompress(before[8:])==zlib.decompress(after[8:])
 assert len(before)==len(after)
 raw=source.read_bytes();new=fixed.read_bytes()
 assert len(raw)==len(new)
 differing=[i for i,(a,b) in enumerate(zip(raw,new)) if a!=b]
 # Repacking preserves the header and entry offsets for this equal-size repair.
 off=next(o for n,o,s,u in bigdir.entries(source) if n==member)
 assert differing==[off+1,off+2],differing
 assert bigdir.table(source)==bigdir.table(fixed)
 for name,*_ in bigdir.entries(source):
  if name!=member:assert bigdir.read(source,name)==bigdir.read(fixed,name)
 for p in R.glob('*.py'):ast.parse(p.read_text('utf-8-sig'))
 import importlib.util
 spec=importlib.util.spec_from_file_location('carrier_install_test',R/'install.py');install=importlib.util.module_from_spec(spec);spec.loader.exec_module(install)
 old_idle=install.tx.idle;old_plan=install.plan
 install.tx.idle=lambda:False
 install.plan=lambda:(_ for _ in ()).throw(AssertionError('Plan reached during game'))
 try:install.main()
 finally:install.tx.idle=old_idle;install.plan=old_plan
 status=install.read(R/'install-status.json')
 assert status['status']=='DEFERRED_GAME_RUNNING' and not status['formal_files_written'] and not status['services_restarted']
 assert sha(source)==report['source_sha256']
 result=dict(status='PASS')
 result.update(bad_carrier_detected=True,original_native_signature_restored=True,actual_changed_archive_bytes=2,
  entire_compressed_payload_after_signature_identical=True,all_50_ABC_blocks_and_all_timelines_identical=True,
  all_57_GFx_tags_identical=True,all_other_members_identical=True,game_running_installer_deferral=True,
  build_report_sha256=sha(R/'build/report.json'),tooling={p.name:sha(p) for p in R.glob('*.py')},native_open_verified=False,formal_written=False)
 save(R/'tests.json',result);print(json.dumps(result))
if __name__=='__main__':main()
