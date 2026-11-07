"""Static inspection of exact current GFX; no game process or GUI access."""
import re,struct,zlib,sys
sys.dont_write_bytecode=True
from common import *
import bigdir
sys.path.insert(0,str(R.parent/'season-display'))
import build_moments_display as vectors
from avm_patch import ABC,dis


def main():
    files={};report={}
    for filename in ('libs/Module.big','components/Label.big'):
        p=C/'data/ui'/filename;files[str(p)]=sha(p)
        member=next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx'));gfx=bigdir.read(p,member)
        plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
        if filename.startswith('libs'):
            found=[]
            for kind,body,_ in vectors.tags(plain,start):
                if kind!=82:continue
                at=body.index(b'\0',4)+1;abc=ABC(body[at:])
                if abc.A['cls'] and 'PlayerListUtil' in str(abc.A['cls'][0][0]):
                    item=dict(class_name=str(abc.A['cls'][0][0]),methods={str(i):dis(abc.A,abc.A['body'][i]) for i in (12,14)})
                    found.append(item)
            report['season_name_methods']=found
        else:
            sprites={};ids=[]
            for kind,body,_ in vectors.tags(plain,start):
                if kind in (2,22,32,39,83):ids.append(struct.unpack_from('<H',body)[0])
                if kind==39 and struct.unpack_from('<H',body)[0] in (144,735):
                    sprites[str(struct.unpack_from('<H',body)[0])]=dict(frame_count=struct.unpack_from('<H',body,2)[0],
                        labels=[b.split(b'\0')[0].decode('utf8') for k,b,_ in vectors.tags(body,4) if k==43])
            report['badge_sprites']=sprites;report['unused_shape_ids']=[i for i in (65050,65051) if i not in ids]
    assert len(report['season_name_methods'])==1
    assert all('856season' not in s['labels'] for s in report['badge_sprites'].values())
    assert report['unused_shape_ids']==[65050,65051]
    report.update(status='STATIC_SEASON_EXTENSION_AUDIT_PASS',input_hashes=files,GUI_used=False,native_verified=False)
    write(R/'display-audit.json',report)
    print('STATIC_SEASON_EXTENSION_AUDIT_PASS; audited PlayerListUtil methods 12/14, two badge sprites, free shape IDs 65050/65051; no GUI.')


if __name__=='__main__':main()
