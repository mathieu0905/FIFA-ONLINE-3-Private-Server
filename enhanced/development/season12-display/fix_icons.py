"""Incremental main-client season12 badge repair. Never controls the game or services."""
from pathlib import Path
import argparse, datetime, importlib.util, json, os, re, shutil, struct, subprocess, sys, zlib
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
sys.path[:0]=['D:/fifaol3','D:/fifaol3/season-display','D:/FO3ID/server/tools/re']
import install_bulk_seasons as tx
import bigdir
import build_moments_display as vector
from build_moments_display import tags, tag
MANIFEST='patches/season-icons-installed.json'
RECEIPT='patches/season-icons-receipt.json'
SELF='patches/season_icons_preflight.py'
IDS={45,609,611,613}

class Bits:
    def __init__(self,b): self.b=b; self.p=0
    def u(self,n):
        v=0
        for _ in range(n): v=(v<<1)|((self.b[self.p//8]>>(7-self.p%8))&1);self.p+=1
        return v
    def s(self,n):
        v=self.u(n);return v-(1<<n) if v&(1<<(n-1)) else v

def bounds(b):
    r=Bits(b[2:]);n=r.u(5);return tuple(r.s(n) for _ in range(4))

def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def plain(p):
    n=next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx'))
    g=bigdir.read(p,n);d=b'FWS'+g[3:8]+zlib.decompress(g[8:])
    return n,d,8+(5+4*(d[8]>>3)+7)//8+4

def polygons():
    out=[(1,[(80,35),(920,35),(990,125),(990,800),(500,980),(10,800),(10,125)]),
         (2,[(120,110),(880,110),(920,160),(920,750),(500,900),(80,750),(80,160)])]
    glyphs=['111/010/010/010/111','111/100/100/100/111','111/101/101/101/111','1001/1101/1011/1001/1001']
    x=130
    for glyph in glyphs:
        rows=glyph.split('/')
        for y,row in enumerate(rows):
            for col,bit in enumerate(row):
                if bit=='1':
                    a=x+col*46;b=300+y*82
                    out.append((3,[(a,b),(a+46,b),(a+46,b+82),(a,b+82)]))
        x+=(len(rows[0])+1)*46
    return out

def references(ts):
    found=[]
    for k,b,_ in ts:
        if k!=39:continue
        parent=struct.unpack_from('<H',b)[0];frame=1;label=''
        for sk,sb,_ in tags(b,4):
            if sk==43:label=sb.rstrip(b'\0').decode('latin1')
            if sk==26 and sb[0]&2:
                found.append(dict(parent=parent,frame=frame,label=label,child=struct.unpack_from('<H',sb,3)[0]))
            elif sk==4:found.append(dict(parent=parent,frame=frame,label=label,child=struct.unpack_from('<H',sb)[0]))
            if sk==1:frame+=1
    return found

def check_vectors(body):
    r=Bits(body[2:]);n=r.u(5);rect=[r.s(n) for _ in range(4)];r.p=(r.p+7)//8*8
    assert r.u(8)==3
    colors=[]
    for _ in range(3):assert r.u(8)==0;colors.append([r.u(8) for _ in range(3)])
    assert colors==[[225,182,78],[25,32,47],[255,239,187]] and r.u(8)==0
    assert r.u(4)==2 and r.u(4)==0
    paths=[];cur=None;x=y=0
    while True:
        if not r.u(1):
            flags=r.u(5)
            if not flags:break
            assert flags==3;n=r.u(5);x=r.s(n);y=r.s(n);fill=r.u(2)
            cur=dict(fill=fill,points=[(x,y)]);paths.append(cur)
        else:
            assert r.u(1)==1;n=r.u(4)+2
            if r.u(1):x+=r.s(n);y+=r.s(n)
            elif r.u(1):y+=r.s(n)
            else:x+=r.s(n)
            cur['points'].append((x,y))
    assert len(paths)==len(polygons()) and all(p['points'][0]==p['points'][-1] for p in paths)
    assert len(body[2:])*8-r.p<8
    return dict(bounds=rect,closed_paths=len(paths),no_external_textures=True)

def build(out):
    assert out.is_relative_to(ROOT) and not out.exists();out.mkdir()
    source=C/'data/ui/components/Label.big';member,d,start=plain(source);ts=list(tags(d,start))
    refs=references(ts)
    expected={(144,7,'12season',45),(614,1,'',609),(614,2,'',611),(614,3,'',613)}
    actual={(r['parent'],r['frame'],r['label'],r['child']) for r in refs if r['child'] in IDS}
    assert actual==expected,actual
    assert {(r['parent'],r['frame'],r['label']) for r in refs if r['child']==614}=={(735,7,'12season')}
    vector.POLYGONS=polygons();changed=[];parts=[];checks=[]
    for k,b,raw in ts:
        cid=struct.unpack_from('<H',b)[0] if k in (2,22,32,39,83) else None
        if cid in IDS:
            assert k in (2,22,32,83),(cid,k)
            oldbounds=bounds(b);b=vector.shape(cid,oldbounds);raw=tag(2,b)
            checks.append(dict(id=cid,**check_vectors(b)));changed.append(cid)
        parts.append(raw)
    assert set(changed)==IDS
    updated=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',updated,4,len(updated))
    vector.replace_ui_member(source,out/'Label.big',member,b'CFX'+updated[3:8]+zlib.compress(updated[8:],9),bigdir)
    _,after,at=plain(out/'Label.big');newtags=list(tags(after,at));assert len(ts)==len(newtags)
    diffs=[]
    for old,new in zip(ts,newtags):
        if old[2]!=new[2]:
            cid=struct.unpack_from('<H',old[1])[0];assert cid in IDS;diffs.append(cid)
        else:assert old==new
    assert set(diffs)==IDS and references(newtags)==refs
    from PIL import Image,ImageDraw
    im=Image.new('RGB',(600,300),(35,39,48));draw=ImageDraw.Draw(im)
    colors={1:(225,182,78),2:(25,32,47),3:(255,239,187)}
    for size,left in [(240,20),(48,300),(24,390),(18,465)]:
        for fill,points in polygons():draw.polygon([(left+x*size/1000,20+y*size/1000) for x,y in points],fill=colors[fill])
        draw.text((left,270),str(size)+'px',fill='white')
    im.save(out/'badge-preview.png')
    proof=dict(status='SEASON12_ICON_RESOURCE_PASS',changed_characters=changed,vector_checks=checks,
               references=[r for r in refs if r['child'] in IDS|{614}],all_other_swf_tags_exact=True,
               season91_XI_unchanged=True,ABC_unchanged=True,native_verified=False,source_sha256=tx.sha(source),output_sha256=tx.sha(out/'Label.big'))
    tx.atomic_json(out/'resource-proof.json',proof)
    prepare(out)

def prepare(out):
    source=C/'data/ui/components/Label.big';proof=tx.read(out/'resource-proof.json');assert tx.sha(source)==proof['source_sha256']
    play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
    rel='patches/'+names[0].decode();parent=load(S/rel,'icons_parent');check=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
    template=(ROOT/'season_name_preflight.py').read_text('utf-8')
    for a,b in [('season-name','season-icons'),('season_name','season_icons'),('SEASON_NAME','SEASON_ICONS'),('season name','season icons')]:template=template.replace(a,b)
    template=template.replace("('client','data/ui/libs/module.big')","('client','data/ui/components/label.big'),('server','patches/label.big')")
    template=template.replace('INSTALLED_SEASON_ICONS_CALLBACK','INSTALLED_SEASON_ICONS')
    template=template.replace('season icons callback revision','season icons resource revision').replace('Season name receipt mismatch','Season icons receipt mismatch')
    (out/'season_icons_preflight.py').write_text(template,'utf-8')
    (out/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\season_icons_preflight.py'))
    rows=[]
    doc=S/'docs/工程经验与修改边界.txt'
    note=('\r\n\r\nFO3-001 续：12号自定义赛季图标（2026-11-06，season-icons-v1）\r\n'
          '确认：正式注册表12=FC传奇精选·ICON，91=世界最佳11人。卡卡12138449/瓦拉内12201535是独立12号卡，不能将其冒充91号WB。Label大图sprite144第7帧12season指shape45，小图sprite735第7帧指sprite614，其3状态依次指shape609/611/613；仍为旧12赛季美术。\r\n'
          '正式修复：仅四个专用shape替换为金色ICON矢量标识，保留各自原RECT、sprite614三状态时间轴、全部其它SWF tag/ABC及所有非目标BIG成员压缩字节。server patches/Label.big与client data/ui/components/Label.big同步，WB91/XI、时刻84/IM、怀旧19/OG及字体金额均保持。未修改数据库、SPID或真实资产；服务未重启。\r\n'
          f'验证：四个shape闭合路径解析、全部引用定位与非目标tag逐字节比较PASS；完整当前父层{check["files"]} guards先检查再组合。游戏运行时安装在锁与首写之前拒绝，用户退出后才允许安装。等待期间choice-search成为新顶层，旧父层预检按预期拒绝，随后按实际play最新父层重新组合保留其修改，无正式覆盖。初次构建因正式venv无PIL终止且无正式写入，改用现有anaconda/PIL完成预览；REA不支持BIg4，实际字节由现有bigdir/SWF解析工具读取。native页面/比赛仍待验证，不由资源检查替代。\r\n'
          '证据D:/fifaol3/season12-display/icons-work2/resource-proof.json、badge-preview.png；安装回执D:/fifaol3/season12-display/icons-installed-handback.json，备份见该回执。复验：正式.venv/Scripts/python.exe -B patches/season_icons_preflight.py；资源预检python -B D:/fifaol3/season12-display/fix_icons.py preview --work D:/fifaol3/season12-display/icons-work2（仅安装前基线）。\r\n')
    (out/'engineering-notes.txt').write_bytes(doc.read_bytes()+note.encode('utf-8'))
    for root,r,f in [('client','data/ui/components/Label.big','Label.big'),('server','patches/Label.big','Label.big'),('server',SELF,'season_icons_preflight.py'),('server','play-local.bat','play-local.bat')]:
        dest=(S if root=='server' else C)/r
        if f=='Label.big':assert tx.sha(dest)==proof['source_sha256'],'Label copies differ; review required'
        rows.append(dict(root=root,relative=r,source=str(out/f),parent_sha256=tx.digest(dest),sha256=tx.sha(out/f)))
    guards={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']}
    for row in rows:guards[row['root'],row['relative'].casefold()]={k:row[k] for k in ('root','relative','sha256')}
    parents={r:tx.sha(S/r) for r in (rel,parent.MANIFEST,parent.RECEIPT)}
    receipt=tx.read(S/parent.RECEIPT)
    comp.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
    comp.setdefault('ancestry',[]).append(dict(preflight=rel,files=parents))
    comp['guards']=list(guards.values())
    m=dict(schema=1,revision='season-icons-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'),client=str(C),guards=list(guards.values()),composition=comp,
           parent_preflight=rel,parent_files=parents,files=rows,state_shop_replaced=False,scope='Season12 ICON badge, four dedicated shapes, all other tags unchanged')
    tx.atomic_json(out/'manifest.json',m);tx.atomic_json(out/'prepare.json',dict(status='PREPARED',parent_preflight=check,manifest_sha256=tx.sha(out/'manifest.json')))
    print(json.dumps(tx.read(out/'prepare.json')))

def gameclosed():
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,'Game is running. Close it normally before installing icons.'

def preview(out):
    m=tx.read(out/'manifest.json');proof=tx.read(out/'resource-proof.json')
    assert proof['status']=='SEASON12_ICON_RESOURCE_PASS'
    for r,h in m['parent_files'].items():assert tx.sha(S/r)==h,'Parent changed: '+r
    parent=load(S/m['parent_preflight'],'icons_preview_parent');p=parent.preflight(S,C)
    for row in m['files']:
        assert tx.sha(row['source'])==row['sha256']
        assert tx.digest(tx.target(dict(server=S,client=C),row))==row['parent_sha256'],'Target changed: '+row['relative']
    return m,p

def install(out):
    gameclosed();m,p=preview(out);roots=dict(server=S,client=C)
    coordination=tx.read(ROOT.parent/'coordination-current.json')
    assert not coordination.get('queue') and not coordination.get('current_unhanded_writers') and not coordination.get('next_formal_writer'),'Another formal writer is scheduled'
    locks=[]
    try:
        for n in ('.shop-release.lock','.fo3-publish.lock'):
            lock=S/n;fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,json.dumps(dict(task='season-icons',pid=os.getpid())).encode());os.close(fd);locks.append(lock)
        gameclosed();preview(out)
        backup=S/'backups'/m['revision'];backup.mkdir()
        audit={n:tx.sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
        for n in audit:shutil.copyfile(S/'gamedata'/n,backup/('audit-'+n))
        receipt=dict(status='INSTALLED_SEASON_ICONS',revision=m['revision'],manifest_sha256=tx.sha(out/'manifest.json'),backup=str(backup),state_shop_replaced=False,native_status='PENDING')
        tx.atomic_json(backup/'receipt.json',receipt)
        entries=list(m['files'])+[
            dict(root='server',relative=MANIFEST,source=str(out/'manifest.json'),parent_sha256=None,sha256=tx.sha(out/'manifest.json')),
            dict(root='server',relative=RECEIPT,source=str(backup/'receipt.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt.json'))]
        def validate():gameclosed();preview(out)
        transaction=tx.commit_transaction(roots,entries,backup,validate)
        try:
            check=load(S/SELF,'icons_installed').preflight(S,C)
            transaction.update(status='installed',preflight=check,state_shop_before=audit,state_shop_after={n:tx.sha(S/'gamedata'/n) for n in audit},state_shop_written=False,service_restart=False)
            tx.atomic_json(backup/'transaction.json',transaction)
        except BaseException:
            tx.restore_completed(roots,transaction,backup);raise
        result=dict(status='INSTALLED_SEASON_ICONS_NATIVE_PENDING',preflight=check,backup=str(backup),service_restart=False,state_shop_written=False,
                    actual_entry=str(S/'play-local.bat'),preflight_path=str(S/SELF),triple_hashes={str(S/r):tx.sha(S/r) for r in (SELF,MANIFEST,RECEIPT)})
        tx.atomic_json(ROOT/'icons-installed-handback.json',result)
        coordination=tx.read(ROOT.parent/'coordination-current.json')
        coordination.update(last_independent_install=dict(task='season-icons',at=datetime.datetime.now().astimezone().isoformat(),preflight=str(S/SELF),handoff=str(ROOT/'icons-installed-handback.json'),completed=True,locks_released=False,root_goal_resumed=False))
        tx.atomic_json(ROOT.parent/'coordination-current.json',coordination)
        tx.atomic_json(ROOT.parent/'root-current-top.json',dict(status='OBSERVED_INDEPENDENT_SEASON_ICONS_INSTALL',observed_at=datetime.datetime.now().astimezone().isoformat(),
            top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),files={str(tx.target(roots,r)):tx.sha(tx.target(roots,r)) for r in entries},
            function_signatures=dict(sha='p',preflight='server=None, client=None',compose_manifest='server=None, client=None'),composition_available=True,
            receipt_record=receipt,physical_preflight_run_by_this_observer=True,GUI_status='Resource checks PASS; native UI not tested; root goal remains paused.',state_shop_written=False))
        print(json.dumps(result))
    finally:
        for lock in reversed(locks):lock.unlink()
    coordination=tx.read(ROOT.parent/'coordination-current.json')
    if coordination.get('last_independent_install',{}).get('task')=='season-icons':
        coordination['last_independent_install']['locks_released']=True
        tx.atomic_json(ROOT.parent/'coordination-current.json',coordination)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','preview','install']);p.add_argument('--work',required=True,type=Path);a=p.parse_args();out=a.work.resolve();assert out.is_relative_to(ROOT)
    if a.action=='build':build(out)
    elif a.action=='preview':print(json.dumps(preview(out)[1]))
    else:install(out)
