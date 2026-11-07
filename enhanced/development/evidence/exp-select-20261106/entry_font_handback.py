from pathlib import Path
import json
O=Path(__file__).parent
s=(O/'quantity_handback.py').read_text('utf8')
s=s.replace('exp_quantity','exp_entry_font').replace('exp-quantity','exp-entry-font').replace('EXP_QUANTITY','EXP_ENTRY_FONT').replace('quantity-install-result','entry-font-install-result').replace('quantity-handback','entry-font-handback')
exec(compile(s,'<entry-font installed handback>','exec'),{'__file__':str(__file__)})
p=O/'entry-font-status.json';r=json.loads(p.read_text('utf8'))
r.update(status='INSTALLED_NATIVE_PENDING',installed=True,production_files_written=True,observed_game_pid=None,next='User manually tests page entry, player selection, quantity and preview; no real use required')
p.write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8')
