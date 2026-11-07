from pathlib import Path
O=Path(__file__).parent
s=(O/'install_entry_font.py').read_text('utf8')
s=s.replace("EXPECTED_PAGE='63531b563e2755064f17add12e5092092b38436d6165cc67abd393293485a0c1'","EXPECTED_PAGE='657e82a5e3af97869e85b4d0050e35a2717deda7e0c5f582b7be7d75bb77be04'")
s=s.replace("assert sha(page)=='e8c1e7cc0d0b69027f2b04d1dd8eac5ffcf8ea58805154a0404d03969fae826a'","assert sha(page)=='63531b563e2755064f17add12e5092092b38436d6165cc67abd393293485a0c1'")
s=s.replace('entry-font-v4','loop-label-v5').replace('exp_entry_font','exp_loop_label').replace('exp-entry-font','exp-loop-label').replace('EXP_ENTRY_FONT','EXP_LOOP_LABEL').replace('entry-font-install-result','loop-label-install-result').replace('entry-font-ledger','loop-label-ledger')
exec(compile(s,'<loop-marker atomic release>','exec'),globals())
