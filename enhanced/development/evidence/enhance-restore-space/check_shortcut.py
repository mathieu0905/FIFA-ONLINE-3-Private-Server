"""Replay installed AVM2 shortcut with temporary objects, never real game assets."""
from patch_restore_space import *
ns={'__file__':str(HELPERS/'test_bp_client.py')}
exec((HELPERS/'test_bp_client.py').read_text(encoding='utf8').split('def load(name):')[0],ns)
VM,Function=ns['VM'],ns['Function']
s=(OUT/'popup.updated.swf').read_bytes()
for t,b,raw in tags(s,8+(5+4*(s[8]>>3)+7)//8+4,len(s)):
    if t!=82:continue
    a=ABC(b[b.index(b'\0',4)+1:])
    if any(x[1]=='restoreStart' for x in a.A['cls'][0][3]):break
report=json.loads((OUT/'build.json').read_text())
checks=[]
for grade in range(21):
    calls=[];pending=[]
    owner={'_result':{'resultgrade':grade},'_restoreCount':0,
           '_restorePlayerData':{'grade':0,'restoreSpaceState':'active'},
           'container':{'stop':lambda:calls.append('stop'),'gotoAndPlay':lambda label:calls.append(label)},
           'changePlayerCardInRestoreAnimation':lambda:calls.append('card'),
           'restoreComplete':lambda:calls.append('complete')}
    vm=VM(a,owner)
    vm.globals['PlayerListUtil']={'expandPlayerStaticData':lambda player,cb:pending.append((player,cb))}
    event={'keyCode':32,'stopImmediatePropagation':lambda:None,'preventDefault':lambda:None}
    vm.run(report['handler'],[dict(event,keyCode=13)])
    assert not calls and not pending
    vm.run(report['handler'],[event]);vm.run(report['handler'],[event])
    assert calls==['stop'] and len(pending)==1
    assert owner['_restoreCount']==owner['_restorePlayerData']['grade']==grade
    # An old async expand callback / queued timeline event cannot restart the loop.
    vm.run(45);vm.run(46)
    assert calls==['stop']
    player,callback=pending.pop();player['staticdata']={'grade':grade}
    vm.run(callback.mid);vm.run(callback.mid);vm.run(report['handler'],[event]);vm.run(45)
    assert calls==['stop','card','complete'] and not pending and not vm.puts
checks.append('grades 0..20; exact server grade; one completion; key repeat and stale callbacks; zero PUT')
for state in [None,'done','pending']:
    owner={'_restorePlayerData':None if state is None else {'restoreSpaceState':state}}
    vm=VM(a,owner);vm.run(report['handler'],[{'keyCode':32}]);assert not vm.puts
checks.append('Space outside active restoration has no effect')
owner={'_restorePlayerData':{'restoreSpaceState':'active'},'container':{'gotoAndPlay':lambda label:checks.append('native '+label)}}
VM(a,owner).run(45);assert checks[-1]=='native restore'
result={'status':'PASS','checks':checks,'scope':'exact shortcut bytecode replay with temporary objects; no native game claim'}
(OUT/'shortcut-checks.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
