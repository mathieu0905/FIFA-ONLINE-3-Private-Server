from pathlib import Path
O=Path(__file__).parent
# The CFG source is loaded one level deeper; inject its benign NOP definition there.
base=(O/'validate_batch_bound.py').read_text('utf8')
base=base.replace("ns={};exec(compile(s", "s=s.replace('0xf0,0xf1,0x09,0xef','0xf0,0xf1,0x02,0x09,0xef')\nns={};exec(compile(s")
base=base.replace("P=O/'batch-bound-v1'","P=O/'entry-font-v4'")
base=base.replace('get(\'enabled\') for n in','get(\'mouseEnabled\') for n in')
base=base.replace("exec(compile(s,'<bound actual bytecode replay>'", "s=s.replace(\"['fo3ExpPlus']['enabled']\",\"['fo3ExpPlus']['mouseEnabled']\")\ns=s.replace(\"get('enabled') for n in\",\"get('mouseEnabled') for n in\")\nexec(compile(s,'<bound actual bytecode replay>'")
exec(compile(base,'<entry v4 CFG and business replay>','exec'),{'__file__':str(__file__)})
