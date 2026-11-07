"""Exact new bodies; distinguish lexical captures from instance this-scope."""
from pathlib import Path
import sys,json,copy,math,types,urllib.parse
sys.dont_write_bytecode=True
W=Path(__file__).parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(T))
from avm_patch import ABC,R,instructions
base=Path(r'D:\fifaol3\protection-checkbox\test_client.py').read_text('utf8').split("\na=ABC((W/")[0]
ns={'__file__':str(W/'test_client.py')};exec(base,ns)
src=ns['src']
src=src.replace('stack=[];locals=',"stack=[];scopes=[self.owner] if getattr(self,'captured',False) else [];locals=")
src=src.replace("elif op in (0x30,0x1c):pop()", "elif op in (0x30,0x1c):scopes.append(pop())")
src=src.replace("elif op in (0x09,0x1d):pass", "elif op==0x09:pass\n            elif op==0x1d:scopes.pop()")
src=src.replace("k=name();stack.append(self.owner if k in self.owner else self.globals)","k=name();target=next((o for o in reversed(scopes) if isinstance(o,dict) and k in o),None)\n                if target is None:\n                    if k not in self.globals:raise LookupError('No instance in lexical scope: '+k)\n                    target=self.globals\n                stack.append(target)")
src=src.replace("elif op==0x96:","elif op in (0x91,0xc0):stack.append(pop()+1)\n            elif op==0x96:")
src=src.replace('elif 0x10<=op<=0x1a:', 'elif 0x0e<=op<=0x1a:')
src=src.replace('elif op==0x09:pass', 'elif op==0x08:locals[r.u30()]=U\n            elif op==0x09:pass')
src=src.replace("elif op in (0x11,0x12):jump=truth(pop())==(op==0x11)","elif op in (0x11,0x12):jump=truth(pop())==(op==0x11)\n                elif op==0x0e:b=pop();a=pop();jump=not a>b\n                elif op==0x0f:b=pop();a=pop();jump=not a>=b")
exec(src,ns);VM=ns['VM'];U=ns['U']
a=ABC((W/'TeamManagementPlayerEnhancementTabPage-after.abc').read_bytes());old_a=ABC((W/'TeamManagementPlayerEnhancementTabPage-before.abc').read_bytes())
p=ABC((W/'TeamManagementPlayerEnhancingPopupScreen-after.abc').read_bytes());old_p=ABC((W/'TeamManagementPlayerEnhancingPopupScreen-before.abc').read_bytes())
checks=[]

for abc,should_fail in ((old_a,False),(a,False)):
 mark={'visible':False};box={'enabled':True,'selected':False,'getChildByName':lambda n:mark}
 calls=[];owner={'_available':True,'getChildByName':lambda n:box,'requestPreview':lambda:calls.append('preview')}
 vm=VM(abc,owner);vm.captured=True
 try:vm.run(45,({'currentTarget':box},),locals_override={0:{}})
 except AssertionError:assert should_fail
 else:
  assert not should_fail and box['selected'] and box['fo3RememberProtection'] and mark['visible'] and calls==['preview']
 assert not vm.puts
checks.append('Fresh official event.currentTarget callback preserved; unbound invocation keeps choice and fresh preview')

