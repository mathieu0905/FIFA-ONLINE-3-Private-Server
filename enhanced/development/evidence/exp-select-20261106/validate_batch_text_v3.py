from pathlib import Path
O=Path(__file__).parent
s=(O/'validate_batch_text.py').read_text('utf8')
s=s.replace("s=s.replace(anchor,", "s=s.replace(\"P=O/'batch-text-v2'\",\"P=O/'batch-text-v3'\")\ns=s.replace(anchor,")
s=s.replace("O/'batch-text-v2/", "O/'batch-text-v3/")
exec(compile(s,'<guarded TextField quantity validation>','exec'),{'__file__':str(O/'validate_batch_text_v3.py')})
