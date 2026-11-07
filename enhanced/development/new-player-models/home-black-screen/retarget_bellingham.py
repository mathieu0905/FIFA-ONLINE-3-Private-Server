"""Retarget imported face weights to the shipped Impact Engine skeleton.

Static conversion only. Never modifies production archives or executes vendor code.
Preserves every vertex byte other than blend indices/weights, all index buffers,
materials, textures, section offsets and the full RX3 length.
"""
import ast,collections,hashlib,json,pathlib,struct,sys,zlib
R=pathlib.Path(__file__).resolve().parent
A=R.parent/'audit'
audit=json.loads((A/'audit.json').read_text('utf8'))
sys.path.insert(0,'D:/FO3ID/server/tools/re')
import bigdir
scope={'struct':struct,'zlib':zlib,'hashlib':hashlib}
for node in ast.parse(pathlib.Path(audit['decoder_source']).read_text('utf8')).body:
    if isinstance(node,ast.FunctionDef) and node.name=='unpack':exec(compile(ast.Module(body=[node],type_ignores=[]),'unpack','exec'),scope)
def sha(b):return hashlib.sha256(b).hexdigest()
def skeleton(name):
    p=R/'converter-research/data/FIFA Converter/Skeletons'/name
    return {int(row.split(',')[0]):row.split(',')[1] for row in p.read_text('utf-8-sig').splitlines() if row.strip()}
source=skeleton('Skeleton_FIFA14_Switch.txt');target=skeleton('Skeleton_ImpactEngine.txt')
aliases=json.loads((R/'converter-research/impact-bone-name-map.json').read_text('utf8'))['mapping']
byname={v:k for k,v in target.items()}
def mapped(i):
    name=source[i]
    result=byname.get(name,aliases.get(name))
    assert result is not None and result in target,('unmapped',i,name)
    return result
def sections(data):
    assert data[:4]==b'RX3l' and struct.unpack_from('<II',data,4)==(4,len(data))
    result=collections.defaultdict(list);ranges=[]
    for i in range(struct.unpack_from('<I',data,12)[0]):
        kind,off,size,_=struct.unpack_from('<IIII',data,16+i*16)
        assert 16+16*struct.unpack_from('<I',data,12)[0]<=off and off+size<=len(data)
        ranges.append((off,off+size));result[kind].append((i,off,size))
    for left,right in zip(sorted(ranges),sorted(ranges)[1:]):assert left[1]<=right[0]
    return result
