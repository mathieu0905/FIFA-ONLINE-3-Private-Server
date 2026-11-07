from pathlib import Path
import sys,zlib,re,json,sqlite3
sys.dont_write_bytecode=True
sys.path[:0]=['D:/FO3ID/server/tools/re','D:/fifaol3/season-display','C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_levels']
from avm_patch import ABC,dis
from build_moments_display import tags
import bigdir
ROOT=Path(__file__).resolve().parent
def inspect():
 out=ROOT/'inspection';out.mkdir(exist_ok=True)
 for path in Path('D:/FO3ID/32795/data/ui').rglob('*.big'):
  raw=path.read_bytes()
  m=re.search(rb'[CF]FX[\x08-\x20]',raw)
  if not m:continue
  try:
   gfx=raw[m.start():]; data=b'FWS'+gfx[3:8]+(zlib.decompress(gfx[8:]) if gfx[:1]==b'C' else gfx[8:])
   start=8+(5+4*(data[8]>>3)+7)//8+4
   for kind,body,_ in tags(data,start):
    if kind!=82:continue
    pos=body.index(b'\0',4)+1;a=ABC(body[pos:]); A=a.A
    for cls in A['cls']:
     if re.search('PlayerInfo|PlayerDetail|PlayerTrait|PlayerHistory|Speciality|Specialty|SquadScreenHandler|PlayerListUtil|Enums',cls[0],re.I):
      name=cls[0];print(path.name,name)
      lines=[str(cls)]
      for idx in [cls[2],cls[4]]+[t[2] for t in cls[3]+cls[5] if t[0] in ('method','get','set')]:
       if idx in A['body']:lines.extend(['\nMETHOD '+str(idx),*dis(A,A['body'][idx])])
      (out/(path.stem+'-'+name+'.txt')).write_text('\n'.join(lines),'utf8')
      (out/(path.stem+'-'+name+'.abc')).write_bytes(body[pos:])
  except Exception as e:print('ERROR',path,str(e))
 with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
  for name,sql in db.execute("select name,sql from sqlite_master where type='table'"):
   if re.search('trait|special|player|team',name,re.I):print(name,sql[:2500])
if __name__=='__main__':inspect()

