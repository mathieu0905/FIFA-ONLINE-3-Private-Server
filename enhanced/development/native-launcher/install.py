"""Reuse the release transaction with an additive native-launcher payload."""
from pathlib import Path
O=Path(__file__).parent
src=(O.parent/'evidence/exp-select-20261106/install_batch.py').read_text('utf8')
start=src.index("    page=C/'data/ui/")
end=src.index("    guards=composition['guards'];seen=set()",start)
replacement='''    code=(S/'patches/exp_selection_preflight.py').read_text('utf8')
    code=code.replace('exp-selection-installed.json','exp-batch-installed.json').replace('exp-selection-receipt.json','exp-batch-receipt.json').replace('exp_selection_preflight.py','exp_batch_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_EXP_BATCH').replace('EXP_SELECTION_PREFLIGHT_PASS','EXP_BATCH_PREFLIGHT_PASS')
    compile(code,str(S/HELPER),'exec')
    files={S/'launcher/FO3Control.exe':(O/'FO3Control.exe').read_bytes(),S/'launcher/fo3_control.py':(O/'fo3_control.py').read_bytes(),S/'launcher/Fo3Control.cs':(O/'Fo3Control.cs').read_bytes(),S/HELPER:code.encode(),play:raw.replace(matches[0].group(1),HELPER.replace('/','\\\\').encode())}
    ledger=S/'docs/工程经验与修改边界.txt'
    files[ledger]=ledger.read_bytes()+b'\\r\\n'+(O/'ledger.txt').read_bytes()
'''
src=src[:start]+replacement+src[end:]
src=src.replace("assert sha(C/'data/ui/TeamManagementExpCapsuleScreen.big')==EXPECTED_PAGE", "assert sha(S/'launcher/FO3Control.exe')==sha(O/'FO3Control.exe')")
src=src.replace('exp_batch','native_launcher').replace('exp-batch','native-launcher').replace('EXP_BATCH','NATIVE_LAUNCHER')
src=src.replace("batch_scope='minus, plus, typed quantity, maximum, unified preview, expected snapshot, authoritative after/count'", "launcher_scope='Separate server/client actions, no batch execution, dynamic current gate, independent player import check'")
src=src.replace("(O/'batch-install-result.json')","(O/'install-result.json')")
exec(compile(src,str(__file__)+':release-transaction','exec'),globals())
