from pathlib import Path
import sys,json,math,types,urllib.parse
sys.dont_write_bytecode=True
W=Path(__file__).parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(T))
from avm_patch import ABC,R,instructions
s=Path(r'D:\fifaol3\enhancement-font-fix\test_ui.py').read_text('utf8').split("a=ABC((W/")[0]
ns={'__file__':str(W/'test_client.py')};exec(s,ns);VM=ns['VM'];U=ns['U']
# The layout uses a numeric division solely to vertically center its text.
code=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client\test_bp_client.py').read_text('utf8')
# Extend the already established replay interpreter without running old tests.
src=ns['s'].replace("elif op==0xa1:","elif op==0xa3:b=pop();a=pop();stack.append(a/b)\n            elif op==0xa1:")
ns['urllib']=types.SimpleNamespace(parse=urllib.parse)
exec(src,ns);VM=ns['VM'];U=ns['U']
a=ABC((W/'TeamManagementPlayerEnhancementTabPage-after.abc').read_bytes());p=ABC((W/'TeamManagementPlayerEnhancingPopupScreen-after.abc').read_bytes())
cp=json.loads((W/'TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text());pp=json.loads((W/'TeamManagementPlayerEnhancingPopupScreen-ABC.patch.json').read_text())
meta=json.loads((W/'client-build.json').read_text())

def display():
 children={};draw=[];events={};obj={'_children':children,'_draw':draw,'_events':events}
 obj.update(getChildByName=lambda n:children.get(n,U),addChild=lambda c:children.setdefault(c['name'],c),addEventListener=lambda n,f:events.setdefault(n,f))
 obj['graphics']={n:(lambda *args,n=n:draw.append((n,args))) for n in ('clear','beginFill','endFill','lineStyle','drawRect','drawRoundRect','moveTo','lineTo')}
 return obj
def vm_for(abc,owner):
 vm=VM(abc,owner);vm.globals.update(Sprite=display,MovieClip=display,isFinite=math.isfinite);return vm
def insertion(abc,patch,mid,old,owner,args=(),locals_override=None):
 row=patch[str(mid)];mapping={int(k):v for k,v in row['mapping'].items()};original=bytes.fromhex(row['original']);end=next(e for at,e,op,t in instructions(original) if at==old);stop=mapping[end]-(end-old)
 vm=vm_for(abc,owner);result=vm.run(mid,args,start=mapping[old],stop=stop,locals_override=locals_override);assert not vm.puts
 return vm,result

rate=display();rate['_children']['__id7_']={'text':'成功率'};rate['rateContainer']={'x':-1,'y':40,'width':180,'height':90,'visible':True}
owner=display();owner.update(_owner={'infoPanel':{'enhanceRate':rate}},_preview=None,_available=True,_selectItem={'value':1000052},_selectedTargets=[{'_id':'main'},{'_id':'material'}])
for value in (0,0.001,3.3,16.5,91.25,99.999,100):
 owner['_preview']={'probability':value};insertion(a,cp,32,7,owner)
 field=rate['_children']['fo3EnhanceProbability'];assert field['text']==format(value,'.15g')+'%'
assert not field['border'] and not field['background'] and field['embedFonts']
assert field['defaultTextFormat']['font']=='$NormalFont' and field['defaultTextFormat']['size']==32
assert field['x']==-1 and field['y']==62 and field['width']==180 and field['height']==46
plate=rate['_children']['fo3ProbabilityPlate'];assert ('drawRoundRect',(0,0,180,90,14,14)) in plate['_draw']
assert rate['rateContainer']['visible'] is False and len(rate['_children'])==3

init_old=cp['8']['insertion_offsets'][0];insertion(a,cp,8,init_old,owner)
box=owner['_children']['fo3ProtectionCheckbox'];assert not box['selected'] and not box['enabled']
assert box['x']==30 and box['y']==50 and box['_children']['fo3ProtectionCaption']['embedFonts']
assert '强化保护' in box['_children']['fo3ProtectionCaption']['text']
insertion(a,cp,8,init_old,owner);assert owner['_children']['fo3ProtectionCheckbox'] is box
enable_old=cp['26']['insertion_offsets'][0];insertion(a,cp,26,enable_old,owner);assert box['enabled']

def preview_uri():
 native=f"/player/main/enhance2.5/material/preview/0/{owner['_selectItem']['value']}/-1"
 row=cp['38'];original=bytes.fromhex(row['original']);ret=row['insertion_offsets'][0];previous=max(at for at,e,op,t in instructions(original) if at<ret)
 vm=vm_for(a,owner);return vm.run(38,start=row['mapping'][str(previous)],locals_override={4:native})
requests=[];owner['requestPreview']=lambda:requests.append(preview_uri())
assert preview_uri().endswith('/1000052/-1')
callback=meta['TeamManagementPlayerEnhancementTabPage']['callbacks']['toggle_callback']
vm=vm_for(a,owner);vm.run(callback,({'currentTarget':box},));assert box['selected'] and box['_children']['fo3ProtectionMark']['visible']
assert requests[-1].endswith('/1000052/-1?protection=1') and owner['_selectItem']['value']==1000052 and not vm.puts
owner['first'],owner['second']=owner['_selectedTargets'];owner['previewUri']=requests[-1];owner['generatePreviewURI']=lambda first,second:preview_uri()
_,result=insertion(a,cp,34,0,owner);assert result=='RESUME'
vm.run(callback,({'currentTarget':box},));assert not box['selected'] and requests[-1].endswith('/1000052/-1')
_,result=insertion(a,cp,34,0,owner);assert result is None,'Old checked response must be ignored after uncheck'
box['selected']=True;box['_children']['fo3ProtectionMark']['visible']=True
insertion(a,cp,18,7,owner);assert not box['selected'] and not box['_children']['fo3ProtectionMark']['visible']
owner['_available']=False;before=len(requests);vm.run(callback,({'currentTarget':box},));assert len(requests)==before

prate=display();prate['_children']['__id15_']={'text':'成功率'};prate['rateContainer']={'x':15,'y':30,'width':250,'height':100,'visible':True}
popup={'boostInfoPanel':{'boostInfoContainer':{'boostRate':prate}}};end=pp['25']['insertion_offsets'][0]
insertion(p,pp,25,end,popup,({'cmd':'setData','info':{'probability':31.5}},));pf=prate['_children']['fo3EnhanceProbability']
assert pf['text']=='31.5%' and pf['y']==48 and pf['height']==64 and not pf['border'] and not pf['background']
assert prate['rateContainer']['visible'] is False and ('drawRoundRect',(0,0,250,100,14,14)) in prate['_children']['fo3ProbabilityPlate']['_draw']
data={'firstPlayer':{'_id':'main'},'secondPlayer':{'_id':'material','spid':1},'usePoint':True,'boostItemId':1000052,'boostEventId':-1,'info':{'protection':{'version':'protection40-v2-stack','token':'test-token'}},'_bpConfirmed':True}
o={'_data':data,'_version':'v2_5','_restoreStep':0,'_enableBoostItem':False,'_enableGuardItem':False}
uri=vm_for(p,o).run(31);query=urllib.parse.parse_qs(urllib.parse.urlsplit(uri).query)
assert '/1/1000052/-1?' in uri and query['protection_ack']==['protection40-v2-stack'] and query['protection_token']==['test-token']
guard=vm_for(a,{'_preview':{'protection':{'blocked':True,'label':'请取消勾选强化保护'}}});guard.run(20,start=7);assert not guard.puts and guard.dialogs

# All old non-rendering instructions and payment/restore/token routines survive.
for name,abc,patch in [('TeamManagementPlayerEnhancementTabPage',a,cp),('TeamManagementPlayerEnhancingPopupScreen',p,pp)]:
 before=ABC((W/(name+'-before.abc')).read_bytes())
 for mid in ([20,22,36,37] if name.endswith('TabPage') else [18,31,33,36,37,63]):assert before.A['body_records'][mid]['raw']==abc.A['body_records'][mid]['raw']
 for mid,row in patch.items():
  old=bytes.fromhex(row['original']);new=abc.A['body'][int(mid)];mapping={int(k):v for k,v in row['mapping'].items()};newins={at:(end,op,targets) for at,end,op,targets in instructions(new)}
  for at,e,op,targets in instructions(old):
   actual=mapping[e]-(e-at);ne,no,nt=newins[actual]
   if no!=op:assert (op,no)==(0x27,0x26) and actual in meta[name]['embed_font_flags'].get(mid,[])
   elif targets is not None:assert nt==[mapping[t] for t in targets]
   else:assert old[at:e]==new[actual:ne]
r=dict(status='PASS',rounded_panel_and_centered_embedded_percentage=True,no_square_textfield_border_or_old_arrow=True,independent_checkbox_and_gold_selection_preserved=True,checkbox_quote_flag_and_signed_gold_execution_uri=True,default_unchecked_and_busy_lock_and_reset=True,stale_checked_response_ignored_after_uncheck=True,blocked_click_zero_put=True,payment_restore_and_existing_button_fix_preserved=True,native_verified=False)
(W/'client-tests.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
