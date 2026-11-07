"""Synthetic PE container for a historical code slice; never execute this artifact."""
from pathlib import Path
import struct
O=Path(__file__).parent/'entry-failure-v4';code=(O/'vm-code.bin').read_bytes();h=bytearray(512)
h[:2]=b'MZ';struct.pack_into('<I',h,0x3c,0x80);h[0x80:0x84]=b'PE\0\0'
struct.pack_into('<HHIIIHH',h,0x84,0x14c,1,0,0,0,224,0x102)
p=0x98;struct.pack_into('<H',h,p,0x10b);struct.pack_into('<I',h,p+4,len(code))
for off,value in ((16,0x360000),(20,0x360000),(28,0x400000),(32,0x1000),(36,0x200),(56,0x3c0000),(60,0x200),(72,0x100000),(76,0x1000),(80,0x100000),(84,0x1000),(92,16)):struct.pack_into('<I',h,p+off,value)
struct.pack_into('<H',h,p+40,6);struct.pack_into('<H',h,p+48,6);struct.pack_into('<H',h,p+68,3)
s=p+224;h[s:s+8]=b'.text\0\0\0';struct.pack_into('<IIII',h,s+8,len(code),0x360000,len(code),512);struct.pack_into('<I',h,s+36,0x60000020)
(O/'vm-analysis-only.exe').write_bytes(h+code)
