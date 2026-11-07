from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
exec(compile(Path(r'D:\fifaol3\lineup-enhance-repair\build.py').read_text('utf8').split('\nreport={}')[0],'<format helpers>','exec'))
from skin import build as build_skin
W=Path(__file__).resolve().parent;C=Path(r'D:\FO3ID\32795');V4=W.parent/'lineup-enhance-v4'
BaseCode=Code
class Code(BaseCode):
 def label(self,name):super().label(name);return self.op(0x09)

def drive(a):
 c=Code(a).local(0).op(0x30).local(0).prop('fo3LineupRequestV2').store(2);c.local(2).jump(0x12,'cancel')
 time(c,a).local(2).prop('createdAt').op(0xa1).store(13)
 c.local(13).number(0).jump(0x15,'cancel');c.local(13).number(30000).jump(0x17,'cancel')
 c.local(2).local(2).prop('polls').number(1).op(0xa0).set('polls');c.local(2).prop('polls').number(600).jump(0x17,'cancel')
 c.local(2).prop('navigated').jump(0x11,'ready');c.local(2).op(0x26).set('navigated')
 c.local(0).prop('teamManagementTab').string('pageClassname').string('TeamManagementPlayerTabPage').op(0x55,1)
 c.string('tabname').string('playerSettingTab').string('pageClassname').string('TeamManagementPlayerEnhancementTabPage').op(0x55,2).op(0x56,2).call('switchTabPage',1).op(0x29).jump(0x10,'done')
 c.label('ready').local(0).prop('teamManagementTab').prop('selectedTabPage').store(3);c.local(3).jump(0x12,'done')
 c.string('playerSettingTab').local(3).op(0xb4).jump(0x12,'done');c.local(3).prop('playerSettingTab').store(4);c.local(4).jump(0x12,'done')
 c.local(4).prop('selectedIndex').local(4).string('TeamManagementPlayerEnhancementTabPage').call('indexOfByClassName',1).jump(0x14,'done')
 c.local(4).prop('selectedTabPage').store(5);c.local(5).jump(0x12,'done');c.local(5).prop('numChildren').number(32).jump(0x17,'cancel');c.number(0).store(12)
 c.label('children').local(12).local(5).prop('numChildren').jump(0x0c,'done');c.local(5).local(12).call('getChildAt',1).store(6)
 c.string('playerPanel').local(6).op(0xb4).jump(0x11,'view');c.local(12).number(1).op(0xa0).store(12).jump(0x10,'children')
 c.label('view').local(6).prop('visible').jump(0x12,'done');c.local(6).prop('playerPanel').store(15);c.local(15).jump(0x12,'done')
 # A lone instance is a valid primary choice. Expand the native inventory view;
 # its default duplicate-only filter must not silently discard that instance.
 c.local(2).prop('expanded').jump(0x11,'inventory')
 c.local(15).prop('showAllPlayersButton').store(11);c.local(11).jump(0x12,'done')
 c.local(2).op(0x26).set('expanded');c.local(11).prop('selected').jump(0x11,'inventory')
 c.local(11).op(0x26).set('selected');c.local(11).lex('ButtonEvent','scaleform.clik.events').string('buttonClick').op(0x42,1).call('dispatchEvent',1).op(0x29).jump(0x10,'done')
 c.label('inventory').local(15).prop('enhanceList').store(7);c.local(7).jump(0x12,'done');c.local(7).prop('dataProvider').store(8);c.local(8).jump(0x12,'done')
 c.local(8).prop('length').store(14);c.local(14).jump(0x12,'done');c.number(0).store(9)
 c.label('items').local(9).local(14).jump(0x0c,'notready');c.local(8).local(9).call('requestItemAt',1).store(10);c.local(10).jump(0x12,'next')
 c.local(10).prop('_id').local(2).prop('id').jump(0x13,'found');c.label('next').local(9).number(1).op(0xa0).store(9).jump(0x10,'items')
 c.label('found')
 for key in ('spid','grade'):c.local(10).prop(key).local(2).prop(key).jump(0x14,'cancel')
 # Preserve native lockinfo.enhance and the exact native timestamp rule,
 # through existing public utilities. No enhancement class changes are needed.
 c.local(6).prop('lockinfo').store(11);c.local(11).jump(0x12,'unlocked');c.local(11).prop('enhance').jump(0x12,'unlocked')
 c.local(10).prop('locked').store(11);c.local(11).jump(0x12,'unlocked')
 c.lex('TimerUtil','fok.utils').local(11).call('parseW3CDTF',1).store(11)
 c.lex('DateUtils','org.as3commons.lang').lex('TimerUtil','fok.utils').call('getTime2',0).local(11).call('getMinutesDiff',2).number(0).jump(0x17,'cancel')
 c.local(11).call('getFullYear',0).number(9999).jump(0x13,'cancel')
 c.label('unlocked').local(2).prop('clearDone').jump(0x11,'cleared')
 c.local(2).op(0x26).set('clearDone');c.local(6).string('clear selected player').op(0x20).call('query',2).op(0x29)
 c.local(7).call('invalidateData',0).op(0x29).jump(0x10,'done')
 c.label('cleared').local(10).prop('enabled').op(0x27).jump(0x13,'cancel')
 c.local(2).local(2).prop('readyFrames').number(1).op(0xa0).set('readyFrames');c.local(2).prop('readyFrames').number(2).jump(0x15,'done')
 c.local(10).op(0x20).op(0x56,2).store(11)
 c.local(0).op(0x20).set('fo3LineupRequestV2');c.local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('removeEventListener',2).op(0x29)
 # Reproduce native selectTarget through its existing public query contract.
 # No synthetic row event or rendered/visible index is needed.
 c.local(6).string('post selected players').local(11).call('query',2).op(0x29)
 c.local(6).string('selected player').local(11).call('query',2).op(0x29)
 c.local(7).call('invalidateData',0).op(0x29)
 c.local(7).local(9).set('selectedIndex');c.local(7).local(9).set('scrollPosition');c.local(7).call('validateNow',0).op(0x29).jump(0x10,'done')
 c.label('notready').local(2).number(0).set('readyFrames').jump(0x10,'done')
 c.label('cancel').local(0).op(0x20).set('fo3LineupRequestV2');c.local(0).string('enterFrame').local(0).prop('fo3LineupDriveV3').call('removeEventListener',2).op(0x29)
 c.label('done').op(0x47)
 rec=a.A['body_records'][20];fields=list(rec['fields']);fields[1]=16;code=c.done();a.changed[20]=u30(20)+b''.join(u30(n) for n in fields)+u30(len(code))+code+rec['suffix']

