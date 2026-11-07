from pathlib import Path
import sys,json,math,types
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(T))
from avm_patch import ABC,R,instructions
s=(T/'test_bp_client.py').read_text(encoding='utf-8');s=s[s.index('class Undefined:'):s.index('\ndef load(name):')]
s=s.replace("elif op==0x96:stack.append(not truth(pop()))", "elif op==0x95:\n                v=pop();stack.append('undefined' if v is U else 'boolean' if isinstance(v,bool) else 'number' if isinstance(v,(int,float)) else 'string' if isinstance(v,str) else 'object')\n            elif op==0x96:stack.append(not truth(pop()))\n            elif op in (0xad,0xaf):\n                b=pop();a=pop();stack.append(a<b if op==0xad else a>b)")
s=s.replace("return lambda:str(o)","return lambda:format(o,'.15g') if isinstance(o,(int,float)) and not isinstance(o,bool) else str(o)")
ns=dict(ABC=ABC,R=R,instructions=instructions,Path=Path,sys=sys,json=json,struct=__import__('struct'),copy=__import__('copy'),zlib=__import__('zlib'),urllib=__import__('urllib.parse',fromlist=['parse']),hashlib=__import__('hashlib'))
# The VM's network helper is never invoked by the numeric display injections.
ns['urllib']=types.SimpleNamespace(parse=__import__('urllib.parse',fromlist=['quote']))
s=s.replace("elif op in (0xad,0xaf):", "elif op in (0xad,0xaf,0xb0):").replace("a<b if op==0xad else a>b", "a<b if op==0xad else a>b if op==0xaf else a>=b")
s=s.replace("elif op==0x66:k=name();stack.append(self.get(pop(),k))", "elif op==0x66:\n                k=name()\n                if k=='[late]':key=pop();obj=pop();stack.append(obj[key])\n                else:stack.append(self.get(pop(),k))")
exec(s,ns);VM=ns['VM'];U=ns['U']
a=ABC((W/'TeamManagementPlayerEnhancementTabPage-after.abc').read_bytes());p=ABC((W/'TeamManagementPlayerEnhancingPopupScreen-after.abc').read_bytes());cp=json.loads((W/'TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text());pp=json.loads((W/'TeamManagementPlayerEnhancingPopupScreen-ABC.patch.json').read_text())
def run_insertion(abc,patch,mid,old,owner,args=()):
 vm=VM(abc,owner);vm.globals['isFinite']=math.isfinite
 row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()};original=bytes.fromhex(row['original']);end=next(e for at,e,_,_ in instructions(original) if at==old);stop=mapping[end]-(end-old)
 vm.run(mid,args,start=mapping[old],stop=stop);assert not vm.puts
 return vm
children={'__id7_':{'text':'成功率加成'}}
container={'getChildByName':lambda name:children.get(name,U),'addChild':lambda child:children.setdefault(child['name'],child)}
owner={'_owner':{'infoPanel':{'enhanceRate':container}},'textContainer':{},'_preview':None}
def render(value):
 owner['_preview']=value;return run_insertion(a,cp,32,7,owner)
def text():return children['fo3EnhanceProbability']['text']
checks=[]
for rate in (0,3,3.3,15,16.5,100,0.001,99.999):
 render({'probability':rate});assert text()==format(rate,'.15g')+'%',text()
assert len(children)==2 and children['__id7_']['text']=='成功率'
checks.append('Eight numeric cases retain 0%, 100% and fractional precision; one reused TextField')
for data in (None,{}, {'probability':None},{'probability':'15'},{'probability':float('nan')},{'probability':float('inf')},{'probability':-1},{'probability':101},{'probability':True}):
 render(data);assert text()=='-',text()
checks.append('Nine absent/invalid/nonfinite/out-of-range cases render dash, never stale chance or NaN')
render({'probability':100,'protection':{'blocked':True,'label':'该组合不需付费保护'}});assert text()=='100%'
assert owner['_preview']['protection']['label']=='该组合不需付费保护'
checks.append('Blocked protection retains actual 100% and nonfatal business label; UI does not invent free/paid action')
for mid,offset,want in ((35,119,'...'),(18,7,'-'),(25,7,'-')):
 render({'probability':16.5});run_insertion(a,cp,mid,offset,owner);assert text()==want,text()
checks.append('New request, reset and changed pair clear previous percentage immediately')
field=children['fo3EnhanceProbability'];assert (field['x'],field['y'],field['width'],field['height'])==(0,36,180,40)
assert field['selectable'] is False and field['mouseEnabled'] is False and field['embedFonts'] is True
assert field['border'] and field['background'] and field['defaultTextFormat']['font']=='$NormalFont' and field['defaultTextFormat']['size']==24 and field['defaultTextFormat']['align']=='center'
checks.append('Native bonus-section owner.infoPanel.enhanceRate parent, outlined 180x40 field at x0/y36; registered embedded $NormalFont instead of device Arial; field never intercepts mouse')
assert text().isascii()
for missing in ({},{'_owner':None},{'_owner':{'infoPanel':None}},{'_owner':{'infoPanel':{'enhanceRate':None}}}):
 run_insertion(a,cp,32,7,missing)
checks.append('Missing native owner/panel/bonus section is a null-safe no-op')
# Verify both source-to-popup values and clearing on re-use.
pset={'__id15_':{'text':'成功率加成'}};parent={'getChildByName':lambda name:pset.get(name,U),'addChild':lambda child:pset.setdefault(child['name'],child),'rateContainer':{'x':15,'y':30,'width':250,'height':100,'visible':True}}
popup={'boostInfoPanel':{'boostInfoContainer':{'boostRate':parent}}}
end=next(iter(pp['25']['insertion_offsets']))
for rate in (0,16.5,3.3,100):
 run_insertion(p,pp,25,end,popup,({'cmd':'setData','info':{'probability':rate}},));assert pset['fo3EnhanceProbability']['text']==format(rate,'.15g')+'%'
run_insertion(p,pp,25,end,popup,({'cmd':'setData','info':{}},));assert pset['fo3EnhanceProbability']['text']=='-'
assert pset['fo3EnhanceProbability']['y']==45 and pset['fo3EnhanceProbability']['height']==70
assert pset['fo3EnhanceProbability']['x']==15 and pset['fo3EnhanceProbability']['width']==250
assert parent['rateContainer']['visible'] is False and pset['__id15_']['text']=='成功率'
assert pset['fo3EnhanceProbability']['border'] and pset['fo3EnhanceProbability']['background']
assert pset['fo3EnhanceProbability']['defaultTextFormat']['size']==40 and pset['fo3EnhanceProbability']['text'].isascii()
checks.append('Exact screenshot confirmation section boostInfoPanel.boostInfoContainer.boostRate: hide arrow, rename original title, centered bordered numeric box; same preview value and reuse clearing')
for missing in ({},{'boostInfoPanel':None},{'boostInfoPanel':{'boostInfoContainer':None}},{'boostInfoPanel':{'boostInfoContainer':{'boostRate':None}}}):
 run_insertion(p,pp,25,end,missing,({'cmd':'setData','info':{'probability':15}},))
checks.append('Missing popup bonus section safely skips rendering')
vm=VM(a,{'_preview':{'probability':100,'protection':{'blocked':True,'label':'该组合不需付费保护'}},'updateTextLabel':lambda:None});vm.run(20,start=7);assert not vm.puts and vm.dialogs
checks.append('Actual current onClickEnhanceButton blocked guard still shows label with zero PUT')
font_report=json.loads((W/'build.json').read_text())
for name,abc,patch in [('TeamManagementPlayerEnhancementTabPage',a,cp),('TeamManagementPlayerEnhancingPopupScreen',p,pp)]:
 before=ABC((W/(name+'-before.abc')).read_bytes())
 for mid in ([20,34,38,39,41,42,43,44] if name.endswith('TabPage') else [18,31,33,36,37,63]):
  assert before.A['body_records'][mid]['raw']==abc.A['body_records'][mid]['raw']
 for mid,row in patch.items():
  old=bytes.fromhex(row['original']);new=bytes.fromhex(row['updated']);mapping={int(k):v for k,v in row['mapping'].items()};newins={at:(end,op,targets) for at,end,op,targets in instructions(new)}
  for at,end,op,targets in instructions(old):
   actual=mapping[end]-(end-at);ne,no,nt=newins[actual];assert no==op or (op==0x27 and no==0x26 and actual in font_report[name]['embed_font_flags'].get(mid,[]))
   if targets is not None:assert nt==[mapping[t] for t in targets]
   elif no==op:assert old[at:end]==new[actual:ne]
checks.append('Only approved embedFonts flags change in original display code; payment, confirmation, restore, blocked and signed-token callback records stay exact')
r=dict(status='PASS',checks=checks,native_pass=False,formal_files_written=False)
(W/'tests.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=True,indent=2))

