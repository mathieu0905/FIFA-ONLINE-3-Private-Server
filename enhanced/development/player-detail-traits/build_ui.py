"""Incremental popup tab build from current production; never writes production."""
from inspect_ui import *
import hashlib,collections,struct
from avm_patch import Code,u30,instructions
from build_moments_display import tag,replace_ui_member
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(a,idx,code,fields):
 old=a.A['body_records'][idx];assert old['exceptions']==0
 a.changed[idx]=u30(idx)+b''.join(u30(v) for v in fields)+u30(len(code))+code+old['suffix']
def invoke(a,mid):return Code(a).op(0x40,mid).local(0).local(1).op(0x41,1).op(0x29).done()
def addfunc(a,code,scope,locals_count,stack=32):
 idx=len(a.A['meth'])+len(a.methods)
 sig=u30(1)+u30(a.name('void'))+u30(a.name('Object'))+b'\0\0'
 body=u30(idx)+u30(stack)+u30(locals_count)+u30(scope)+u30(scope+1)+u30(len(code))+code+b'\0\0'
 a.methods.append((sig,body));return idx
def build(out):
 source=C/'data/ui/SquadAssets.big';baseline=sha(source);dbhash=sha(S/'gamedata/fifadb.sqlite')
 member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 gfx=bigdir.read(source,member);data=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
 start=8+(5+4*(data[8]>>3)+7)//8+4;output=bytearray(data[:start]);count=0
 with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  hist=collections.defaultdict(set)
  for pid,tid in db.execute('SELECT playerid,teamid FROM playerhistory'):hist[pid].add(tid)
 for kind,body,raw in tags(data,start):
  if kind==82:
   pos=body.index(b'\0',4)+1;a=ABC(body[pos:])
   if any(c[0]=='PlayerDetailPopup' for c in a.A['cls']):
    # Build a bounded-stack fallback from the exact same guarded database. The
    # native client suppresses history on many cards (historyopen=0).
    # Prefer native current clubhistory when available; union the snapshot to
    # avoid losing valid household entries through that display permission.
    c=Code(a).local(0).op(0x30)
    c.local(0).prop('dataProvider').op(0x24,0).ownprop('[late]').prop('staticdata').store(2)
    c.local(2).prop('playerid').store(3)
    # Some source cards expose only SPID; identity is its last six digits.
    c.local(3).jump(0x11,'pid_ready')
    c.local(0).prop('dataProvider').op(0x24,0).ownprop('[late]').prop('spid').number(1000000).op(0xa4).store(3)
    c.label('pid_ready').string('').store(4)
    items=sorted(hist.items())
    for i in range(0,len(items),48):
     chunk=items[i:i+48];nxt='chunk_'+str(i)
     c.local(3).number(chunk[0][0]).jump(0x15,nxt)
     c.local(3).number(chunk[-1][0]).jump(0x17,nxt)
     for pid,clubs in chunk:c.string(str(pid)).string(','.join(map(str,sorted(clubs))))
     c.op(0x55,len(chunk)).local(3).op(0x66,a.own('[late]')).store(4)
     c.jump(0x10,'lookup_done').label(nxt)
    c.label('lookup_done')
    c.local(4).jump(0x11,'has_history').string('').store(4)
    c.label('has_history').local(4).string(',').call('split',1).store(5)
    # Include the current team, matching tc_static / active_teamcolors exactly.
    c.local(5).local(2).prop('teamid').call('push',1).op(0x29)
    c.local(2).prop('clubhistory').store(6)
    c.local(6).jump(0x12,'native_done').number(0).store(7)
    c.label('native_loop').op(0x09).local(7).local(6).prop('length').jump(0x18,'native_done')
    c.local(5).local(6).local(7).ownprop('[late]').prop('teamid').call('push',1).op(0x29)
    c.local(7).op(0x91).store(7).jump(0x10,'native_loop').label('native_done')
    c.op(0x55,0).store(6).op(0x56,0).store(7).number(0).store(8)
    c.label('loop').op(0x09).local(8).local(5).prop('length').jump(0x18,'done')
    c.local(5).local(8).ownprop('[late]').op(0x73).store(9)
    c.local(9).number(0).jump(0x16,'next')
    # Season/all-star placeholders are not real clubs; do not call them careers.
    c.local(9).number(900000).jump(0x18,'next')
    c.local(6).local(9).ownprop('[late]').jump(0x11,'next')
    c.local(6).local(9).op(0x26).op(0x61,a.own('[late]'))
    c.local(7).string('stat_name').find('Localization').ownprop('Localization').local(9).call('TEAMNAME',1)
    c.string('stat_value').string('具备户口').op(0x55,2).call('push',1).op(0x29)
    c.label('next').local(8).op(0x91).store(8).jump(0x10,'loop')
    c.label('done').local(7).prop('length').jump(0x11,'rows_ready')
    c.local(7).string('stat_name').string('暂无可显示的俱乐部户口').string('stat_value').string('').op(0x55,2).call('push',1).op(0x29)
    c.label('rows_ready')
    c.local(0).ownprop('statList').op(0x26).set('visible')
    c.local(0).ownprop('statList').find('DataProvider').local(7).op(0x4a,a.own('DataProvider'),1).set('dataProvider')
    c.local(0).ownprop('statList').local(0).ownprop('ALL_STATS_LIST_ROW_COUNT').set('rowCount')
    c.local(0).ownprop('statList').number(0).set('selectedIndex')
    c.local(0).ownprop('statList').number(0).set('scrollPosition').op(0x47)
    history_mid=addfunc(a,c.done(),12,10,100)
    # Split histories out of the trait page; show every IM trait rather than
    # silently truncating the strengthened list to the original eight labels.
    e=Code(a).local(0).op(0x30)
    e.local(0).ownprop('myPlayerTraitInfo').store(2)
    for field in ('clubhistorypanel','barMC'):
     e.local(2).prop(field).jump(0x12,'skip_'+field)
     e.local(2).prop(field).op(0x27).set('visible').label('skip_'+field)
    e.local(2).prop('content').store(3)
    e.local(3).string('_imNativeTraitList').call('getChildByName',1).store(4)
    e.local(4).jump(0x12,'removed')
    e.local(3).local(4).call('removeChild',1).op(0x29).label('removed')
    e.local(0).prop('dataProvider').number(0).ownprop('[late]').store(4)
    e.local(4).prop('spid').number(1000000).op(0xa3).op(0x73).number(84).jump(0x14,'end')
    e.local(3).prop('_traitDescription1').store(5)
    # Use the existing embedded Chinese font and original label text format.
    e.lex('TextField','flash.text').op(0x42,0).store(6)
    e.local(6).string('_imNativeTraitList').set('name')
    e.local(6).local(5).prop('x').set('x')
    e.local(6).local(5).prop('y').set('y')
    e.local(6).local(5).prop('width').set('width')
    e.local(6).local(5).prop('textField').prop('defaultTextFormat').set('defaultTextFormat')
    e.local(6).local(5).prop('textField').prop('embedFonts').set('embedFonts')
    for prop,val in (('multiline',True),('wordWrap',False),('selectable',False),('mouseEnabled',False)):
     e.local(6).op(0x26 if val else 0x27).set(prop)
    e.local(6).string('left').set('autoSize')
    e.op(0x56,0).store(7).number(0).store(8)
    e.label('traits_loop').op(0x09).local(8).local(4).prop('__traits').prop('length').jump(0x18,'traits_done')
    e.local(7).find('Localization').ownprop('Localization').string('PLAYER_TRAIT_')
    e.find('PlayerListUtil').ownprop('PlayerListUtil').prop('PLAYER_TRAITS').local(4).prop('__traits').local(8).ownprop('[late]').ownprop('[late]').op(0xa0)
    e.call('getLocalizedString',1).call('push',1).op(0x29)
    e.local(8).op(0x91).store(8).jump(0x10,'traits_loop').label('traits_done')
    e.local(6).local(7).string('\n').call('join',1).set('text')
    e.local(3).local(6).call('addChild',1).op(0x29)
    for i in range(1,9):e.local(3).prop('_traitDescription'+str(i)).op(0x27).set('visible')
    e.label('end').local(0).ownprop('myTraitScrollPanel').call('refresh',0).op(0x29)
    e.local(0).ownprop('myTraitScrollPanel').number(0).call('setScrollPercent',1).op(0x29).op(0x47)
    traits_mid=addfunc(a,e.done(),12,9)
    # Three ordinary tabs; optional price tab is now fourth.
    code=bytearray(a.A['body'][26]);assert code[219:221]==b'\x24\x02';code[220]=3;a.A['body'][26]=bytes(code)
    label=Code(a).local(0).ownprop('positionTabBar').number(2).string('俱乐部经历').owncall('setTabLabel',2).op(0x29).done()
    a.modify(26,{270:label})
    # Keep price behavior and all contract/stat controls. Dispatch the new page
    # after the existing common visibility reset, before normal tab branches.
    code=bytearray(a.A['body'][24]);assert code[455]==0xd0 and code[456]==0x66
    code[455:458]=b'\x24\x03\x02';a.A['body'][24]=bytes(code)
    branch=Code(a).local(1).prop('tabIndex').number(2).jump(0x14,'old')
    branch.raw(invoke(a,history_mid)).op(0x47).label('old')
    a.modify(24,{123:branch.done(),438:invoke(a,traits_mid)})
    updated=a.output();check=ABC(updated)
    assert set(a.changed)=={24,26}
    for mid,r in a.A['body_records'].items():
     if mid not in a.changed:assert check.A['body_records'][mid]['raw']==r['raw']
    (out/'popup-before.abc').write_bytes(body[pos:]);(out/'popup-after.abc').write_bytes(updated)
    for mid in (24,26,history_mid,traits_mid):(out/('method-'+str(mid)+'.txt')).write_text('\n'.join(dis(check.A,check.A['body'][mid])),'utf8')
    raw=tag(kind,body[:pos]+updated);count+=1
  output+=raw
 assert count==1
 struct.pack_into('<I',output,4,len(output))
 replacement=b'CWS'+output[3:8]+zlib.compress(output[8:])
 replace_ui_member(source,out/'SquadAssets.big',member,replacement,bigdir)
 assert sha(source)==baseline and sha(S/'gamedata/fifadb.sqlite')==dbhash
 proof=dict(source=str(source),source_sha256=baseline,output_sha256=sha(out/'SquadAssets.big'),changed_methods=[24,26],added_history_method=history_mid,
  fallback_identities=len(hist),fallback_history_sha256=hashlib.sha256(json.dumps({str(p):sorted(v) for p,v in sorted(hist.items())},sort_keys=True).encode()).hexdigest(),
  history_database_sha256=dbhash,added_traits_method=traits_mid,static_only=True,native_gui_verified=False,formal_written=False)
 (out/'ui-report.json').write_text(json.dumps(proof,indent=2),'utf8');return proof
if __name__=='__main__':
 out=ROOT/'ui-build';out.mkdir(exist_ok=True);print(json.dumps(build(out)))