def recovery(target,old=False):
 abc=old_p if old else p;queue=[];draw=[];events=[];clabel={}
 def clip(name):
  return {'gotoAndPlay':lambda label:events.append((name,'play',label)),'gotoAndStop':lambda label:events.append((name,'stop',label)),'stop':lambda:events.append((name,'halt'))}
 owner={'_version':'v2_5','_result':{'resultgrade':target,'resultPrice':12345,'rprice':12345,'grantes':140,'usepoint':{'currency':'ES','price':420}},
  '_data':{'firstPlayer':{'_id':'main','spid':19020289,'grade':13,'levelinfo':{'level':30,'exp':0}},'info':{'grade':14,'levelinfo':{'level':30,'exp':0,'to':100}}},
  '_restoreStep':0,'_restoreCount':0,'_restorePlayerData':None,'_restoreButton':{'enabled':True,'visible':True},'container':clip('root'),
  'priceResult':{'priceTextField':{}},'boostInfoPanel':dict(clip('boost'),esTextContainer={'saveES':{},'esTitle':{}}),
  'failurePlayer':{'setData':lambda data:draw.append(copy.deepcopy(data))},'failureCardContainer':clip('failure'),
  'setEnhanceCautionLabelString':lambda text:events.append(('caption',text)),'enableQuitScreen':lambda flag:events.append(('exit',flag)),
  'setNumericLabel':lambda field,value:field.update(value=value)}
 allvms=[]
 def run(mid,args=(),captured=False):
  vm=VM(abc,owner);vm.captured=captured;allvms.append(vm)
  vm.globals.update(isFinite=math.isfinite,ObjectUtil={'deepCopy':copy.deepcopy},PlayerListUtil={'expandPlayerStaticData':lambda data,fn:queue.append(fn)},
   Localization={'getLocalizedString':lambda key:key,'getLocalizedStringWithArgs':lambda key,*args:key},StringUtil={'formatToCurrency':lambda value:format(value,',')})
  return vm.run(mid,args)
 owner.update(changePlayerCardInRestoreAnimation=lambda:run(49),restoreComplete=lambda:run(48),checkRestoreComplete=lambda:run(44))
 return owner,queue,draw,events,allvms,run

for target in (0,1,12,20):
 owner,queue,draw,events,vms,run=recovery(target)
 run(47)
 assert owner['_restoreCount']==target and owner['_restorePlayerData']['grade']==target
 assert owner['_restorePlayerData']['restoreSpaceState']=='pending' and len(queue)==1 and not draw
 run(46);assert owner['_restoreCount']==target and len(queue)==1
 run(queue[0].mid,captured=True)
 assert owner['_restorePlayerData']['restoreSpaceState']=='done' and len(draw)==1 and draw[0]['grade']==target
 assert draw[0]['levelinfo']=={'level':30,'exp':0,'to':100}
 assert ('root','play','restoreFail' if target==0 else 'restoreSuccess') in events
 run(46);run(queue[0].mid,captured=True)
 assert len(draw)==1 and owner['_restoreCount']==target and len(queue)==1
 # The original completion frame enables the existing paid recovery/exit path.
 run(21,captured=True);assert owner['_restoreStep']==1 and owner['_restoreButton']['enabled']
 assert ('exit',True) in events
 assert all(not vm.puts for vm in vms)
checks.append('Actual one-shot restoreStart/async callback/native completion bodies: grades0/1/12/20 render exactly once, keep XP, ignore old loops and duplicate callbacks; zero PUT')

owner,queue,draw,events,vms,run=recovery(12,old=True)
owner['_restorePlayerData']={'grade':0,'restoreSpaceState':'active'}
try:run(46)
except LookupError as error:assert '_restorePlayerData' in str(error)
else:raise AssertionError('Old pre-pushscope guard should not resolve an instance')
checks.append('Scope-aware replay exposes old restore loop accessing instance state before this is on scope')

# Failure still draws +0; paid server calls, confirmations and URI remain exact.
for mid in (18,19,20,21,22,23,31,33,36,37,38,39,40,41,42,43,44,49,61,62,63):assert old_p.A['body_records'][mid]['raw']==p.A['body_records'][mid]['raw']
for mid,row in old_a.A['body_records'].items():
 assert row['raw']==a.A['body_records'][mid]['raw']
checks.append('Original failure +0 rendering, protected failure handling, paid recovery consent/URI, space shortcut, pair/preferences, fees and all other methods unchanged')
result=dict(status='PASS',checks=checks,real_assets_written=False,real_recovery_executed=False,native_game_verified=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
