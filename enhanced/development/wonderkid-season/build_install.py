"""Native-resource-only forty-player season. Build files stay outside production."""
from pathlib import Path
import ast,collections,hashlib,importlib.util,json,math,os,shutil,sqlite3,struct,sys,types,zlib
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path[:0]=[str(W/'work/season_expansion'),'D:/fifaol3/season-display',str(W/'work/experience_levels')]
import roster_import as codec
import build_moments_display as vectors
from avm_patch import ABC,Code,dis,u30
SID=18;TEAM=999918;LEAGUE=2028;LANGS=('chi','eng','ind','kor','tha','vie')
STAT='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
TARGETS={'帕托':94,'巴洛特利':94,'罗比尼奥':94,'古尔库夫':94,'威尔希尔':94,'迪亚比':94,
 '博扬':93,'卡萨诺':93,'朱塞佩·罗西':93,'约维蒂奇':93,'本·阿尔法':93,'纳斯里':93,'马夏尔':93,'阿德勒':93,
 '菲尔·琼斯':91,'迈卡·理查兹':92,'桑顿':91,'巴德施图贝尔':92,'拉诺基亚':91,'扬加-姆比瓦':90,
 '拉斐尔':91,'法比奥':90,'吉布斯':90,'蒙托亚':90,'罗德维尔':91,'巴特兰':92}
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def source_paths():
    paths=[S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json',S/'http_config.py',S/'server_display_zh.json',C/'data/data_0.big',C/'data/ui/libs/Module.big',C/'data/ui/components/Label.big']
    paths += [C/f'data/ui/localization/{lang}.big' for lang in LANGS]
    paths += [C/f'_cache/{prefix}/externalAssets/language_{lang}.big' for prefix in ('games/fo3id','cdn') for lang in LANGS]
    paths += [S/'patches/language_chi.big',S/'patches/验证结果.json']
    return [p for p in paths if p.exists()]
def swf(big,path):
    member=next(n for n,*_ in big.entries(path) if n.endswith('.gfx'));gfx=big.read(path,member)
    plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
    return member,plain,start,list(vectors.tags(plain,start))
def set_body(a,mid,inserts):
    a.modify(mid,inserts);r=a.A['body_records'][mid];code=bytes.fromhex(a.insertions[mid]['updated'])
    a.changed[mid]=u30(mid)+b''.join(u30(f) for f in r['fields'])+u30(len(code))+code+r['suffix']
def build_module(big,out):
    source=C/'data/ui/libs/Module.big';member,plain,start,tags=swf(big,source);result=bytearray(plain[:start]);done=0
    for kind,body,raw in tags:
        if kind==82:
            at=body.index(b'\0',4)+1;a=ABC(body[at:])
            if a.A['cls'] and 'PlayerListUtil' in str(a.A['cls'][0][0]):
                # Only the new season is intercepted. Existing19 and all other
                # original branches, including their callback binding, are retained.
                c=Code(a).local(1).op(0x24,SID).jump(0x14,'old')
                c.op(0x60,a.own('Localization')).string('FO3_CUSTOM_SEASON_18').owncall('getLocalizedString',1).op(0x48).label('old')
                set_body(a,14,{2:c.done()})
                c=Code(a).local(2).op(0x24,SID).jump(0x14,'old')
                c.find('callback').find('Localization').ownprop('Localization').string('COMMON_SEASON_PLUS_NAME_TEXT')
                c.find('getSeasonString').op(0x24,SID).owncall('getSeasonString',1).local(1).owncall('getLocalizedStringWithArgs',3).op(0x4c,a.own('callback'),1).op(0x29).op(0x47).label('old')
                set_body(a,12,{111:c.done()});new=a.output();check=ABC(new)
                assert all(check.A['body_records'][i]['raw']==r['raw'] for i,r in a.A['body_records'].items() if i not in (12,14))
                assert len(check.A['body'])==len(a.A['body'])
                for i in (12,14):
                    (out/f'module-method{i}-before.txt').write_text('\n'.join(dis(a.A,a.A['body'][i])),'utf-8')
                    (out/f'module-method{i}-after.txt').write_text('\n'.join(dis(check.A,check.A['body'][i])),'utf-8')
                (out/'module-before.abc').write_bytes(body[at:]);(out/'module-after.abc').write_bytes(new)
                raw=vectors.tag(kind,body[:at]+new);done+=1
        result+=raw
    assert done==1;struct.pack_into('<I',result,4,len(result))
    vectors.replace_ui_member(source,out/'Module.big',member,b'CFX'+result[3:8]+zlib.compress(result[8:],9),big)
    assert zlib.decompress(big.read(out/'Module.big',member)[8:])==result[8:]
class BitsReader:
    def __init__(self,b,pos):self.b=b;self.p=pos*8
    def u(self,n):
        x=0
        for _ in range(n):x=(x<<1)|((self.b[self.p//8]>>(7-self.p%8))&1);self.p+=1
        return x
def matrix(b,pos):
    r=BitsReader(b,pos)
    if r.u(1):
        n=r.u(5);r.p+=n*2
    if r.u(1):
        n=r.u(5);r.p+=n*2
    n=r.u(5);r.p+=n*2
    return b[pos:(r.p+7)//8]
POLYS=[(1,[(80,30),(920,30),(1000,130),(1000,800),(500,1000),(0,800),(0,130)]),
 (2,[(115,100),(885,100),(930,160),(930,750),(500,920),(70,750),(70,160)]),
 (3,[(140,250),(230,250),(285,590),(335,400),(395,590),(450,250),(540,250),(445,750),(365,750),(335,610),(305,750),(225,750)]),
 (3,[(575,250),(660,250),(660,445),(795,250),(900,250),(725,500),(910,750),(800,750),(660,550),(660,750),(575,750)])]
COLORS={1:(100,175,255,255),2:(24,34,65,255),3:(235,247,255,255)}
def build_label(big,out):
    source=C/'data/ui/components/Label.big';member,plain,start,tags=swf(big,source)
    assert all(not (len(b)>=2 and struct.unpack_from('<H',b)[0] in (65018,65019)) for k,b,_ in tags if k in (2,22,32,39,83))
    oldpoly=vectors.POLYGONS;vectors.POLYGONS=POLYS
    small=vectors.shape(65018,(-40,720,-20,700));large=vectors.shape(65019,(-40,400,-40,440));vectors.POLYGONS=oldpoly
    # The geometry writer's three original solid fills are replaced bytewise.
    for color,new in [(bytes([225,182,78]),bytes(COLORS[1][:3])),(bytes([25,32,47]),bytes(COLORS[2][:3])),(bytes([255,239,187]),bytes(COLORS[3][:3]))]:small=small.replace(color,new,1);large=large.replace(color,new,1)
    result=bytearray(plain[:start]+vectors.tag(2,small)+vectors.tag(2,large));changed=[]
    for kind,body,raw in tags:
        if kind==39 and struct.unpack_from('<H',body)[0] in (144,735):
            sprite,count=struct.unpack_from('<HH',body);parts=list(vectors.tags(body,4));label='';current_matrix=None;wanted=None
            assert not any(k==43 and b.split(b'\0')[0]==b'18season' for k,b,_ in parts)
            for k,b,_ in parts:
                if k==43:label=b.split(b'\0')[0].decode('utf-8')
                if k==26 and struct.unpack_from('<H',b,1)[0]==1 and b[0]&4:
                    current_matrix=matrix(b,3+(2 if b[0]&2 else 0))
                if k==1 and label=='84season':wanted=current_matrix
            assert wanted is not None and parts[-1][0]==0
            cid=65018 if sprite==144 else 65019;flags=6 if sprite==144 else 38
            place=bytes([flags])+struct.pack('<HH',1,cid)+wanted+(b'iconColor\0' if sprite==735 else b'')
            new=struct.pack('<HH',sprite,count+1)+b''.join(r for _,_,r in parts[:-1])+vectors.tag(43,b'18season\0')+vectors.tag(28,struct.pack('<H',1))+vectors.tag(26,place)+vectors.tag(1,b'')+parts[-1][2]
            raw=vectors.tag(kind,new);changed.append(sprite)
        result+=raw
    assert changed==[144,735];struct.pack_into('<I',result,4,len(result))
    vectors.replace_ui_member(source,out/'Label.big',member,b'CFX'+result[3:8]+zlib.compress(result[8:],9),big)
    before=[raw for k,b,raw in tags if not(k==39 and struct.unpack_from('<H',b)[0] in changed)]
    after=[raw for k,b,raw in vectors.tags(result,start) if not(k==39 and struct.unpack_from('<H',b)[0] in changed) and not(k==2 and struct.unpack_from('<H',b)[0] in (65018,65019))]
    assert before==after,'Unrelated Label tags changed'
def png_icon(size):
    def inside(x,y,p):
        odd=False
        for (ax,ay),(bx,by) in zip(p,p[1:]+p[:1]):
            if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:odd=not odd
        return odd
    raw=bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            color=(0,0,0,0)
            for fill,points in POLYS:
                if inside((x+.5)*1000/size,(y+.5)*1000/size,points):color=COLORS[fill]
            raw+=bytes(color)
    def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
def main(out):
    out=out.resolve();assert out.is_relative_to(R) and not out.exists();out.mkdir()
    source_hashes={str(p):sha(p) for p in source_paths()};roster=read(R/'first-roster.json');assert roster['roster_size']==40 and roster['user_approved_roster']
    src=ast.parse((S/'http_config.py').read_text('utf-8'));ns={}
    for n in src.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ROLE_WEIGHTS','POS_ROLE','POSOVR') for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'<current rating>','exec'),ns)
    database=out/'fifadb.sqlite';shutil.copyfile(S/'gamedata/fifadb.sqlite',database);cards=[]
    with sqlite3.connect(database.as_uri(),uri=True) as db:
        db.row_factory=sqlite3.Row;assert db.execute('select count(*) from players where spid/1000000=?',(SID,)).fetchone()[0]==0
        for p in roster['players']:
            row=dict(db.execute('select * from players where spid=?',(p['source_card_spid'],)).fetchone());assert row['playerid']==p['playerid']
            spid=SID*1000000+p['playerid'];target=TARGETS.get(p['name_zh'],92)
            weights=ns['ROLE_WEIGHTS'][ns['POS_ROLE'][row['preferredposition1']]]
            for delta in range(-40,61):
                stats={k:max(1,min(99,row[k]+delta)) for k in STAT};rating=sum(stats[k]*v for k,v in weights.items())//100+5
                if rating>=target:break
            assert rating==target
            row.update(stats);row.update(spid=spid,overallrating=target,teamid=TEAM,leagueid=LEAGUE,headclasscode=0,headtypecode=p['native_appearance']['headtypecode'],hashighqualityhead=1)
            db.execute('insert into players('+','.join('"'+k+'"' for k in row)+') values('+','.join('?' for _ in row)+')',list(row.values()))
            permission=dict(db.execute('select * from permid where spid=?',(p['source_card_spid'],)).fetchone());permission.update(spid=spid,licensed=1,transferable=1)
            db.execute('insert into permid('+','.join('"'+k+'"' for k in permission)+') values('+','.join('?' for _ in permission)+')',list(permission.values()))
            cards.append(dict(fo3_spid=spid,base_playerid=p['playerid'],name_zh=p['name_zh'],name_en=p['name_en'],source_template_spid=p['source_card_spid'],season_id=SID,season='神童',native_plus1_ovr=target,raw_delta=delta,model_mode='existing_dedicated_native',affiliation_teamid=TEAM,affiliation_label='神童',fictional_potential=True))
        db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        db.execute('attach database ? as old',((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',))
        for table in ('players','permid'):
            assert not db.execute(f'select * from old."{table}" except select * from main."{table}"').fetchone()
            assert db.execute(f'select count(*) from main."{table}"').fetchone()[0]-db.execute(f'select count(*) from old."{table}"').fetchone()[0]==40
    big,decrypt,replace,refpack,encrypt=codec.load_codecs(S);archive=out/'data_0.big';shutil.copyfile(C/'data/data_0.big',archive)
    raw=bytes(decrypt.decrypt(big.read(archive,codec.MEMBER)));assert b'SQLite format 3\0'+raw[16:]==(S/'gamedata/fifadb.sqlite').read_bytes()
    encrypted=encrypt(raw[:16]+database.read_bytes()[16:]);replace(archive,codec.MEMBER,refpack(encrypted),len(encrypted))
    changed={codec.MEMBER}
    for lang in LANGS:
        member=f'data/db2/{lang}.db.db2';old=bytes(decrypt.decrypt(big.read(archive,member)));db=sqlite3.connect(':memory:');db.deserialize(b'SQLite format 3\0'+old[16:])
        label='神童' if lang=='chi' else 'Wonderkids';assert not db.execute('select 1 from team where teamid=?',(TEAM,)).fetchone()
        db.execute('insert into team(teamid,teamname,leagueid) values(?,?,?)',(TEAM,label,LEAGUE));db.commit();plain=db.serialize();db.close();new=encrypt(old[:16]+plain[16:]);replace(archive,member,refpack(new),len(new));changed.add(member)
        local=C/f'data/ui/localization/{lang}.big';target=out/f'{lang}.big';shutil.copyfile(local,target);name=next(n for n,*_ in big.entries(local) if '/TEAMNAMES_' in n)
        values=json.loads(big.read(local,name));assert str(TEAM) not in values;values[str(TEAM)]=label;replace(target,name,json.dumps(values,ensure_ascii=False,separators=(',',':')).encode(),0)
    for prefix in ('games/fo3id','cdn'):
        for lang in LANGS:
            source=C/f'_cache/{prefix}/externalAssets/language_{lang}.big'
            if not source.exists():continue
            target=out/'languages'/prefix/f'language_{lang}.big';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            member=next(n for n,*_ in big.entries(source) if 'LANGUAGESTRING' in n);values=json.loads(big.read(source,member));assert 'FO3_CUSTOM_SEASON_18' not in values;values['FO3_CUSTOM_SEASON_18']='神童' if lang=='chi' else 'Wonderkids';replace(target,member,json.dumps(values,ensure_ascii=False,separators=(',',':')).encode(),0)
    central=S/'patches/language_chi.big';target=out/'language_chi.big';shutil.copyfile(central,target);member=next(n for n,*_ in big.entries(central) if 'LANGUAGESTRING' in n);values=json.loads(big.read(central,member));values['FO3_CUSTOM_SEASON_18']='神童';replace(target,member,json.dumps(values,ensure_ascii=False,separators=(',',':')).encode(),0)
    check=read(S/'patches/验证结果.json');check.update(sha256=sha(target),package_bytes=target.stat().st_size,result_keys=len(values));write(out/'language-check.json',check)
    display=read(S/'server_display_zh.json');display['names_by_id']['TEAMNAMES_CHI.json'][str(TEAM)]='神童';write(out/'server_display_zh.json',display)
    registry=read(S/'gamedata/custom_rosters.json');assert all(s['id']!=SID for s in registry['seasons'])
    registry['seasons'].append(dict(id=SID,label='神童',source='Unfulfilled potential fantasy edition; only existing native faces',cards=[c['fo3_spid'] for c in cards]));registry['cards'].extend(cards);write(out/'custom_rosters.json',registry)
    dropdown=read(S/'responses/static_roster.json');entry=dict(season='$FO3_CUSTOM_SEASON_18',value=[18],open='2013-01-01T00:00:00.000Z',close='2099-12-31T00:00:00.000Z')
    with sqlite3.connect(database) as db:
        mean=sum(c['native_plus1_ovr'] for c in cards)/40;where=len(dropdown['seasons'])
        for i,row in enumerate(dropdown['seasons']):
            ids=[int(x) for x in row.get('value',[]) if int(x)>0]
            if not ids:continue
            avg=db.execute('select avg(('+ns['POSOVR']+')+5) from players p where spid/1000000 in ('+','.join(map(str,ids))+')').fetchone()[0]
            if avg is not None and mean>avg:where=i;break
    dropdown['seasons'].insert(where,entry);write(out/'static_roster.json',dropdown)
    source=(S/'http_config.py').read_bytes();needle=b'if __name__ == "__main__":';assert source.count(needle)==1;(out/'http_config.py').write_bytes(source.replace(needle,b'import wonderkid_runtime\nwonderkid_runtime.install(sys.modules[__name__])\n\n'+needle));shutil.copyfile(R/'wonderkid_runtime.py',out/'wonderkid_runtime.py')
    build_module(big,out);build_label(big,out)
    for size,letter,pixels in [('small','s',32),('large','l',128)]:
        target=out/'crests'/size/f'{letter}{TEAM}.png';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(png_icon(pixels))
    portraits=[]
    for p in roster['players']:
        ids=[p['source_card_spid'],p['playerid']]+[r[0] for r in p['source_card_options']]
        source=next((C/f'_cache/games/fo3id/externalAssets/players/p{pid}.png' for pid in ids if (C/f'_cache/games/fo3id/externalAssets/players/p{pid}.png').exists()),None)
        if source:
            dest=out/'portraits'/f'p{SID*1000000+p["playerid"]}.png';dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest);portraits.append(dest.name)
    spec=importlib.util.spec_from_file_location('layout',W/'tools/check_data0_layout.py');layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout);check=layout.inspect(archive,C/'data/data_0.big',changed_members=changed,expected_count=271);assert check['status']=='PASS';write(out/'layout.json',check)
    assert source_hashes=={str(p):sha(p) for p in source_paths()},'Concurrent source changed; rebuild required'
    write(out/'cards.json',cards)
    report=dict(status='BUILD_PASS',season=18,cards=40,plus1_min=min(c['native_plus1_ovr'] for c in cards),plus1_max=max(c['native_plus1_ovr'] for c in cards),mean=mean,source_hashes=source_hashes,changed_data0_members=sorted(changed),new_model_files=0,portraits=portraits,output_hashes={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},native_verified=False)
    write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps({k:v for k,v in report.items() if k not in ('source_hashes','output_hashes','portraits')}))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=R/'install-build-v1');main(p.parse_args().out)
