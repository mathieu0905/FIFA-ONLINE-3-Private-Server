from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'D:/fifaol3/new-player-models/home-black-screen')
from minidump_read import Dump
O=Path(__file__).parent/'entry-failure-v4'
small=Dump(O/'native.dmp');full=Dump('D:/fifaol3/new-player-models/home-black-screen/official-game-85916-20261107-012032.dmp')
a=small.read(0x791743,256);b=full.read(0x791743,256);assert a==b,'Historical code differs; cannot use as source for current fault'
code=full.read(0x760000,0x60000);target=O/'vm-code.bin';target.write_bytes(code)
(O/'code-source.json').write_text(json.dumps(dict(source=str(full.path),target=str(target),base='0x760000',length=len(code),sha256=hashlib.sha256(code).hexdigest(),fault_window_256_bytes_match=True,limitation='Historical read-only code, confirmed equal only within current dump 256-byte fault window; heap objects not transferable'),indent=2),'utf8')
print('Extracted historical VM code; current fault window byte-identical')
