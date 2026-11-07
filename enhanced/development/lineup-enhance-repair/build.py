"""Replace the faulty shortcut with native buttons and deferred native Zone queries."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,Code,R,u30,tags,tag,pack_archive,bigdir,instructions
import avm_patch
W=Path(__file__).resolve().parent;OLD=W.parent/'lineup-enhance-shortcut'
ICON='fo3NativeEnhanceIcon';PENDING='fo3LineupRequestV2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def addtraits(data,cls,methods,slots=()):
 src=avm_patch.SOURCE.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []').replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
 ns={'__name__':'bounds'};exec(compile(src,'<bounds>','exec'),ns);a=ns['parse'](data,0);row=next(v for v in a['cls'] if v[0]==cls);b=next(v for v in a['trait_records'] if v['values']==row[3]);r=R(data,b['start']);count=r.u30()
 additions=b''.join(u30(n)+b'\x01\x00'+u30(m) for n,m in methods)+b''.join(u30(n)+b'\x00\x00'+u30(t)+b'\x00' for n,t in slots)
 return data[:b['start']]+u30(count+len(methods)+len(slots))+data[r.p:b['end']]+additions+data[b['end']:]
def add(a,c,ref,locals):return a.add_method(c.done(),a.A['body_records'][ref]['fields'][2],local_count=locals)
def endcall(a,mid,name):
 at=next(at for at,_,op,_ in reversed(list(instructions(a.A['body'][mid]))) if op==0x47)
 a.modify(mid,{at:Code(a).local(0).op(0x20).call(name,1).op(0x29).done()})
def restore_own(a,prefix,mids,obsolete):
 original=ABC((OLD/(prefix+'.abc')).read_bytes());faulty=ABC((OLD/(prefix+'-after.abc')).read_bytes())
 for i in range(7):assert a.values[i][:len(original.values[i])]==original.values[i]
 for mid in mids:
  assert a.A['body_records'][mid]['raw']==faulty.A['body_records'][mid]['raw'],('Later method edit',prefix,mid)
  a.changed[mid]=original.A['body_records'][mid]['raw'];a.A['body_records'][mid]=original.A['body_records'][mid];a.A['body'][mid]=original.A['body'][mid]
 for mid in obsolete:
  r=a.A['body_records'][mid];code=b'\x47';a.changed[mid]=u30(mid)+b''.join(u30(x) for x in r['fields'])+u30(1)+code+r['suffix']
def query(c,a,command,extras=()):
 c.lex('ZoneManager','fok').prop('instance').prop('currentZone').string('TeamManagementScreen.swf').string('cmd').string(command)
 for name,emit in extras:c.string(name);emit(c)
 c.op(0x55,1+len(extras)).call('query',2).op(0x29)
def time(c,a):return c.op(0x5d,a.name('getTimer','flash.utils')).op(0x46,a.name('getTimer','flash.utils'),0)

def root(a):
 # Receive via the native Zone.query/onQuery contract; defer all navigation until
 # the original button event has unwound. No display-parent walk or carrier clips.
 c=Code(a).local(1).jump(0x12,'native')
 c.local(1).prop('cmd').string('fo3LineupOpenV2').jump(0x14,'take')
 c.local(0).local(1).set(PENDING)
 c.local(1);time(c,a).set('createdAt')
 c.local(0).string('enterFrame').local(0).prop('fo3LineupNavigateV2').call('addEventListener',2).op(0x29).op(0x47)
 c.label('take').local(1).prop('cmd').string('fo3LineupPeekV2').jump(0x14,'consume')
 c.local(1).local(0).prop(PENDING).set('response').op(0x47)
 c.label('consume').local(1).prop('cmd').string('fo3LineupConsumeV2').jump(0x14,'native')
 c.local(1).prop('request').local(0).prop(PENDING).jump(0x1a,'ret')
 c.local(0).op(0x20).set(PENDING).label('ret').op(0x47).label('native')
 a.modify(2,{2:c.done()})
 c=Code(a).local(0).op(0x30)
 c.local(0).string('enterFrame').local(0).prop('fo3LineupNavigateV2').call('removeEventListener',2).op(0x29)
 c.local(0).prop(PENDING).jump(0x12,'done')
 c.local(0).prop('teamManagementTab')
 c.string('pageClassname').string('TeamManagementPlayerTabPage').op(0x55,1)
 c.string('tabname').string('playerSettingTab').string('pageClassname').string('TeamManagementPlayerEnhancementTabPage').op(0x55,2)
 c.op(0x56,2).call('switchTabPage',1).op(0x29).label('done').op(0x47)
 mid=add(a,c,14,2)
 cleanup=Code(a).local(0).op(0x20).set(PENDING).local(0).string('enterFrame').local(0).prop('fo3LineupNavigateV2').call('removeEventListener',2).op(0x29)
 at=next(at for at,_,op,_ in reversed(list(instructions(a.A['body'][7]))) if op==0x47)
 a.modify(7,{at:cleanup.done()})
 return [(a.name('fo3LineupNavigateV2'),mid)],[(a.name(PENDING),a.name('Object'))],dict(navigate=mid)

def renderer(a):
 restore_own(a,'components-ScrollingList-3451',(10,28,33),(36,37,38));methods=[]
 c=Code(a).local(0).op(0x30).local(1).call('stopPropagation',0).op(0x29)
 c.local(0).prop('data').store(2);c.local(2).jump(0x12,'done');c.local(2).prop('id').jump(0x12,'done')
 query(c,a,'fo3LineupOpenV2',[(key,lambda c,key=key:c.local(2).prop(key)) for key in ('id','spid','grade')])
 c.label('done').op(0x47);click=add(a,c,28,3);methods.append((a.name('fo3NativeEnhanceClickV2'),click))
 c=Code(a).local(0).op(0x30).local(0).string(ICON).call('getChildByName',1).store(2);c.local(2).jump(0x11,'done')
 c.op(0x5d,a.name('getDefinitionByName','flash.utils')).string('PlayerGrowthIncreaseButton').op(0x46,a.name('getDefinitionByName','flash.utils'),1).op(0x42,0).store(2)
 for name,emit in [('name',lambda c:c.string(ICON)),('focusable',lambda c:c.op(0x27)),('visible',lambda c:c.op(0x27)),('toggle',lambda c:c.op(0x27)),('autoSize',lambda c:c.string('none'))]:c.local(2);emit(c);c.set(name)
 c.local(2).lex('ButtonEvent',a.A['mnns'][a.own('ButtonEvent')]).prop('CLICK').local(0).prop('fo3NativeEnhanceClickV2').call('addEventListener',2).op(0x29)
 c.local(0).local(2).call('addChild',1).op(0x29).label('done').op(0x47)
 init=add(a,c,28,3);methods.append((a.name('fo3NativeEnhanceInitV2'),init));endcall(a,10,'fo3NativeEnhanceInitV2')
 c=Code(a).local(0).op(0x30).local(0).string(ICON).call('getChildByName',1).store(2);c.local(2).jump(0x12,'done')
 c.local(2).op(0x27).set('visible');c.local(0).prop('data').jump(0x12,'done')
 c.local(0).prop('playerLockButton').store(3);c.local(3).jump(0x11,'anchor');c.local(0).prop('playerUnLockButton').store(3);c.local(3).jump(0x12,'done')
 c.label('anchor')
 # Timeline inspection: search x=407, lock/unlock x=467. Keep both untouched,
 # put the extra native button at x=527, matching the 60px native pitch.
 c.local(2).local(3).prop('x').number(60).op(0xa0).set('x')
 c.local(2).local(3).prop('y').set('y')
 c.local(2).local(3).prop('width').set('width');c.local(2).local(3).prop('height').set('height')
 c.local(0).prop('playerDetailInfoButton').store(3);c.local(3).jump(0x12,'done')
 c.local(3).prop('visible').jump(0x12,'done');c.local(0).prop('data').prop('__lockButtonVisible').jump(0x12,'done')
 c.local(2).op(0x26).set('visible').label('done').op(0x47)
 sync=add(a,c,28,4);methods.append((a.name('fo3NativeEnhanceSyncV2'),sync))
 for mid in (28,33):endcall(a,mid,'fo3NativeEnhanceSyncV2')
 return methods,[],dict(click=click,init=init,sync=sync)

def base(a):
 restore_own(a,'components-ScrollingList-3269',(37,),())
 c=Code(a).local(0).string(ICON).call('getChildByName',1).jump(0x12,'done')
 c.local(0).op(0x20).call('fo3NativeEnhanceSyncV2',1).op(0x29).label('done');a.modify(37,{136:c.done()})
 return [],[],{}

def panel(a):
 restore_own(a,'TeamManagementPlayerEnhancementTabPage-289',(15,54),(90,));methods=[]
 # Inventory/start only arms a one-frame callback; never selects while native
 # updatePlayers or tab dispatch is still running.
 c=Code(a).local(0).op(0x30).local(0).string('enterFrame').local(0).prop('fo3LineupAcceptV2').call('addEventListener',2).op(0x29).op(0x47)
 schedule=add(a,c,54,2);methods.append((a.name('fo3LineupScheduleV2'),schedule))
 for mid in (15,54):endcall(a,mid,'fo3LineupScheduleV2')
 c=Code(a).local(0).op(0x30).local(0).string('enterFrame').local(0).prop('fo3LineupAcceptV2').call('removeEventListener',2).op(0x29)
 c.local(0).prop('stage').jump(0x12,'done');c.local(0).prop('visible').jump(0x12,'done')
 c.string('cmd').string('fo3LineupPeekV2').op(0x55,1).store(2)
 c.lex('ZoneManager','fok').prop('instance').prop('currentZone').string('TeamManagementScreen.swf').local(2).call('query',2).op(0x29)
 c.local(2).prop('response').store(3);c.local(3).jump(0x12,'done')
 time(c,a).local(3).prop('createdAt').op(0xa1).store(4)
 c.local(4).number(0).jump(0x15,'consume');c.local(4).number(60000).jump(0x17,'consume')
 c.local(0).ownprop('_players').store(5);c.local(5).jump(0x12,'done');c.local(5).prop('length').jump(0x12,'done')
 c.number(0).store(6)
 c.label('loop').local(6).local(5).prop('length').jump(0x0c,'consume')
 c.local(5).local(6).op(0x66,a.A['mn'].index('[late]')).store(7)
 c.local(7).prop('_id').local(3).prop('id').jump(0x13,'found')
 c.local(6).number(1).op(0xa0).store(6).jump(0x10,'loop')
 c.label('found')
 for key in ('spid','grade'):c.local(7).prop(key).local(3).prop(key).jump(0x14,'consume')
 query(c,a,'fo3LineupConsumeV2',[('request',lambda c:c.local(3))])
 c.local(0).owncall('clearSelectedPlayer',0).op(0x29)
 c.local(0).local(7).owncall('availableEnhancePlayer',1).jump(0x12,'done')
 c.local(0).local(7).op(0x20).owncall('selectTarget',2).op(0x29)
 c.local(0).owncall('invalidatePlayerList',0).op(0x29).jump(0x10,'done')
 c.label('consume');query(c,a,'fo3LineupConsumeV2',[('request',lambda c:c.local(3))])
 c.label('done').op(0x47)
 accept=add(a,c,54,8);methods.append((a.name('fo3LineupAcceptV2'),accept))
 return methods,[],dict(schedule=schedule,accept=accept)

report={}
for key,selected in [('components-ScrollingList',{3269:('PlayerListItemRendererNew',base),3451:('PlayerPoolItemListRenderer',renderer)}),('TeamManagementPlayerEnhancementTabPage',{289:('EnhancePlayerPanel',panel)}),('TeamManagementScreen',{29:('TeamManagementScreen',root)})]:
 source=W/(key+'-baseline.big');swf=(W/(key+'-baseline.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];blocks={}
 for ordinal,(kind,body,raw) in enumerate(tags(swf,start,len(swf))):
  if ordinal in selected:
   assert kind==82;cls,fn=selected[ordinal];head=body.index(b'\0',4)+1;before=body[head:];old=ABC(before);a=ABC(before);assert cls in [v[0] for v in a.A['cls']]
   methods,slots,callbacks=fn(a);data=a.output();data=addtraits(data,cls,methods,slots) if methods or slots else data;b=ABC(data)
   prefix=f'{key}-{ordinal}';(W/(prefix+'-before.abc')).write_bytes(before);(W/(prefix+'-after.abc')).write_bytes(data)
   (W/(prefix+'-patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
   for mid,row in old.A['body_records'].items():
    if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
   assert old.A['sig']==b.A['sig'][:len(old.A['sig'])]
   blocks[prefix]=dict(class_name=cls,changed=sorted(a.changed),added=list(range(len(old.A['meth']),len(b.A['meth']))),callbacks=callbacks)
   raw=tag(kind,body[:head]+data)
  parts.append(raw)
 out=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out));target=W/(key+'.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 pack_archive(source,target,{member:b'CFX'+out[3:8]+zlib.compress(out[8:],9)},[])
 assert all(x[2]==y[2] for x,y in zip(tags(swf,start,len(swf)),tags(out,start,len(out))) if x[0]!=82)
 for n,*_ in bigdir.entries(source):
  if n!=member:assert bigdir.read(source,n)==bigdir.read(target,n)
 report[key]=dict(source_sha256=sha(source),sha256=sha(target),blocks=blocks,unmodified_members_and_methods_preserved=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
