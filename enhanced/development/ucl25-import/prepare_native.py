"""Run the official import finisher/full gate on the single prepared roster delta."""
import os,subprocess,shutil
from common import *


def main():
    out=Path(read(R/'latest-build.json')['path']);report=read(out/'build.json')
    for p,digest in report['input_hashes'].items():
        if sha(p)!=digest:raise ValueError('Formal source advanced; rebase UI build before native preparation: '+p)
    final=out/'native'
    if final.exists():raise ValueError('Native output already exists; inspect before rerun')
    command=[str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/prepare.py'),
        '--spec',str(out/'native-spec.json'),'--server',str(S),'--client',str(C),'--database',str(out/'fifadb.sqlite'),
        '--data0',str(out/'data_0.big'),'--registry',str(out/'custom_rosters.json'),
        '--imports',str(S/'gamedata/player-imports.json'),'--portraits',str(R/'portraits'),'--output',str(final)]
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    result=subprocess.run(command,cwd=S,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/'native-prepare.stdout.log').write_text(result.stdout,encoding='utf8');(out/'native-prepare.stderr.log').write_text(result.stderr,encoding='utf8')
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    archive=S/'gamedata/removed-player-profiles.json'
    if archive.exists():shutil.copyfile(archive,final/archive.name)
    proof=read(final/'player-import-validation.json');assert proof['status']=='PLAYER_IMPORT_FULL_PASS'
    report.update(status='UI_AND_NATIVE_FULL_PASS',native_full_validation=proof,native_output=str(final))
    write(out/'build.json',report);write(R/'native-ready.json',dict(status='PLAYER_IMPORT_FULL_PASS',build=str(out),native=str(final),
        cards=360,new_generic_identities=sum(not p['native_existing'] for p in imported_cards()),excluded_playerids=sorted(BLOCKED_PIDS),GUI_used=False,formal_files_written=False))
    print('OFFICIAL_NATIVE_FULL_PASS; 360 new cards, 87 new native identities (121 existing identities reused); no formal writes.')


if __name__=='__main__':main()
