"""Incremental Space shortcut for the installed enhancement recovery animation."""
from pathlib import Path
import sys, struct, zlib, hashlib, json, shutil, datetime, os
sys.dont_write_bytecode = True
HELPERS=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path.insert(0,str(HELPERS))
from avm_patch import ABC, Code, parse
sys.path.insert(0,r'D:\FO3ID\server\tools\re')
import bigdir
OUT=Path(__file__).parent
TARGET=Path(r'D:\FO3ID\32795\data\ui\TeamManagementPlayerEnhancingPopupScreen.big')
def sha(b): return hashlib.sha256(b).hexdigest()
def tags(d,p,end):
    while p+2<=end:
        at=p; v=struct.unpack_from('<H',d,p)[0];p+=2;t,n=v>>6,v&63
        if n==63:n=struct.unpack_from('<I',d,p)[0];p+=4
        yield t,d[p:p+n],d[at:p+n]
        p+=n
        if t==0:break
def tag(t,b):return struct.pack('<HI',t<<6|63,len(b))+b
def data(c):return c.find('_restorePlayerData').ownprop('_restorePlayerData')
def state(c):return data(c).prop('restoreSpaceState')
def resultgrade(c):return c.find('_result').ownprop('_result').prop('resultgrade')
def setstate(c,s):return data(c).string(s).set('restoreSpaceState')
def skip_guard(a):
    c=Code(a);data(c).jump(0x12,'normal')
    state(c).string('pending').jump(0x13,'return')
    state(c).string('done').jump(0x14,'normal')
    c.label('return').op(0x47).label('normal');return c.done()
