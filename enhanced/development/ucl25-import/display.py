"""Minimal native 25UCL name/badge delta on current Module/Label resources."""
import re,struct,zlib
from common import *
import bigdir
sys.path.insert(0,str(R.parent/'season-display'))
import build_moments_display as vectors
from avm_patch import ABC,Code,dis,u30

KEY='FO3_CUSTOM_SEASON_856'


def swf(path):
    member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'));gfx=bigdir.read(path,member)
    plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
    return member,plain,start,list(vectors.tags(plain,start))


def set_body(a,mid,pos,code):
    a.modify(mid,{pos:code});record=a.A['body_records'][mid];new=bytes.fromhex(a.insertions[mid]['updated'])
    a.changed[mid]=u30(mid)+b''.join(u30(f) for f in record['fields'])+u30(len(new))+new+record['suffix']


def build_module(out):
    source=C/'data/ui/libs/Module.big';member,plain,start,tags=swf(source);result=bytearray(plain[:start]);changed=0
    for kind,body,raw in tags:
        if kind==82:
            at=body.index(b'\0',4)+1;a=ABC(body[at:])
            if a.A['cls'] and 'PlayerListUtil' in str(a.A['cls'][0][0]):
                assert not any(KEY in line for line in dis(a.A,a.A['body'][14]))
                assert any(re.match(r'\s*21: jump',line) for line in dis(a.A,a.A['body'][12]))
                c=Code(a).local(1).number(SID).jump(0x14,'old')
                c.op(0x60,a.own('Localization')).string(KEY).owncall('getLocalizedString',1).op(0x48).label('old')
                set_body(a,14,2,c.done())
                # Intercept just after the actual season is assigned to local 2,
                # before the old switch; every old-season path remains original.
                c=Code(a).local(2).number(SID).jump(0x14,'old')
                c.find('callback').find('Localization').ownprop('Localization').string('COMMON_SEASON_PLUS_NAME_TEXT')
                c.find('getSeasonString').number(SID).owncall('getSeasonString',1).local(1).owncall('getLocalizedStringWithArgs',3)
                c.op(0x4c,a.own('callback'),1).op(0x29).op(0x47).label('old')
                set_body(a,12,21,c.done());new=a.output();check=ABC(new)
                assert all(check.A['body_records'][i]['raw']==v['raw'] for i,v in a.A['body_records'].items() if i not in (12,14))
                for mid in (12,14):
                    (out/f'module-{mid}-before.txt').write_text('\n'.join(dis(a.A,a.A['body'][mid])),encoding='utf8')
                    (out/f'module-{mid}-after.txt').write_text('\n'.join(dis(check.A,check.A['body'][mid])),encoding='utf8')
                raw=vectors.tag(kind,body[:at]+new);changed+=1
        result+=raw
    assert changed==1;struct.pack_into('<I',result,4,len(result))
    vectors.replace_ui_member(source,out/'Module.big',member,b'CFX'+result[3:8]+zlib.compress(result[8:],9),bigdir)


def matrix(data,pos):
    helper=load(R.parent/'wonderkid-season/build_install.py','ucl_badge_matrix_reader')
    return helper.matrix(data,pos)


def build_label(out):
    source=C/'data/ui/components/Label.big';member,plain,start,tags=swf(source)
    assert not any(len(b)>=2 and struct.unpack_from('<H',b)[0] in (65050,65051) for k,b,_ in tags if k in (2,22,32,39,83))
    # Repo-native vector badge: dark blue shield and simple 2/5/U strokes.
    polygons=[(1,[(80,30),(920,30),(1000,130),(1000,800),(500,1000),(0,800),(0,130)]),
      (2,[(115,100),(885,100),(930,160),(930,750),(500,920),(70,750),(70,160)])]
    def rect(x,y,w,h):return (3,[(x,y),(x+w,y),(x+w,y+h),(x,y+h)])
    # Seven-segment 2 and 5; U retains a distinctive open top.
    for x,segments in [(150,'abged'),(390,'afgcd')]:
        boxes={'a':(0,250,170,45),'b':(125,250,45,220),'c':(125,455,45,220),'d':(0,630,170,45),
            'e':(0,455,45,220),'f':(0,250,45,220),'g':(0,440,170,45)}
        for segment in segments:
            xx,y,w,h=boxes[segment];polygons.append(rect(x+xx,y,w,h))
    polygons += [rect(650,250,45,425),rect(790,250,45,425),rect(650,630,185,45)]
    previous=vectors.POLYGONS
    try:
        vectors.POLYGONS=polygons
        shapes=[vectors.shape(65050,(-40,720,-20,700)),vectors.shape(65051,(-40,400,-40,440))]
    finally:vectors.POLYGONS=previous
    replacements=[(bytes([225,182,78]),bytes([87,163,239])),(bytes([25,32,47]),bytes([12,27,62])),(bytes([255,239,187]),bytes([235,245,255]))]
    for i,shape in enumerate(shapes):
        for old,new in replacements:shape=shape.replace(old,new,1)
        shapes[i]=shape
    result=bytearray(plain[:start]);inserted=False;changes=[]
    for kind,body,raw in tags:
        if not inserted and kind!=69:
            result+=vectors.tag(2,shapes[0])+vectors.tag(2,shapes[1]);inserted=True
        if kind==39 and struct.unpack_from('<H',body)[0] in (144,735):
            sprite,count=struct.unpack_from('<HH',body);parts=list(vectors.tags(body,4));label='';current=None;wanted=None
            for k,b,_ in parts:
                if k==43:label=b.split(b'\0')[0].decode('utf8');assert label!='856season'
                if k==26 and struct.unpack_from('<H',b,1)[0]==1 and b[0]&4:
                    current=matrix(b,3+(2 if b[0]&2 else 0))
                if k==1 and label=='84season':wanted=current
            assert wanted is not None and parts[-1][0]==0
            cid=65050 if sprite==144 else 65051;flags=6 if sprite==144 else 38
            place=bytes([flags])+struct.pack('<HH',1,cid)+wanted+(b'iconColor\0' if sprite==735 else b'')
            extra=vectors.tag(43,b'856season\0')+vectors.tag(26,place)+vectors.tag(1,b'')
            body=struct.pack('<HH',sprite,count+1)+b''.join(p[2] for p in parts[:-1])+extra+parts[-1][2]
            raw=vectors.tag(39,body);changes.append(sprite)
        result+=raw
    assert changes==[144,735] or sorted(changes)==[144,735]
    struct.pack_into('<I',result,4,len(result))
    vectors.replace_ui_member(source,out/'Label.big',member,b'CFX'+result[3:8]+zlib.compress(result[8:],9),bigdir)
    _,_,_,after=swf(out/'Label.big')
    for k,b,_ in after:
        if k==39 and struct.unpack_from('<H',b)[0] in (144,735):
            assert sum(t==43 and v==b'856season\0' for t,v,_ in vectors.tags(b,4))==1


def build(out):
    out.mkdir(parents=True,exist_ok=True);build_module(out);build_label(out)
    write(out/'display-validation.json',dict(status='STATIC_DISPLAY_EXTENSION_PASS',season=SID,
        module_modified_methods=[12,14],badge_modified_sprites=[144,735],GUI_used=False,native_verified=False,
        files={n:sha(out/n) for n in ('Module.big','Label.big')}))


if __name__=='__main__':build(R/'display-build')
