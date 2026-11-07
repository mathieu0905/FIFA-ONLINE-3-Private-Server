from pathlib import Path
O=Path(__file__).parent
s=(O/'test_entry_font_install.py').read_text('utf8').replace('install_entry_font.py','install_loop_label.py').replace('entry-font-v4','loop-label-v5').replace('batch-text-v3','entry-font-v4').replace('EXP_ENTRY_FONT','EXP_LOOP_LABEL').replace('entry-font-install-tests','loop-label-install-tests').replace('entry-font-ledger','loop-label-ledger')
exec(compile(s,'<loop-marker temporary publisher regression>','exec'),{'__file__':str(__file__)})
