"""Patch one default-name branch in PlayerListUtil; never writes production."""
from pathlib import Path
import argparse, hashlib, json, struct, sys, zlib
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path[:0] = ['D:/FO3ID/server/tools/re','D:/fifaol3/season-display',
 'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_levels']
import bigdir
from build_moments_display import tags, tag, replace_ui_member
from avm_patch import ABC, Code, dis, u30

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(out,expected_source):
    assert out.resolve().is_relative_to(ROOT)
    out.mkdir(exist_ok=False)
    source = Path('D:/FO3ID/32795/data/ui/libs/Module.big')
    assert sha(source) == expected_source
    member = next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    gfx = bigdir.read(source,member); data = b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
    start = 8+(5+4*(data[8]>>3)+7)//8+4
    output = bytearray(data[:start]); count = 0
    for kind, body, raw in tags(data,start):
        if kind == 82:
            pos = body.index(b'\0',4)+1; a = ABC(body[pos:])
            if a.A['cls'] and 'PlayerListUtil' in str(a.A['cls'][0][0]):
                old = a.A['body'][12]; assert 'lookupswitch' in '\n'.join(dis(a.A,old))
                baseline=ROOT/'callback-v1/old.abc'
                if baseline.exists():assert old==ABC(baseline.read_bytes()).A['body'][12], 'Target method changed; review required'
                c = Code(a)
                for season in (19,): c.local(2).op(0x24,season).jump(0x13,'custom')
                c.jump(0x10,'original')
                c.label('custom').find('callback').find('Localization').ownprop('Localization')
                c.string('COMMON_SEASON_PLUS_NAME_TEXT').find('getSeasonString').local(2).owncall('getSeasonString',1)
                c.local(1).owncall('getLocalizedStringWithArgs',3).op(0x4c,a.own('callback'),1).op(0x29).op(0x47)
                c.label('original')
                insert = c.done()
                a.modify(12,{111:insert})
                # Existing stack maximum is sufficient; no unrelated header widening.
                rec = a.A['body_records'][12]; fields=rec['fields']; assert fields[0]>=5
                updated = bytes.fromhex(a.insertions[12]['updated'])
                a.changed[12]=u30(12)+b''.join(u30(f) for f in fields)+u30(len(updated))+updated+rec['suffix']
                newabc = a.output(); check=ABC(newabc)
                assert all(check.A['body_records'][i]['raw']==r['raw'] for i,r in a.A['body_records'].items() if i!=12)
                assert check.values == a.values and not any(a.additions) and not a.methods
                (out/'old.abc').write_bytes(body[pos:]);(out/'new.abc').write_bytes(newabc)
                (out/'method12-before.txt').write_text('\n'.join(dis(a.A,old)),'utf-8')
                (out/'method12-after.txt').write_text('\n'.join(dis(check.A,updated)),'utf-8')
                (out/'relocation.json').write_text(json.dumps(a.insertions[12],indent=2),'utf-8')
                raw=tag(kind,body[:pos]+newabc);count+=1
        output+=raw
    assert count==1
    struct.pack_into('<I',output,4,len(output))
    replacement=b'CWS'+bytes(output[3:8])+zlib.compress(bytes(output[8:]))
    replace_ui_member(source,out/'Module.big',member,replacement,bigdir)
    readback=bigdir.read(out/'Module.big',member)
    assert zlib.decompress(readback[8:])==bytes(output[8:])
    original_tags=list(tags(data,start));new_tags=list(tags(output,start))
    diffs=[i for i,(x,y) in enumerate(zip(original_tags,new_tags)) if x!=y]
    assert len(original_tags)==len(new_tags) and len(diffs)==1
    proof=dict(status='ONE_METHOD_ONLY_BUILD_PASS',source=str(source),source_sha256=sha(source),
      module_sha256=sha(out/'Module.big'),changed_method=12,insert_offset=111,insert_bytes=len(insert),
      all_other_method_records_exact=True,constant_pools_exact=True,all_other_swf_tags_exact=True,
      all_other_big_compressed_members_exact=True,native_verified=False,production_written=False)
    (out/'build.json').write_text(json.dumps(proof,indent=2),'utf-8');print(json.dumps(proof))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'callback-v1');p.add_argument('--source-sha',default='dd0abd209945fe53930d6acfaa0747daf03cffe4f65bdc690c3641584ccbaab7');a=p.parse_args()
    build(a.out.resolve(),a.source_sha)
