"""Bounded RX3 mesh validation and explicit FIFA14-to-Impact rig conversion.

Formats follow the pinned FIFALibrary22 structures audited with this project.
No assembly is loaded or executed; geometry/material bytes are retained.
"""
import collections,hashlib,json,math,pathlib,struct,zlib
SKIN=0xdf9aec1e;VERTEX=0x587aa1;INDEX=0x5878f4;FORMAT=0xc28193f0;REMAP=0xf3861a2
FORMATS={'3f32':('3f',12),'4f16':('4e',8),'2f16':('2e',4),'2f32':('2f',8),'4u8':('4B',4),'4u8n':('4B',4),'4u16':('4H',8),'4u16n':('4H',8),'3s10n':('I',4)}
def sha(b):return hashlib.sha256(b).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def unwrap(data):
    if data[:8]!=b'chunkzip':return data
    def word(p):return struct.unpack_from('>I',data,p)[0]
    version=word(8);old=version<=2
    full,chunk,pos=(word(12),word(16),40) if old else (version,word(12),16)
    require(0<full<100*1024*1024 and chunk>0,'Invalid chunkzip bounds');out=bytearray()
    while len(out)<full:
        if old:
            pos=(pos+7)//8*8
            while pos%16!=8:pos+=8
        size=word(pos);pos+=4;flag=word(pos) if old else None
        if old:pos+=4
        payload=data[pos:pos+size];require(len(payload)==size,'Truncated chunkzip');wanted=min(chunk,full-len(out))
        if flag==4:plain=payload
        else:
            for bits in [-15,15,31]:
                try:plain=zlib.decompress(payload,bits);break
                except zlib.error:continue
            else:raise ValueError('Unsupported chunkzip codec')
        require(len(plain)==wanted,'Invalid inflated chunk length');out.extend(plain);pos+=size
    return bytes(out)
def sections(d):
    require(d[:4]==b'RX3l' and len(d)>=16,'Not little endian RX3')
    version,size,count=struct.unpack_from('<III',d,4);require(version==4 and size==len(d) and 0<count<1000,'Invalid RX3 header')
    groups=collections.defaultdict(list);ranges=[]
    for i in range(count):
        kind,off,size,_=struct.unpack_from('<IIII',d,16+i*16)
        require(16+count*16<=off and off+size<=len(d),'RX3 section out of bounds')
        groups[kind].append((i,off,size));ranges.append((off,off+size))
    require(all(a[1]<=b[0] for a,b in zip(sorted(ranges),sorted(ranges)[1:])),'Overlapping RX3 sections')
    return groups
def vertex_fields(d,f,v):
    _,fo,fs=f;_,vo,vs=v;total,length=struct.unpack_from('<II',d,fo);require(total==fs and 16+length<=fs,'Invalid vertex format')
    text=d[fo+16:fo+16+length].rstrip(b'\0').decode('ascii');fields={}
    for field in text.split():
        parts=field.split(':');require(len(parts)>=3 and parts[-1] in FORMATS,'Unsupported vertex field')
        fields[parts[0]]=(int(parts[1],16),parts[-1])
    total,n,stride=struct.unpack_from('<III',d,vo);require(total==vs and 16+n*stride<=vs and d[vo+12] in [0,1],'Invalid vertex buffer')
    require(all(off+FORMATS[typ][1]<=stride for off,typ in fields.values()),'Vertex field exceeds stride')
    return fields,n,stride,'<' if d[vo+12] else '>'
