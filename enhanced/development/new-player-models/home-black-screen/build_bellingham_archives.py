"""Prepare byte-local archive deltas; no formal files are written."""
from pathlib import Path
import hashlib,json,shutil,sys,zlib
sys.path.insert(0,'D:/FO3ID/server/tools/re')
import bigdir
R=Path(__file__).resolve().parent;O=R/'bellingham-impact'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    report=json.loads((O/'report.json').read_text('utf8'));groups={}
    for row in report['files']:groups.setdefault(row['archive'],[]).append(row)
    archives=[]
    for archive,rows in groups.items():
        p=Path(archive);before=sha(p);target=O/p.name;shutil.copyfile(p,target);entries={n:(off,size,usize) for n,off,size,usize in bigdir.entries(p)};ranges=[]
        with target.open('r+b') as f:
            for row in rows:
                off,size,usize=entries[row['member']];assert usize==0 and size==row['bytes']
                f.seek(off);assert hashlib.sha256(f.read(size)).hexdigest()==row['before_sha256']
                payload=Path(row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['after_sha256']
                f.seek(off);f.write(payload);ranges.append((off,off+size))
        assert bigdir.table(p)==bigdir.table(target) and p.stat().st_size==target.stat().st_size
        # Every byte outside the three explicit RX3 member extents must match.
        with p.open('rb') as a,target.open('rb') as b:
            start=0
            for left,right in sorted(ranges)+[(p.stat().st_size,p.stat().st_size)]:
                a.seek(start);b.seek(start);remaining=left-start
                while remaining:
                    n=min(8*1024*1024,remaining);assert a.read(n)==b.read(n);remaining-=n
                start=right
        assert sha(p)==before,'Source changed during build'
        archives.append(dict(target=str(p),payload=str(target),before_sha256=before,after_sha256=sha(target),modified_members=[r['member'] for r in rows],directory_and_other_members_unchanged=True))
    backup=Path('D:/FO3ID/server/backups/names-route-20261107-001134/0-Module.big')
    assert sha(backup)=='1b9519f979ae58ac11a0d5442b726be1e36919b3f8018a1a313c05c7ba0a8016'
    module=Path('D:/FO3ID/32795/data/ui/libs/Module.big')
    assert sha(module)=='8a8f3a97ffeaf5045e97ba28fb81e637b831c655b2718acbc73dbd8034cee097'
    # Return only this task's ineffective UI edits to its exact prior bytes.
    current=bigdir.entries(module);original=bigdir.entries(backup)
    assert [r[0] for r in current]==[r[0] for r in original]
    for name,*_ in original:
        if not name.endswith('.gfx'):assert bigdir.read(module,name)==bigdir.read(backup,name)
        else:
            g=bigdir.read(backup,name);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:]);assert swf==(R/'current-Module.swf').read_bytes()
    archives.append(dict(target=str(module),payload=str(backup),before_sha256=sha(module),after_sha256=sha(backup),scope='Remove only this task UI rewrites; restore exact pre-task Module'))
    out=dict(status='READY_FOR_CLIENT_CLOSED_INSTALL',files=archives,assets_preserved=True,state_shop_written=False,native_verified=False)
    (O/'archive-build.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
if __name__=='__main__':main()
