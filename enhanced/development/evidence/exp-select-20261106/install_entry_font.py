from pathlib import Path
src=(Path(__file__).parent/'install_batch.py').read_text('utf8')
src=src.replace("EXPECTED_PAGE='2555f22d92b0e7b0bcc29da37be1e1082271bdcad7d38dda6ba290e29fd0644c'","EXPECTED_PAGE='63531b563e2755064f17add12e5092092b38436d6165cc67abd393293485a0c1'")
src=src.replace("assert sha(page)=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8'","assert sha(page)=='e8c1e7cc0d0b69027f2b04d1dd8eac5ffcf8ea58805154a0404d03969fae826a'")
src=src.replace("O/'batch-bound-v1'","O/'entry-font-v4'")
src=src.replace('exp_batch','exp_entry_font').replace('exp-batch','exp-entry-font').replace('EXP_BATCH','EXP_ENTRY_FONT')
src=src.replace("(O/'batch-install-result.json')","(O/'entry-font-install-result.json')")
src=src.replace("    guards=composition['guards'];seen=set()", "    ledger=S/'docs/工程经验与修改边界.txt'\n    files[ledger]=ledger.read_bytes()+b'\\r\\n'+(O/'entry-font-ledger.txt').read_bytes()\n    guards=composition['guards'];seen=set()")
exec(compile(src,str(__file__)+':atomic-publisher','exec'),globals())
