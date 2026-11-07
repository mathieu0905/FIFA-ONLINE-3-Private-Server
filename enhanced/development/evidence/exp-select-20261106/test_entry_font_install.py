from pathlib import Path
O=Path(__file__).parent
s=(O/'test_batch_install.py').read_text('utf8').replace("SCRIPT=O/'install_batch.py'","SCRIPT=O/'install_entry_font.py'")
s=s.replace("source=SCRIPT.read_text('utf8')","source=(O/'install_batch.py').read_text('utf8')")
s=s.replace("'EXP_BATCH_PREFLIGHT_PASS'","'EXP_ENTRY_FONT_PREFLIGHT_PASS'")
s=s.replace("'batch-bound-v1'","'entry-font-v4'").replace("O/'batch-bound-v1/TeamManagementExpCapsuleScreen.big'","O/'entry-font-v4/TeamManagementExpCapsuleScreen.big'")
s=s.replace("(realS/'backups/xp30-batch-module-20261106-145705-239491/6.backup').read_bytes()","(O/'batch-text-v3/TeamManagementExpCapsuleScreen.big').read_bytes()")
s=s.replace("(O/'batch-install-tests.json')","(O/'entry-font-install-tests.json')")
s=s.replace("    baseline={str(p)","    (m.S/'docs').mkdir();(m.S/'docs/工程经验与修改边界.txt').write_text('fixture ledger')\n    (m.O/'entry-font-ledger.txt').write_bytes((O/'entry-font-ledger.txt').read_bytes())\n    baseline={str(p)")
exec(compile(s,'<font-entry temporary publisher regression>','exec'),{'__file__':str(__file__)})
