from pathlib import Path
import json, struct,sys,re
sys.path[:0]=['D:/fifaol3/new-player-models/home-black-screen','D:/fifaol3/analysis_deps']
from minidump_read import Dump
import capstone
R=Path(__file__).resolve().parent
d=Dump(R/'official-game-78636-20261107-234634.dmp')
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for addr,size in [(0x613860,100),(0x5f0400,200),(0x5f1ac0,160),(0x5f1d50,180)]:
    print('\nCODE',hex(addr))
    print('\n'.join(f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in cs.disasm(d.read(addr,size),addr)))
found=[]
for needle in [b'VerifyError',b'Error #',b'exception',b'Exception',b'no such table',b'SELECT * FROM trainingteamplayers',b'Error:']:
    pos=0;hits=[]
    while len(hits)<35:
        pos=d.data.find(needle,pos)
        if pos<0:break
        hits.append(dict(offset=hex(pos),text=repr(d.data[max(0,pos-40):pos+200])));pos+=len(needle)
    found.append(dict(needle=needle.decode(),hits=hits))
(R/'dump-strings.json').write_text(json.dumps(found,indent=2),'utf8')
# AV EXCEPTION_RECORD candidates: distinguish real allocated record from constants/code.
pattern=struct.pack('<II',0xc0000005,0)
pos=0;exceptions=[]
while True:
    pos=d.data.find(pattern,pos)
    if pos<0:break
    try:
        code,flags,chain,addr,n=struct.unpack_from('<5I',d.data,pos)
        if 0x400000<=addr<0x2146000 and n==2:
            exceptions.append(dict(offset=hex(pos),address=hex(addr),params=list(struct.unpack_from('<2I',d.data,pos+20)),raw=d.data[pos:pos+80].hex()))
    except struct.error:pass
    pos+=8
print('EXCEPTIONS',json.dumps(exceptions[:25]))
(R/'exception-candidates.json').write_text(json.dumps(exceptions,indent=2),'utf8')