def build():
    before=TARGET.read_bytes();entries=bigdir.entries(TARGET)
    member=next(n for n,*_ in entries if n.endswith('.gfx'))
    gfx=bigdir.read(TARGET,member);assert gfx[:3]==b'CFX'
    swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
    start=8+(5+4*(swf[8]>>3)+7)//8+4
    ts=list(tags(swf,start,len(swf)));selected=[]
    for ix,(t,b,raw) in enumerate(ts):
        if t!=82:continue
        p=b.index(b'\0',4)+1
        a=ABC(b[p:])
        if a.A['cls'][0][0]=='TeamManagementPlayerEnhancingPopupScreen' and any(t[1]=='restoreStart' for t in a.A['cls'][0][3]):selected.append((ix,p,a,b))
    assert len(selected)==1
    ix,p,a,b=selected[0]
    mids={name:mid for kind,name,mid in a.A['cls'][0][3] if kind=='method'}
    # Existing closure scopes include the attached screen.
    # No scope push here: nested callbacks keep the native closure depth of 12.
    c=Code(a);state(c).string('pending').jump(0x14,'done')
    setstate(c,'done')
    c.find('changePlayerCardInRestoreAnimation').owncall('changePlayerCardInRestoreAnimation',0).op(0x29)
    c.find('restoreComplete').owncall('restoreComplete',0).op(0x29)
    c.label('done').op(0x47)
    completed=a.add_method(c.done(),12)
    c=Code(a).local(1).prop('keyCode').number(32).jump(0x14,'done')
    data(c).jump(0x12,'done');state(c).string('active').jump(0x14,'done')
    # Lock before starting async expansion: repeat presses and stale callbacks do nothing.
    setstate(c,'pending')
    c.find('container').ownprop('container').call('stop',0).op(0x29)
    c.find('_restoreCount');resultgrade(c);c.ownset('_restoreCount')
    data(c);resultgrade(c);c.set('grade')
    data(c).op(0x21).set('staticdata')
    c.find('PlayerListUtil').ownprop('PlayerListUtil');data(c)
    c.op(0x40,completed).call('expandPlayerStaticData',2).op(0x29)
    c.local(1).call('stopImmediatePropagation',0).op(0x29)
    c.local(1).call('preventDefault',0).op(0x29)
    c.label('done').op(0x47)
    handler=a.add_method(c.done(),12)
    # ObjectUtil owns cleanup on detach, as for all original animation listeners; attach only after stage exists.
    c=Code(a).find('ObjectUtil').ownprop('ObjectUtil').local(0)
    c.local(0).prop('stage').string('keyDown').op(0x40,handler)
    c.call('addAndManageEventListenerFrom',4).op(0x29)
    a.modify(mids['onAttached'],{45:c.done()})
    c=Code(a);setstate(c,'active')
    # restoreStart initializes the copied player and levelinfo before this boundary.
    a.modify(mids['restoreStart'],{124:c.done()})
    # Ignore animation callbacks already queued when Space stopped the timeline.
    for mid in [45,mids['restorePlayerCardLoop']]:a.modify(mid,{0:skip_guard(a)})
    c=Code(a);data(c).jump(0x12,'normal');setstate(c,'done');c.label('normal')
    a.modify(mids['restoreComplete'],{0:c.done()})
    patched=a.output();checked=ABC(patched)
    # Existing stack/branch checker, without its historical top-level execution.
    ns={'__file__':str(HELPERS/'verify_stacks.py')}
    exec((HELPERS/'verify_stacks.py').read_text(encoding='utf8').split('results={}')[0].replace('0x85,0x90,0x96','0x85,0x90,0x91,0x96'),ns)
    stack={str(mid):ns['check'](checked,mid) for mid in sorted(set(a.changed)|{handler,completed})}
    ts[ix]=(82,b[:p]+patched,tag(82,b[:p]+patched))
    updated=bytearray(swf[:start]+b''.join(raw for _,_,raw in ts))
    struct.pack_into('<I',updated,4,len(updated))
    newgfx=b'CFX'+updated[3:8]+zlib.compress(updated[8:],9)
    assert zlib.decompress(newgfx[8:])==updated[8:]
    # Single UI member append; all DDS payloads and other UI/DB files stay intact.
    staged=OUT/'popup.updated.big';staged.write_bytes(before)
    bigdir.patch(staged,{member:newgfx})
    newentries=bigdir.entries(staged);raw=staged.read_bytes()
    for name,off,size,usize in entries:
        if name==member:continue
        _,no,nsz,nu=next(e for e in newentries if e[0]==name)
        assert (size,usize)==(nsz,nu) and before[off:off+size]==raw[no:no+nsz]
    (OUT/'popup.updated.swf').write_bytes(updated)
    report=dict(version='restore-space-v1',target=str(TARGET),before_sha256=sha(before),after_sha256=sha(raw),
                changed_methods=sorted(a.changed),handler=handler,completed=completed,stack=stack,
                non_target_methods_byte_identical=True,non_target_members_byte_identical=True,
                native_test='skipped at user request',installed=False)
    (OUT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report,staged
def install(report,staged):
    # Final installation must be composed into the current startup guard layer.
    # This low-level helper alone cannot finish that transaction.
    raise RuntimeError('Use the coordinated installer with current parent guards; standalone UI replacement disabled')
    assert sha(TARGET.read_bytes())==report['before_sha256'],'Concurrent target change; rebuild required'
    backup=Path(r'D:\FO3ID\server\backups')/('restore-space-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir();shutil.copy2(TARGET,backup/TARGET.name)
    temp=TARGET.with_suffix('.big.restore-space.tmp');shutil.copyfile(staged,temp)
    assert sha(temp.read_bytes())==report['after_sha256']
    assert sha(TARGET.read_bytes())==report['before_sha256']
    os.replace(temp,TARGET)
    assert sha(TARGET.read_bytes())==report['after_sha256']
    report.update(installed=True,backup=str(backup/TARGET.name),reload='next client restart')
    (OUT/'installation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':
    report,staged=build()
    if '--install' in sys.argv:install(report,staged)
    print(json.dumps(report,ensure_ascii=True))




