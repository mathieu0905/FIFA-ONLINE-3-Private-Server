"""Bind the unchanged native UI contract to the server response/route fix."""
from pathlib import Path
import sys,zlib,json,hashlib
sys.dont_write_bytecode=True;sys.path.insert(0,'D:/fifaol3/enhancement-entry-fix')
from client_tools import ABC,tags,bigdir,dis
W=Path(__file__).resolve().parent;C=Path('D:/FO3ID/32795/data/ui');checks=[];hashes={}
def classes(name):
 p=C/(name+'.big');hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 for member,*_ in bigdir.entries(p):
  if not member.endswith('.gfx'):continue
  g=bigdir.read(p,member);s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4
  for kind,body,raw in tags(s,start,len(s)):
   if kind!=82:continue
   a=ABC(body[body.index(b'\0',4)+1:]);yield a.A
def check(ok,label):assert ok,label;checks.append(label)
proxy=next(a for a in classes('libs/Module') if any(r[0]=='TransferMarketProxy' for r in a['cls']))
row=next(r for r in proxy['cls'] if r[0]=='TransferMarketProxy');text='\n'.join(dis(proxy,proxy['body'][row[4]]))
check('pushstring "waiting"' in text and 'initproperty STATUS_SELLING' in text,'Actual native proxy defines in-sale wire status as waiting')
controller=next(a for a in classes('libs/Module') if any(r[0]=='TransferMarketController' for r in a['cls']))
row=next(r for r in controller['cls'] if r[0]=='TransferMarketController');methods={n:mid for k,n,mid in row[3] if k=='method'}
text='\n'.join(dis(controller,controller['body'][methods['doReCreateOffer']]))
check('pushstring "/transfer/offer/from/{0}"' in text and 'pushstring "price"' in text,'Native change-price request uses existing recreate path and price body')
text='\n'.join(dis(controller,controller['body'][methods['doCancelOffer']]))
check('/transfer/my/offer/' in text,'Native cancel path includes wire status; waiting route alias is necessary')
renderer=next(a for a in classes('components/ScrollingList') if any(r[0]=='TransferMarketOfferItemRenderer' and r[1]=='ListItemRenderer' for r in a['cls']))
text='\n'.join(dis(renderer,renderer['body'][3]))
check('pushstring "waiting"' in text and 'getproperty reregistrerButton' in text and 'getproperty cancelButton' in text,'Native hover already reveals change-price and cancel buttons for waiting listings')
source=(W/'market_simulation.py').read_text('utf8');import ast,re
tree=ast.parse(source);patterns=[n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='compile' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str)]
check(any(re.fullmatch(p,'/transfer/my/offer/waiting/card_1') for p in patterns),'Built native cancel route accepts unchanged waiting status and exact instance ID')
report=dict(status='PASS',count=len(checks),checks=checks,client_hashes=hashes,client_files_written=False,GUI_used=False,native_execution_verified=False)
(W/'native-contract.json').write_text(json.dumps(report,indent=2),'utf8');print('PASS',len(checks),'native contract checks')
