"""Patch only the native draft search, preserving every other method and asset."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parent
WORK = Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online')
sys.path.insert(0, str(WORK/'work/bp_client'))
sys.path.insert(0, r'D:\FO3ID\server\tools\re')
from avm_patch import ABC, Code, u30, parse, dis
import bigdir

source = Path(r'D:\FO3ID\32795\data\ui\TeamManagementDraftPackScreen.big')
member = next(n for n, *_ in bigdir.entries(source) if n.endswith('.gfx'))
gfx = bigdir.read(source, member)
d = b'FWS' + gfx[3:8] + zlib.decompress(gfx[8:])
start = 8+(5+4*(d[8]>>3)+7)//8+4
pos = start
parts = [d[:start]]
changed = []
while pos+2 <= len(d):
    at = pos
    tagword = struct.unpack_from('<H', d, pos)[0]; pos += 2
    kind, size = tagword >> 6, tagword & 63
    if size == 63:
        size = struct.unpack_from('<I', d, pos)[0]; pos += 4
    payload = d[pos:pos+size]; pos += size
    if kind != 82:
        parts.append(d[at:pos]); continue
    abc_start = payload.index(b'\0',4)+1
    a = ABC(payload[abc_start:])
    cls = next((x for x in a.A['cls'] if x[0] == 'TeamManagementDraftPackScreen'), None)
    if cls is None:
        parts.append(d[at:pos]); continue
    mi = next(i for kind, name, i in cls[3] if kind == 'method' and name == 'searchInLocalDatabase')
    fields = a.A['body_records'][mi]['fields']
    scope = fields[2]+1
    # Callbacks retain the search method's lexical 'this'; no new class fields are added.
    after_id = len(a.A['meth'])
    c = Code(a).local(0).op(0x30)
    c.find('setSearchingComplete').op(0x26).owncall('setSearchingComplete',1).op(0x29).op(0x47)
    assert a.add_method(c.done(),scope+1) == after_id
    response_id = len(a.A['meth'])+1
    c = Code(a).local(0).op(0x30)
    c.find('_searchingPriceData').local(1).prop('body').op(0x80,a.name('Array')).ownset('_searchingPriceData')
    c.lex('PlayerListUtil','fok.utils').find('_searchingPriceData').ownprop('_searchingPriceData')
    c.op(0x40,after_id).call('expandPlayersStaticData',2).op(0x29).op(0x47)
    assert a.add_method(c.done(),scope) == response_id
    c = Code(a)
    c.local(0).ownprop('_itemId').number(97200000).jump(0x15,'normal')
    c.local(0).ownprop('_itemId').number(97300000).jump(0x18,'normal')
    c.local(0).ownprop('_isAbleToFind').jump(0x12,'done')
    c.local(0).ownprop('leagueComboBox').prop('data').jump(0x12,'done')
    c.local(0).owncall('startSearch',0).op(0x29)
    c.lex('ResourceController','fok.net').prop('instance')
    c.lex('StringUtil','fok.utils').string('/packchoice/{0}/search?q={1}&league={2}&team={3}')
    c.local(0).ownprop('_itemId').local(0).ownprop('searchPlayerName').prop('text')
    c.local(0).ownprop('leagueComboBox').prop('data').prop('value')
    c.local(0).ownprop('teamComboBox').prop('data').prop('value')
    c.call('createEncodedUri',5).call('pushGET',1)
    c.lex('NetEvent','fok.events').prop('ON_COMPLETE').op(0x40,response_id).local(0)
    c.call('on',3).call('end',0).op(0x29)
    c.label('done').op(0x47).label('normal')
    # Original instructions 0..6 establish 'this' on the scope stack; retain them.
    a.modify(mi,{7:c.done()})
    out = a.output()
    rebuilt = payload[:abc_start] + out
    parts.append(struct.pack('<HI', (82<<6)|63, len(rebuilt))+rebuilt)
    changed.append({'class':cls[0],'method':mi,'added_callback_methods':[after_id,response_id],
                    'other_existing_methods_identical':True})
    (ROOT/'native/patched-search.txt').write_text('\n'.join(dis(parse(out,0),parse(out,0)['body'][mi])),encoding='utf-8')
assert len(changed)==1
swf = b''.join(parts)
swf = swf[:4]+struct.pack('<I',len(swf))+swf[8:]
updated = b'CFX'+gfx[3:4]+struct.pack('<I',len(swf))+zlib.compress(swf[8:],9)
target = ROOT/source.name
target.write_bytes(source.read_bytes())
bigdir.patch(target,{member:updated})
assert bigdir.read(target,member)==updated
original_bytes = source.read_bytes(); output = target.read_bytes()
for name,off,size,usize in bigdir.entries(source):
    if name==member:continue
    _,no,ns,nu=next(e for e in bigdir.entries(target) if e[0]==name)
    assert (size,usize)==(ns,nu) and original_bytes[off:off+size]==output[no:no+ns]
report = dict(status='PASS', source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),member=member,changes=changed,
              native_runtime_verified=False)
(ROOT/'native/build-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
