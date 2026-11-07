from pathlib import Path
import hashlib,json,struct,sys,zlib
sys.dont_write_bytecode=True
T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
from avm_patch import ABC,Code,R,instructions,u30,dis
import bigdir
ns={};exec((T.parents[1]/'work/grade_render_audit/build_display_fix.py').read_text('utf8').split("source=OLD/'TileList.big'")[0],ns)
tags=ns['tags'];tag=ns['tag'];pack_archive=ns['pack_archive']
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
NAMES=('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snapshot():
    report={}
    for name in NAMES:
        source=C/'data/ui'/(name+'.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
        gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
        (W/(name+'-baseline.big')).write_bytes(source.read_bytes());(W/(name+'-baseline.swf')).write_bytes(swf)
        report[name]=dict(source=str(source),source_sha256=sha(source),server_source_sha256=sha(S/'patches'/(name+'.big')),member=member)
        assert report[name]['source_sha256']==report[name]['server_source_sha256']
    (W/'baseline.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def inspect():
    for name,cname in zip(NAMES,('EnhanceControlPanel','TeamManagementPlayerEnhancingPopupScreen')):
        swf=(W/(name+'-baseline.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4
        for kind,body,raw in tags(swf,start,len(swf)):
            if kind!=82:continue
            head=body.index(b'\0',4)+1;a=ABC(body[head:]);A=a.A
            if not any(c[0]==cname for c in A['cls']) or ('_preview' if name==NAMES[0] else 'boostInfoPanel') not in A['mn']:continue
            (W/(name+'-before.abc')).write_bytes(body[head:])
            out=[]
            for row in A['cls']:
                if row[0]!=cname:continue
                out.append(repr(row))
                for k,n,mid in row[3]+row[5]:
                    if k in ('method','get','set') and mid in A['body']:
                        out.append('METHOD '+str(mid)+' '+n+'\n'+'\n'.join(dis(A,A['body'][mid])))
            for mid in ((34,37,45) if name==NAMES[0] else (32,63)):
                out.append('ANONYMOUS '+str(mid)+'\n'+'\n'.join(dis(A,A['body'][mid])))
            (W/(name+'-analysis.txt')).write_text('\n\n'.join(out),encoding='utf8')
if __name__=='__main__':snapshot();inspect();print('Bound and decoded current official enhancement UI artifacts')
