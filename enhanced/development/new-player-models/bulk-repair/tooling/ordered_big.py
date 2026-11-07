"""Rebuild an archive in directory order and preserve all non-target raw payloads."""
import hashlib,pathlib,struct
import bigdir
def digest(p):
    with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def rebuild(source,target,replacements):
    source,target=pathlib.Path(source),pathlib.Path(target)
    if source.resolve()==target.resolve():raise ValueError('Build to a separate artifact, then use the release transaction')
    baseline=digest(source);table=bytearray(bigdir.table(source));records=list(bigdir._walk(table));seen=set();unchanged=0
    known={r[1] for r in records};additions=sorted(set(replacements)-known)
    if additions:
        rows=[(n,off,size,usize) for _,n,off,size,usize in records]+[(n,0,len(replacements[n][0]),replacements[n][1]) for n in additions]
        length=max(len(table),(17+sum(17+len(n.encode('latin1')) for n,_,_,_ in rows)+127)&~127)
        header=bytearray(length);header[:17]=table[:17];struct.pack_into('>II',header,8,bigdir.enc(len(rows)),bigdir.enc(length));records=[];pos=17
        for n,off,size,usize in rows:
            struct.pack_into('>IIII',header,pos,bigdir.enc(off),bigdir.enc(size),bigdir.enc(usize),bigdir.enc(len(n.encode('latin1'))));records.append((pos,n,off,size,usize));pos+=17+len(n.encode('latin1'))
        table=header
    with source.open('rb') as inp,target.open('wb') as out:
        out.write(table)
        for pos,name,off,size,usize in records:
            newoff=(out.tell()+127)&~127;out.write(bytes(newoff-out.tell()))
            if name in replacements:
                payload,unpacked=replacements[name];seen.add(name);newsize=len(payload);out.write(payload)
            else:
                inp.seek(off);remaining=size;newsize=size;unpacked=usize
                while remaining:
                    block=inp.read(min(8*1024*1024,remaining))
                    if not block:raise ValueError('Truncated archive')
                    out.write(block);remaining-=len(block)
                unchanged+=1
            struct.pack_into('>III',table,pos,bigdir.enc(newoff),bigdir.enc(newsize),bigdir.enc(unpacked));key=newsize&255
            for j,ch in enumerate(name.encode('latin1')):
                b=ch^key;table[pos+16+j]=((b<<4)|(b>>4))&255;key=((b or newsize&255)-0x66)&255
        end=out.tell();struct.pack_into('<I',table,4,end);out.seek(0);out.write(table)
    if seen!=set(replacements):raise ValueError('Replacement member not in archive')
    actual=bigdir.entries(target)
    if [r[1] for r in records]!=[r[0] for r in actual] or any(a[1]+a[2]>b[1] for a,b in zip(actual,actual[1:])):raise ValueError('Archive order/bounds failed')
    with source.open('rb') as a,target.open('rb') as b:
        for old,new in zip(records,actual):
            _,name,off,size,usize=old;_,noff,nsize,nusize=new
            if name in replacements:continue
            if (size,usize)!=(nsize,nusize):raise ValueError('Untargeted member metadata changed')
            a.seek(off);b.seek(noff);left=size
            while left:
                n=min(left,8*1024*1024)
                if a.read(n)!=b.read(n):raise ValueError('Untargeted member bytes changed: '+name)
                left-=n
    if digest(source)!=baseline:raise ValueError('Source archive changed during build')
    return dict(before_sha256=baseline,after_sha256=digest(target),target=str(source),payload=str(target),unchanged_members=unchanged,replaced_members=sorted(replacements))
