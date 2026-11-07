"""Keep the enhancement ABC native; drive its existing ListEvent after readiness."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
# Reuse only the format writer definitions, never execute an older build.
exec(compile(Path(r'D:\fifaol3\lineup-enhance-repair\build.py').read_text('utf8').split('report={}')[0],'<ABC helpers>','exec'))
W=Path(__file__).resolve().parent;V1=W.parent/'lineup-enhance-shortcut';V2=W.parent/'lineup-enhance-repair'
ICON='fo3LineupEnhanceV3';PENDING='fo3LineupRequestV2'
def restore(a,prefix,mids,obsolete):
 native=ABC((V1/(prefix+'.abc')).read_bytes());installed=ABC((V2/(prefix+'-after.abc')).read_bytes())
 for mid in mids:
  assert a.A['body_records'][mid]['raw']==installed.A['body_records'][mid]['raw'],('Later legitimate method edit',prefix,mid)
  a.changed[mid]=native.A['body_records'][mid]['raw'];a.A['body_records'][mid]=native.A['body_records'][mid];a.A['body'][mid]=native.A['body'][mid]
 for mid in obsolete:
  record=a.A['body_records'][mid];a.changed[mid]=u30(mid)+b''.join(u30(n) for n in record['fields'])+b'\x01\x47'+record['suffix']

def renderer(a):
 restore(a,'components-ScrollingList-3451',(10,28,33),(36,37,38,39,40,41));methods=[]
 c=Code(a).local(0).op(0x30).local(1).call('stopPropagation',0).op(0x29)
 c.local(0).prop('data').store(2);c.local(2).jump(0x12,'done');c.local(2).prop('id').jump(0x12,'done')
 query(c,a,'fo3LineupOpenV3',[(key,lambda c,key=key:c.local(2).prop(key)) for key in ('id','spid','grade')])
 c.label('done').op(0x47);click=add(a,c,28,3);methods.append((a.name('fo3LineupClickV3'),click))
 c=Code(a).local(0).op(0x30).local(0).string(ICON).call('getChildByName',1).store(2);c.local(2).jump(0x11,'done')
 # A blank native capsule, unlike the old square plus and its extra hit-area.
 c.op(0x5d,a.name('getDefinitionByName','flash.utils')).string('TransferMarketRollOverButton').op(0x46,a.name('getDefinitionByName','flash.utils'),1).op(0x42,0).store(2)
 for name,emit in [('name',lambda c:c.string(ICON)),('focusable',lambda c:c.op(0x27)),('visible',lambda c:c.op(0x27)),('toggle',lambda c:c.op(0x27)),('autoSize',lambda c:c.string('none')),('label',lambda c:c.string('')),('width',lambda c:c.number(64)),('height',lambda c:c.number(37))]:c.local(2);emit(c);c.set(name)
 c.lex('MovieClip','flash.display').op(0x42,0).store(3)
 c.local(3).op(0x27).set('mouseEnabled');c.local(3).op(0x27).set('mouseChildren')
 c.local(3).prop('graphics').store(4);c.local(4).number(0x407f99).call('beginFill',1).op(0x29)
 for fn,x,y in [('moveTo',23,18),('lineTo',32,9),('lineTo',41,18),('lineTo',36,18),('lineTo',36,27),('lineTo',28,27),('lineTo',28,18),('lineTo',23,18)]:c.local(4).number(x).number(y).call(fn,2).op(0x29)
 c.local(4).call('endFill',0).op(0x29);c.local(2).local(3).call('addChild',1).op(0x29)
 c.local(2).lex('ButtonEvent',a.A['mnns'][a.own('ButtonEvent')]).prop('CLICK').local(0).prop('fo3LineupClickV3').call('addEventListener',2).op(0x29)
 c.local(0).local(2).call('addChild',1).op(0x29).label('done').op(0x47)
 init=add(a,c,28,5);methods.append((a.name('fo3LineupInitV3'),init));endcall(a,10,'fo3LineupInitV3')
 c=Code(a).local(0).op(0x30).local(0).string(ICON).call('getChildByName',1).store(2);c.local(2).jump(0x12,'done')
 c.local(2).op(0x27).set('visible');c.local(0).prop('data').jump(0x12,'done')
 c.local(0).prop('playerLockButton').store(3);c.local(3).jump(0x11,'anchor');c.local(0).prop('playerUnLockButton').store(3);c.local(3).jump(0x12,'done')
 c.label('anchor').local(2).local(3).prop('x').number(60).op(0xa0).set('x');c.local(2).local(3).prop('y').set('y')
 # Never resize a native compound clip from another button's dynamic bounds.
 c.local(0).prop('playerDetailInfoButton').store(3);c.local(3).jump(0x12,'done');c.local(3).prop('visible').jump(0x12,'done')
 c.local(0).prop('data').prop('__lockButtonVisible').jump(0x12,'done');c.local(2).op(0x26).set('visible').label('done').op(0x47)
 sync=add(a,c,28,4);methods.append((a.name('fo3LineupSyncV3'),sync))
 for mid in (28,33):endcall(a,mid,'fo3LineupSyncV3')
 return methods,[],dict(click=click,init=init,sync=sync)

def base(a):
 restore(a,'components-ScrollingList-3269',(37,),())
 c=Code(a).local(0).string(ICON).call('getChildByName',1).jump(0x12,'done');c.local(0).op(0x20).call('fo3LineupSyncV3',1).op(0x29).label('done');a.modify(37,{136:c.done()})
 return [],[],{}

def root(a):
 restore(a,'TeamManagementScreen-29',(2,7),(19,))
 c=Code(a).local(1).jump(0x12,'native');c.local(1).prop('cmd').string('fo3LineupOpenV3').jump(0x14,'native')
 c.local(0).local(1).set(PENDING);c.local(1);time(c,a).set('createdAt')
 for name in ('navigated','positioned'):c.local(1).op(0x27).set(name)
 c.local(1).number(0).set('polls');c.local(1).number(0).set('readyFrames')
 c.local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('addEventListener',2).op(0x29).op(0x47).label('native');a.modify(2,{2:c.done()})
 c=Code(a).local(0).op(0x30).local(0).prop(PENDING).store(2);c.local(2).jump(0x12,'cancel')
 time(c,a).local(2).prop('createdAt').op(0xa1).store(13)
 c.local(13).number(0).jump(0x15,'cancel');c.local(13).number(30000).jump(0x17,'cancel')
 c.local(2).local(2).prop('polls').number(1).op(0xa0).set('polls')
 c.local(2).prop('polls').number(600).jump(0x17,'cancel')
 c.local(2).prop('navigated').jump(0x11,'waitready')
 c.local(2).op(0x26).set('navigated')
 c.local(0).prop('teamManagementTab')
 c.string('pageClassname').string('TeamManagementPlayerTabPage').op(0x55,1)
 c.string('tabname').string('playerSettingTab').string('pageClassname').string('TeamManagementPlayerEnhancementTabPage').op(0x55,2)
 c.op(0x56,2).call('switchTabPage',1).op(0x29).jump(0x10,'done')
 c.label('waitready').local(0).prop('teamManagementTab').prop('selectedTabPage').store(3);c.local(3).jump(0x12,'done')
 c.string('playerSettingTab').local(3).op(0xb4).jump(0x12,'done')
 c.local(3).prop('playerSettingTab').store(4);c.local(4).jump(0x12,'done')
 c.local(4).prop('selectedIndex').local(4).string('TeamManagementPlayerEnhancementTabPage').call('indexOfByClassName',1).jump(0x14,'done')
 c.local(4).prop('selectedTabPage').store(5);c.local(5).jump(0x12,'done')
 c.local(5).prop('numChildren').number(32).jump(0x17,'cancel');c.number(0).store(12)
 c.label('children').local(12).local(5).prop('numChildren').jump(0x0c,'done')
 c.local(5).local(12).call('getChildAt',1).store(6)
 c.string('playerPanel').local(6).op(0xb4).jump(0x11,'view')
 c.local(12).number(1).op(0xa0).store(12).jump(0x10,'children')
 c.label('view').local(6).prop('visible').jump(0x12,'done');c.local(6).prop('playerPanel').store(7);c.local(7).jump(0x12,'done')
 c.local(7).prop('enhanceList').store(7);c.local(7).jump(0x12,'done');c.local(7).prop('dataProvider').store(8);c.local(8).jump(0x12,'done')
 c.local(8).prop('length').store(14);c.local(14).jump(0x12,'done');c.number(0).store(9)
 c.label('items').local(9).local(14).jump(0x0c,'cancel')
 c.local(8).local(9).call('requestItemAt',1).store(10);c.local(10).jump(0x12,'next')
 c.local(10).prop('_id').local(2).prop('id').jump(0x13,'found')
 c.label('next').local(9).number(1).op(0xa0).store(9).jump(0x10,'items')
 c.label('found')
 for key in ('spid','grade'):c.local(10).prop(key).local(2).prop(key).jump(0x14,'cancel')
 c.local(2).prop('positioned').jump(0x11,'rendered')
 c.local(2).op(0x26).set('positioned');c.local(7).local(9).set('selectedIndex');c.local(7).local(9).set('scrollPosition');c.local(7).call('validateNow',0).op(0x29).jump(0x10,'done')
 c.label('rendered').local(7).local(9).local(7).prop('scrollPosition').call('getRendererAt',2).store(11);c.local(11).jump(0x12,'done')
 c.local(11).prop('data').jump(0x12,'done');c.local(11).prop('data').prop('_id').local(2).prop('id').jump(0x14,'done')
 c.local(2).local(2).prop('readyFrames').number(1).op(0xa0).set('readyFrames');c.local(2).prop('readyFrames').number(2).jump(0x15,'done')
 # Consume first, then dispatch the exact native click event. Enhancement ABC,
 # native private methods, inventory and static-load handlers remain untouched.
 c.local(0).op(0x20).set(PENDING);c.local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('removeEventListener',2).op(0x29)
 c.local(6).string('clear selected player').op(0x20).call('query',2).op(0x29)
 c.local(7).lex('ListEvent','scaleform.clik.events').string('itemClick').op(0x27).op(0x27).local(9).raw(b'\x24\xff\x24\xff').local(11).local(10).number(0).number(0).op(0x27).op(0x42,11).call('dispatchEvent',1).op(0x29).jump(0x10,'done')
 c.label('cancel').local(0).op(0x20).set(PENDING);c.local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('removeEventListener',2).op(0x29)
 c.label('done').op(0x47);drive=add(a,c,14,15)
 cleanup=Code(a).local(0).op(0x20).set(PENDING).local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('removeEventListener',2).op(0x29)
 at=next(at for at,_,op,_ in reversed(list(instructions(a.A['body'][7]))) if op==0x47);a.modify(7,{at:cleanup.done()})
 return [(a.name('fo3LineupDriveV3'),drive)],[],dict(drive=drive)

report={}
for key,selected in [('components-ScrollingList',{3269:('PlayerListItemRendererNew',base),3451:('PlayerPoolItemListRenderer',renderer)}),('TeamManagementPlayerEnhancementTabPage',{289:('EnhancePlayerPanel',None)}),('TeamManagementScreen',{29:('TeamManagementScreen',root)})]:
 source=W/(key+'-baseline.big');swf=(W/(key+'-baseline.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];blocks={}
 for ordinal,(kind,body,raw) in enumerate(tags(swf,start,len(swf))):
  if ordinal in selected:
   assert kind==82;cls,fn=selected[ordinal];head=body.index(b'\0',4)+1;before=body[head:];old=ABC(before);a=ABC(before);prefix=f'{key}-{ordinal}'
   if fn is None:
    assert before==(V2/(prefix+'-after.abc')).read_bytes(),'Preserve later legitimate enhancement edits'
    data=(V1/(prefix+'.abc')).read_bytes();block=dict(class_name=cls,restored_native_abc_exact=True,changed=[],added=[],callbacks={})
   else:
    methods,slots,meta=fn(a);data=a.output();data=addtraits(data,cls,methods,slots) if methods or slots else data;b=ABC(data)
    for mid,row in old.A['body_records'].items():
     if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
    (W/(prefix+'-patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    block=dict(class_name=cls,changed=sorted(a.changed),added=list(range(len(old.A['meth']),len(b.A['meth']))),callbacks=meta)
   (W/(prefix+'-before.abc')).write_bytes(before);(W/(prefix+'-after.abc')).write_bytes(data);blocks[prefix]=block;raw=tag(kind,body[:head]+data)
  parts.append(raw)
 out=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out));target=W/(key+'.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 pack_archive(source,target,{member:b'CFX'+out[3:8]+zlib.compress(out[8:],9)},[])
 assert all(x[2]==y[2] for x,y in zip(tags(swf,start,len(swf)),tags(out,start,len(out))) if x[0]!=82)
 for n,*_ in bigdir.entries(source):
  if n!=member:assert bigdir.read(source,n)==bigdir.read(target,n)
 report[key]=dict(source_sha256=sha(source),sha256=sha(target),blocks=blocks,unmodified_members_and_methods_preserved=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
