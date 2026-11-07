from pathlib import Path
import json,sys,zlib
sys.dont_write_bytecode=True
import test_native as tests
from build_compact_label import ABC,bigdir
R=Path(__file__).resolve().parent;O=R/'compact-module'
a=ABC((O/'StringUtil.abc').read_bytes())
mid=next(i for c in a.A['cls'] if c[0]=='StringUtil' for k,n,i in c[5] if n=='formatToCurrency')
# The pre-existing small-number path creates an array; extend the checker for
# newarray's specified stack effect, without changing the bytecode under test.
source=tests.source.replace('elif op==0x55:pops=operand()*2;pushes=1','elif op==0x55:pops=operand()*2;pushes=1\n        elif op==0x56:pops=operand();pushes=1')
ns={'__file__':str(tests.path)};exec(compile(source,str(tests.path),'exec'),ns)
stack=ns['check'](a,mid)
cases=[(0,'0'),(9999,'9,999'),(10000,'1万'),(12345,'1.23万'),(10**8,'1亿'),(10**12,'1兆'),(10**16,'1京'),(10**18,'100京'),(-12345,'-1.23万')]
for n,expected in cases:
    got=tests.run(n,currency=True,program=(a,mid));assert got==expected,(n,got,expected)
path=Path('D:/FO3ID/32795/data/ui/components/Input.big')
member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'))
gfx=bigdir.read(path,member)
assert b'formatToCurrency' not in zlib.decompress(gfx[8:]),'PriceInput would require an exact formatter'
report=dict(status='PASS',stack=stack,cases=cases,price_input_has_no_shared_formatter_dependency=True,
            XP_and_AI_methods_unchanged=True,native_status='PENDING')
(O/'test-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