report={};skin_meta=build_skin()
bp=W/'components-Button-baseline.big';report['components-Button']=dict(source_sha256=sha(bp),sha256=sha(W/'components-Button.big'),metadata=skin_meta)
for key,rel,ordinal in [('components-ScrollingList','components/ScrollingList',3451),('TeamManagementScreen','TeamManagementScreen',29)]:
 source=C/'data/ui'/(rel+'.big');(W/(key+'-baseline.big')).write_bytes(source.read_bytes());member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];meta={}
 for i,(kind,body,raw) in enumerate(tags(swf,start,len(swf))):
  if i==ordinal:
   assert kind==82;head=body.index(b'\0',4)+1;before=body[head:];a=ABC(before);old=ABC(before);prefix=f'{key}-{ordinal}';aliases=[]
   if key=='components-ScrollingList':
    expected=ABC((V4/(prefix+'-after.abc')).read_bytes());assert before==expected.data
    # The only constructor change is the reflection name of the new true
    # upgrade symbol; button semantics/natural scale remain unchanged.
    c=Code(a).local(0).op(0x30).local(0).string('fo3LineupEnhanceV3').call('getChildByName',1).store(2);c.local(2).jump(0x11,'done')
    c.op(0x5d,a.name('getDefinitionByName','flash.utils')).string('Fo3LineupUpgradeButton').op(0x46,a.name('getDefinitionByName','flash.utils'),1).op(0x42,0).store(2)
    for n,emit in [('name',lambda c:c.string('fo3LineupEnhanceV3')),('focusable',lambda c:c.op(0x27)),('visible',lambda c:c.op(0x27)),('toggle',lambda c:c.op(0x27)),('autoSize',lambda c:c.string('none')),('label',lambda c:c.string(''))]:c.local(2);emit(c);c.set(n)
    c.local(2).lex('ButtonEvent',a.A['mnns'][a.own('ButtonEvent')]).prop('CLICK').local(0).prop('fo3LineupClickV3').call('addEventListener',2).op(0x29);c.local(0).local(2).call('addChild',1).op(0x29).label('done').op(0x47)
    rec=a.A['body_records'][43];code=c.done();a.changed[43]=u30(43)+b''.join(u30(n) for n in rec['fields'])+u30(len(code))+code+rec['suffix'];changed=[43]
   elif key=='TeamManagementScreen':
    assert before==(V4/(prefix+'-after.abc')).read_bytes();drive(a);changed=[20]
   else:
    assert before==(W.parent/'lineup-enhance-shortcut'/(prefix+'.abc')).read_bytes()
    aliases=[(a.name('fo3PrimaryLockAllowedV5'),85),(a.name('fo3PrimaryIsLockedV5'),86),(a.name('fo3PrimaryRefreshV5'),69)];changed=[]
   data=a.output()
   if aliases:data=addtraits(data,'EnhancePlayerPanel',aliases)
   new=ABC(data)
   for mid,record in old.A['body_records'].items():
    if mid not in changed:assert record['raw']==new.A['body_records'][mid]['raw']
   for mid,code in new.A['body'].items():assert all(code[t]==9 for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at),(prefix,mid)
   (W/(prefix+'-before.abc')).write_bytes(before);(W/(prefix+'-after.abc')).write_bytes(data);raw=tag(kind,body[:head]+data);meta=dict(changed=changed,aliases_only=[85,86,69] if aliases else [],no_new_startup_hooks=True)
  parts.append(raw)
 out=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out));target=W/(key+'.big');pack_archive(source,target,{member:b'CFX'+out[3:8]+zlib.compress(out[8:],9)},[])
 assert all(x[2]==y[2] for x,y in zip(tags(swf,start,len(swf)),tags(out,start,len(out))) if x[0]!=82)
 for n,*_ in bigdir.entries(source):
  if n!=member:assert bigdir.read(source,n)==bigdir.read(target,n)
 report[key]=dict(source_sha256=sha(source),sha256=sha(target),prefix=prefix,metadata=meta,all_other_members_methods_preserved=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
