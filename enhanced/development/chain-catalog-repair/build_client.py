"""Place the shipped native button on the chain renderer timeline; repair category leakage."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));import avm_patch as avm
from avm_patch import ABC,Code,u30,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SOURCE=C/'data/ui/components/TileList.big';sha=lambda b:hashlib.sha256(b).hexdigest()
def body(a,mid,code):
 rec=a.A['body_records'][mid];f=list(rec['fields']);f[0]=max(32,f[0]);a.changed[mid]=u30(mid)+b''.join(u30(x) for x in f)+u30(len(code))+code+rec['suffix']
def matrix(x,y):
 bits='00';values=[round(x*20),round(y*20)];n=max(abs(v).bit_length()+1 for v in values);bits+=format(n,'05b')+''.join(format(v&((1<<n)-1),'0'+str(n)+'b') for v in values);bits+='0'*(-len(bits)%8);return int(bits,2).to_bytes(len(bits)//8,'big')
def add_slot(data,name,type_name):
 src=avm.SOURCE.replace('ii = r.u30(); inst.append([name, sup, ii, traits()])',"ii = r.u30(); tp=r.p; tr=traits(); A.setdefault('instance_trait_offsets',[]).append((tp,r.p)); inst.append([name,sup,ii,tr])")
 ns={'__name__':'trait_offsets'};exec(compile(src,'trait-offsets','exec'),ns);parsed=ns['parse'](data,0);start,end=parsed['instance_trait_offsets'][0];reader=avm.R(data,start);count=reader.u30();entries=reader.p
 return data[:start]+u30(count+1)+data[entries:end]+u30(name)+b'\x00'+u30(0)+u30(type_name)+u30(0)+data[end:]
def build():
 raw=SOURCE.read_bytes();member=next(n for n,*_ in bigdir.entries(SOURCE) if n.endswith('.gfx'));g=bigdir.read(SOURCE,member);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4;ts=list(tags(swf,start,len(swf)));core_count=timeline_count=0
 for ix,(t,b,r) in enumerate(ts):
  if t==82:
   pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
   if not cls or cls[0]!='ShopChainedListItemRenderer' or not any(x[1]=='_chainRoundState' for x in cls[3]):continue
   core_count+=1;state=a.name('_chainRoundState');slot=a.name('roundPurchaseButton');object_type=a.name('Object');prefix=a.A['body'][4][:206]
   def st(c):return c.local(0).op(0x66,state)
   def button(c):return c.local(0).op(0x66,slot)
   c=Code(a).local(1).jump(0x12,'done');button(c).jump(0x12,'done');st(c).jump(0x11,'exists')
   c.local(0).string('busy').op(0x27).string('quote').op(0x20).string('purchasePending').op(0x27).string('button');button(c);c.op(0x55,4).op(0x61,state)
   button(c).lex('ButtonEvent','scaleform.clik.events').prop('CLICK').op(0x40,16).call('addEventListener',2).op(0x29)
   button(c).op(0x26).set('preventAutosizing');button(c).op(0x27).set('focusable');button(c).number(190).number(27).call('setSize',2).op(0x29)
   c.label('exists');st(c);button(c);c.set('button');button(c).local(1).prop('round_buy_supported').op(0x76).set('visible');c.local(0).ownprop('countLabel').local(1).prop('round_buy_supported').op(0x96).set('visible')
   c.local(1).prop('round_buy_enabled').jump(0x12,'disabled');st(c).prop('busy').jump(0x11,'disabled');button(c).op(0x26).set('enabled');c.jump(0x10,'caption')
   c.label('disabled');button(c).op(0x27).set('enabled')
   c.label('caption');st(c).prop('purchasePending').jump(0x12,'normal');button(c).string('重试本轮购买').set('label');c.jump(0x10,'validate')
   c.label('normal');button(c).string('一键购买本轮').set('label');c.label('validate');button(c).call('validateNow',0).op(0x29);c.label('done').op(0x47);body(a,4,prefix+c.done())
   patched=add_slot(a.output(),slot,object_type);checked=ABC(patched);assert ('slot','roundPurchaseButton','Object') in checked.A['cls'][0][3]
   for mid,code in a.A['body'].items():
    if mid!=4:assert checked.A['body'][mid]==code
   (R/'list.updated.abc').write_bytes(patched);(R/'list-patched.txt').write_text('\n'.join(dis(checked.A,checked.A['body'][4])),encoding='utf8');ts[ix]=(82,b[:pos]+patched,tag(82,b[:pos]+patched))
  elif t==39 and struct.unpack_from('<H',b)[0]==873:
   frames=list(tags(b,4,len(b)));depth=max(struct.unpack_from('<H',bb,2 if tt==70 else 1)[0] for tt,bb,rr in frames if tt in (26,70))+1
   placement=bytes([0x24,0x08])+struct.pack('<H',depth)+b'ShopBuyButton\0'+matrix(1009,2)+b'roundPurchaseButton\0'
   inserted=False;parts=[]
   for tt,bb,rr in frames:
    if tt==1 and not inserted:parts.append(tag(70,placement));inserted=True
    parts.append(rr)
   assert inserted;newbody=b[:4]+b''.join(parts);ts[ix]=(39,newbody,tag(39,newbody));timeline_count+=1
 assert core_count==timeline_count==1
 s=bytearray(swf[:start]+b''.join(r for _,_,r in ts));struct.pack_into('<I',s,4,len(s));gfx=b'CFX'+s[3:8]+zlib.compress(s[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:gfx});assert bigdir.read(target,member)==gfx
 source=(S/'product_packs.py').read_bytes();needle=b"stages={int(i):(root,round_index,index) for root,t in tracks.items() for round_index,steps in enumerate(t['round_steps']) for index,i in enumerate(steps)}";assert source.count(needle)==1
 source2=source.replace(needle,needle+b"\r\n    chain_catalogue_ids=set(stages)|{int(i) for steps in h.CHAINED.values() for i in steps}")
 old=b"rows=[r for r in rows if r.get('shopid') not in tracks]";new=b"rows=[r for r in rows if r.get('shopid') not in tracks and int(r.get('product',{}).get('itemid',0)) not in chain_catalogue_ids]";assert source2.count(old)==1;source2=source2.replace(old,new);compile(source2,'product_packs.py','exec');(R/'product_packs.py').write_bytes(source2)
 report=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha(source),server_after=sha(source2),native_button_class='ShopBuyButton',button_binding='PlaceObject3 timeline instance with declared public slot',timeline_depth=depth,all_other_methods_including_completion_and_purchase_callbacks_identical=True,native_verified=False)
 (R/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':build()
