"""Incremental child that replaces only the confirmed failing 2555 EXP page."""
from pathlib import Path
src=(Path(__file__).parent/'install_batch.py').read_text('utf8')
src=src.replace("EXPECTED_PAGE='2555f22d92b0e7b0bcc29da37be1e1082271bdcad7d38dda6ba290e29fd0644c'", "EXPECTED_PAGE='e8c1e7cc0d0b69027f2b04d1dd8eac5ffcf8ea58805154a0404d03969fae826a'")
src=src.replace("assert sha(page)=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8'", "assert sha(page)=='2555f22d92b0e7b0bcc29da37be1e1082271bdcad7d38dda6ba290e29fd0644c'")
src=src.replace("O/'batch-bound-v1'","O/'batch-text-v3'")
src=src.replace('exp_batch_preflight','exp_quantity_preflight').replace('exp-batch-installed','exp-quantity-installed').replace('exp-batch-receipt','exp-quantity-receipt').replace('INSTALLED_EXP_BATCH','INSTALLED_EXP_QUANTITY').replace('EXP_BATCH_PREFLIGHT_PASS','EXP_QUANTITY_PREFLIGHT_PASS')
src=src.replace("(O/'batch-install-result.json')","(O/'quantity-install-result.json')")
src=src.replace("    guards=composition['guards'];seen=set()", "    ledger=S/'docs/工程经验与修改边界.txt'\n    files[ledger]=ledger.read_bytes()+b'\\r\\n'+(O/'quantity-ledger.txt').read_bytes()\n    guards=composition['guards'];seen=set()")
exec(compile(src,str(__file__)+':atomic-publisher','exec'),globals())