def validate(raw,target_bones=252):
    d=unwrap(raw);s=sections(d);rows=[]
    if not s[VERTEX]:return dict(meshes=[],rx3_bytes=len(d),sha256=sha(raw))
    require(len({len(s[k]) for k in [VERTEX,INDEX,FORMAT,SKIN,REMAP]})==1,'Per-mesh section count mismatch')
    for mi,(v,f,ib,skin,remap) in enumerate(zip(s[VERTEX],s[FORMAT],s[INDEX],s[SKIN],s[REMAP])):
        fields,n,stride,endian=vertex_fields(d,f,v);_,vo,vs=v;_,so,ss=skin;_,ro,rs=remap;_,io,isize=ib
        total,nb=struct.unpack_from('<II',d,so);require(total==ss and 16+nb*64<=ss,'Invalid skin matrices')
        if target_bones is not None:require(nb==target_bones,f'Expected {target_bones} bones, got {nb}')
        require(all(math.isfinite(x) for b in range(nb) for x in struct.unpack_from('<15f',d,so+16+b*64)),'Nonfinite skin matrix')
        require(struct.unpack_from('<I',d,ro)[0]==rs and rs==528,'Unsupported bone remap')
        used=d[ro+4];palette=list(d[ro+272:ro+272+used]);require(not palette or palette[0]!=1,'High-byte bone palettes unsupported')
        weighted=set()
        for j in range(n):
            at=vo+16+j*stride
            for name,(off,typ) in fields.items():
                if name.startswith(('p','t')):
                    fmt,_=FORMATS[typ];require(all(math.isfinite(x) for x in struct.unpack_from(endian+fmt,d,at+off)),'Nonfinite geometry or UV')
            require(fields.get('i0',(0,None))[1]=='4u8' and fields.get('w0',(0,None))[1]=='4u8n','Unsupported blend encoding')
            ids=d[at+fields['i0'][0]:at+fields['i0'][0]+4];weights=d[at+fields['w0'][0]:at+fields['w0'][0]+4]
            require(abs(sum(weights)-255)<=1,'Invalid vertex blend weight sum')
            for b,w in zip(ids,weights):
                if w:require(b<nb,'Bone index outside skin');weighted.add(b)
        require(weighted<=set(palette),'Weighted bone absent from remap')
        for local,b in enumerate(palette):require(d[ro+16+b]==local,'Remap inverse mismatch')
        total,ni=struct.unpack_from('<II',d,io);istride=d[io+8];require(total==isize and istride in [2,4] and 16+ni*istride<=isize,'Invalid index buffer')
        indices=struct.unpack_from('<'+str(ni)+('H' if istride==2 else 'I'),d,io+16);require(all(x<n for x in indices),'Triangle index out of bounds')
        rows.append(dict(mesh=mi,vertices=n,indices=ni,skin_bones=nb,weighted_bones=sorted(weighted),geometry_index_sha256=sha(d[io+16:io+16+ni*istride])))
    return dict(meshes=rows,rx3_bytes=len(d),sha256=sha(raw))
def retarget(raw,native_template,rig):
    d=unwrap(raw);native=unwrap(native_template);s=sections(d);ns=sections(native);out=bytearray(d);allowed=set();proof=[]
    require(rig['source_bone_count']==255 and rig['target_bone_count']==252,'Unsupported rig conversion')
    def change(at,b):out[at:at+len(b)]=b;allowed.update(range(at,at+len(b)))
    mapping={int(k):int(v) for k,v in rig['index_mapping'].items()}
    for mi,(v,f,skin,remap) in enumerate(zip(s[VERTEX],s[FORMAT],s[SKIN],s[REMAP])):
        fields,n,stride,endian=vertex_fields(d,f,v);_,vo,vs=v;si,so,ss=skin;_,ro,rs=remap
        require(endian=='<' and fields['i0'][1]=='4u8' and fields['w0'][1]=='4u8n','Unsupported retarget vertex encoding')
        io=fields['i0'][0];wo=fields['w0'][0];used=set();bones={}
        for j in range(n):
            at=vo+16+j*stride;ids=d[at+io:at+io+4];weights=d[at+wo:at+wo+4];merged={}
            for b,w in zip(ids,weights):
                if w:
                    require(b in mapping,'Unknown weighted source bone '+str(b));dest=mapping[b];merged[dest]=merged.get(dest,0)+w;bones[b]=dest
            require(max(merged.values(),default=0)<=255,'Merged weights overflow');pairs=list(merged.items());used.update(merged)
            newids=bytes([b for b,w in pairs]+[0]*(4-len(pairs)));newweights=bytes([w for b,w in pairs]+[0]*(4-len(pairs)))
            require(sum(weights)==sum(newweights),'Blend sum changed');change(at+io,newids);change(at+wo,newweights)
            require(d[at:at+io]==out[at:at+io] and all(d[at+k]==out[at+k] for k in range(stride) if k not in range(io,io+4) and k not in range(wo,wo+4)),'Geometry or UV changed')
        require(rs==528 and 1 not in used and len(used)<256,'Unsupported palette')
        palette=sorted(used);body=bytearray(rs);struct.pack_into('<II',body,0,rs,len(palette))
        for local,b in enumerate(palette):body[16+b]=local
        body[272:272+len(palette)]=bytes(palette);change(ro,body)
        _,nso,nss=ns[SKIN][min(mi,len(ns[SKIN])-1)]
        require(struct.unpack_from('<II',d,so)==(16336,255) and ss==16336,'Source skin is not declared FIFA14 255')
        require(struct.unpack_from('<II',native,nso)==(16144,252) and nss==16144,'Destination is not native 252')
        change(so,native[nso:nso+nss]+bytes(ss-nss));change(16+si*16+8,struct.pack('<I',nss))
        proof.append(dict(mesh=mi,weighted_mapping=bones,target_skin_sha256=sha(native[nso:nso+nss])))
    result=bytes(out);require(len(result)==len(d),'RX3 layout length changed')
    require(all(i in allowed for i,(a,b) in enumerate(zip(d,result)) if a!=b),'Nonbinding byte changed')
    checked=validate(result)
    return result,dict(before_sha256=sha(raw),after_sha256=sha(result),geometry_materials_indices_preserved=True,bindings=proof,validation=checked)