OUT=R/'bellingham-impact';OUT.mkdir(exist_ok=True)
reports=[]
player=next(p for p in audit['players'] if p['playerid']==252371)
for f in player['files']:
    if '/textures/' in f['member'] or 'textures.rx3' in f['member']:continue
    if not any('/'+k+'/' in f['member'] for k in ['heads','hair','hairlod']):continue
    raw=pathlib.Path(f['source_path']).read_bytes();assert sha(raw)==f['source_sha256']
    original=bigdir.read(f['installed_archive'],f['member']);assert original==raw,'production drift'
    data,_=scope['unpack'](raw);assert data==raw
    native_name=f['member'].replace('252371','231747')
    native_raw=bigdir.read(audit['original_archives'][str(f['archive_index'])]['path'],native_name)
    native,_=scope['unpack'](native_raw);sg=sections(data);ng=sections(native);out=bytearray(data);allowed=set();meshes=[]
    def change(off,payload):
        out[off:off+len(payload)]=payload;allowed.update(range(off,off+len(payload)))
    for mi,(vs,fs,rs,ss) in enumerate(zip(sg[0x587aa1],sg[0xc28193f0],sg[0x0f3861a2],sg[0xdf9aec1e])):
        _,vo,vsize=vs;_,fo,_=fs;_,ro,rsize=rs;si,so,ssize=ss
        count,stride=struct.unpack_from('<II',data,vo+4);assert data[vo+12]==1
        text=data[fo+16:fo+16+struct.unpack_from('<I',data,fo+4)[0]].rstrip(b'\0').decode('ascii')
        fields={v.split(':')[0]:(int(v.split(':')[1],16),v.split(':')[-1]) for v in text.split()}
        io,it=fields['i0'];wo,wt=fields['w0'];assert it=='4u8' and wt=='4u8n'
        used=set();mapping={};changed_vertices=0;merged_vertices=0
        for v in range(count):
            at=vo+16+v*stride;ids=list(data[at+io:at+io+4]);weights=list(data[at+wo:at+wo+4]);assert sum(weights) in [254,255,256]
            merged={}
            for i,w in zip(ids,weights):
                if w:
                    b=mapped(i);mapping[i]=b;merged[b]=merged.get(b,0)+w
            assert max(merged.values())<=255
            # Preserve first appearance ordering and integer weight total.
            pairs=list(merged.items());newids=bytes([b for b,w in pairs]+[0]*(4-len(pairs)));newweights=bytes([w for b,w in pairs]+[0]*(4-len(pairs)))
            changed_vertices+=newids!=bytes(ids) or newweights!=bytes(weights)
            merged_vertices+=len(pairs)<sum(w>0 for w in weights)
            used.update(merged)
            change(at+io,newids);change(at+wo,newweights)
            assert sum(newweights)==sum(weights)
        assert rsize==528 and len(used)<256 and 1 not in used
        palette=sorted(used);remap=bytearray(rsize);struct.pack_into('<II',remap,0,rsize,len(palette))
        for local,global_ in enumerate(palette):remap[16+global_]=local
        remap[272:272+len(palette)]=bytes(palette);change(ro,remap)
        # Author ConvertToRx3 keeps the destination template's native bind poses.
        _,nso,nssize=ng[0xdf9aec1e][min(mi,len(ng[0xdf9aec1e])-1)]
        assert struct.unpack_from('<II',native,nso)==(16144,252) and nssize==16144
        assert struct.unpack_from('<II',data,so)==(16336,255) and ssize==16336
        change(so,native[nso:nso+nssize]+bytes(ssize-nssize));change(16+si*16+8,struct.pack('<I',nssize))
        meshes.append(dict(vertices=count,changed_vertices=changed_vertices,merged_vertices=merged_vertices,palette=palette,mapping=[dict(source=i,name=source[i],target=b,target_name=target[b],method='exact' if source[i] in byname else 'author-alias') for i,b in sorted(mapping.items())],native_skin_sha256=sha(native[nso:nso+nssize])))
    after=bytes(out);assert len(after)==len(raw);sections(after)
    actual={i for i,(a,b) in enumerate(zip(data,after)) if a!=b};assert actual<=allowed
    for kind in [0x5878f4,0xc28193f0,0x4c9b9eb2,0xd48d7880]:
        for _,off,size in sg[kind]:assert data[off:off+size]==after[off:off+size]
    for _,off,size in sg[0x587aa1]:
        nv,stride=struct.unpack_from('<II',data,off+4)
        for v in range(nv):
            at=off+16+v*stride
            for k in range(stride):
                if k not in list(range(io,io+4))+list(range(wo,wo+4)):assert data[at+k]==after[at+k]
    path=OUT/pathlib.Path(f['member']).name;path.write_bytes(after)
    reports.append(dict(member=f['member'],archive=f['installed_archive'],path=str(path),before_sha256=sha(raw),after_sha256=sha(after),bytes=len(after),changed_bytes=len(actual),meshes=meshes))
report=dict(status='STATIC_RETARGET_BUILT_NOT_INSTALLED',source_bones=len(source),target_bones=len(target),files=reports,geometry_and_materials_preserved=True,native_runtime_verified=False)
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='files'}));print([(f['member'],f['changed_bytes'],sum(len(m['mapping']) for m in f['meshes'])) for f in reports])
