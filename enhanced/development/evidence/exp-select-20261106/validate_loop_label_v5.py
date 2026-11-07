from pathlib import Path
O=Path(__file__).parent
s=(O/'validate_entry_font_v4.py').read_text('utf8').replace('entry-font-v4','loop-label-v5')
exec(compile(s,'<loop-marker CFG and business replay>','exec'),{'__file__':str(__file__)})
s=(O/'test_quantity_lifecycle.py').read_text('utf8').replace('batch-text-v3','loop-label-v5')
exec(compile(s,'<loop-marker early lifecycle replay>','exec'),{'__file__':str(__file__)})
