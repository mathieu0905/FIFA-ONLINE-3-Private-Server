from pathlib import Path
O=Path(__file__).parent
s=(O/'test_batch_install.py').read_text('utf8').replace("SCRIPT=O/'install_batch.py'","SCRIPT=O/'install_quantity.py'")
s=s.replace("source=SCRIPT.read_text('utf8')", "source=(O/'install_batch.py').read_text('utf8')")
s=s.replace("'EXP_BATCH_PREFLIGHT_PASS'","'EXP_QUANTITY_PREFLIGHT_PASS'")
s=s.replace("'batch-bound-v1'","'batch-text-v3'").replace("O/'batch-bound-v1/TeamManagementExpCapsuleScreen.big'","O/'batch-text-v3/TeamManagementExpCapsuleScreen.big'")
s=s.replace("(realS/'backups/xp30-batch-module-20261106-145705-239491/6.backup').read_bytes()", "(O/'batch-bound-v1/TeamManagementExpCapsuleScreen.big').read_bytes()")
s=s.replace("(O/'batch-install-tests.json')","(O/'quantity-install-tests.json')")
s=s.replace("    baseline={str(p)","    (m.S/'docs').mkdir();(m.S/'docs/工程经验与修改边界.txt').write_text('fixture ledger')\n    (m.O/'quantity-ledger.txt').write_bytes((O/'quantity-ledger.txt').read_bytes())\n    baseline={str(p)")
exec(compile(s,'<quantity page temporary publisher regression>','exec'),{'__file__':str(O/'test_quantity_install.py')})
