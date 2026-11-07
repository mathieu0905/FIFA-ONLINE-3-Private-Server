"""Bounded RX3 v4 mesh audit, translated from pinned FIFALibrary22 read routines.

Reads local assets only. Does not import or execute third party software.
"""
from pathlib import Path
import ast,collections,hashlib,json,math,re,struct,sys,zlib
R=Path(__file__).resolve().parent
AUDIT=json.loads((R/'audit.json').read_text('utf8'))
REFERENCE=json.loads((R/'original-native-reference.json').read_text('utf8'))
SOURCES=json.loads((R/'reference-source/manifest.json').read_text('utf8'))
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
scope={'struct':struct,'zlib':zlib,'hashlib':hashlib}
for node in ast.parse(Path(AUDIT['decoder_source']).read_text('utf8')).body:
 if isinstance(node,ast.FunctionDef) and node.name=='unpack':exec(compile(ast.Module(body=[node],type_ignores=[]),'existing-unpack','exec'),scope)
TYPES={5798132:'index',5798561:'vertex',3263271920:'format',255353250:'remap',3751472158:'skin',3566041216:'primitive',2047566042:'texture'}
FORMATS={'3f32':('3f',12),'4f16':('4e',8),'2f16':('2e',4),'2f32':('2f',8),'4u8':('4B',4),'4u8n':('4B',4),'4u16':('4H',8),'4u16n':('4H',8),'3s10n':('I',4)}
def digest(d):return hashlib.sha256(d).hexdigest()
def scalar(d,offset,fmt):return struct.unpack_from(fmt,d,offset)
def parse(raw,label):
 d,chunks=scope['unpack'](raw);assert d[:4]==b'RX3l'
 version,size,count=scalar(d,4,'<III');assert version==4 and size==len(d)
 groups=collections.defaultdict(list);sections=[]
 for i in range(count):
  kind,off,length,other=scalar(d,16+i*16,'<IIII');assert off+length<=len(d)
  section=dict(kind=kind,offset=off,size=length,body=d[off:off+length]);sections.append(section);groups[TYPES.get(kind,str(kind))].append(section)
 out=dict(label=label,raw_sha256=digest(raw),unwrapped_sha256=digest(d),file_size=len(d),issues=[],unsupported=[],meshes=[],textures=[])
 formats=groups['format'];vbs=groups['vertex'];ibs=groups['index'];skins=groups['skin'];remaps=groups['remap'];primitives=groups['primitive']
 if vbs:
  assert len(formats)==len(vbs)==len(ibs)==len(skins)==len(remaps)==len(primitives),'per-mesh section counts differ'
 for mi,(f,v,ib,skin,remap,prim) in enumerate(zip(formats,vbs,ibs,skins,remaps,primitives)):
  fb=f['body'];total,fmt_size=scalar(fb,0,'<II');assert total==len(fb) and 16+fmt_size<=len(fb)
  text=fb[16:16+fmt_size].rstrip(b'\0').decode('ascii');fields=[]
  for element in text.split():
   parts=element.split(':');usage=parts[0];typ=parts[-1];assert typ in FORMATS,typ
   # These assets carry explicit hexadecimal byte offsets.
   assert len(parts)>=3,'implicit descriptor offset not supported'
   offset=int(parts[1],16);fields.append((usage,offset,typ))
  vb=v['body'];vtotal,nv,stride=scalar(vb,0,'<III');endian=vb[12];assert vtotal==len(vb) and 16+nv*stride<=len(vb) and endian in [0,1]
  prefix='<' if endian==1 else '>'
  for usage,offset,typ in fields:assert offset+FORMATS[typ][1]<=stride
  index=ib['body'];itotal,ni=scalar(index,0,'<II');istride=index[8];assert itotal==len(index) and istride in [2,4] and 16+ni*istride<=len(index)
  indices=scalar(index,16,'<'+str(ni)+('H' if istride==2 else 'I'));invalid_indices=sum(x>=nv for x in indices)
  primitive=scalar(prim['body'],0,'<I')[0]
  degenerate_triangles=sum(len(set(indices[i:i+3]))<3 for i in range(0,ni,3)) if primitive==4 and ni%3==0 else None
  skin_data=skin['body'];stotal,nbones=scalar(skin_data,0,'<II');assert stotal==len(skin_data) and 16+64*nbones<=len(skin_data)
  poses=[];nonfinite_pose=0
  for b in range(nbones):
   floats=scalar(skin_data,16+64*b,'<15f');nonfinite_pose+=sum(not math.isfinite(x) for x in floats);poses.append(skin_data[16+64*b:16+64*(b+1)])
  remap_data=remap['body'];rsize=scalar(remap_data,0,'<I')[0];used_count=remap_data[4];reserve=(rsize-16)//2;assert rsize==len(remap_data) and used_count<=reserve
  global_to_local=remap_data[16:16+reserve];palette_raw=remap_data[16+reserve:16+2*reserve]
  if used_count and palette_raw[0]==1:
   palette=[x+256 for x in palette_raw[1:used_count]];remap_high_byte=True
  else:palette=list(palette_raw[:used_count]);remap_high_byte=False
  positions=[];uv_nonfinite=0;position_nonfinite=0;weight_sums=collections.Counter();all_bone_ids=set();weighted_bone_ids=set();invalid_weighted=0;badweight=0;unsupported=[]
  field_map={name:(off,typ) for name,off,typ in fields}
  assert 'p0' in field_map
  for vertex in range(nv):
   start=16+vertex*stride;values={}
   for usage,offset,typ in fields:
    fmt,_=FORMATS[typ];vs=scalar(vb,start+offset,prefix+fmt)
    values[usage]=vs
    if usage.startswith('p'):
     position_nonfinite+=sum(not math.isfinite(x) for x in vs);positions.append(vs[:3])
    elif usage.startswith('t'):uv_nonfinite+=sum(not math.isfinite(x) for x in vs)
   for usage,vs in values.items():
    if not usage.startswith('i'):continue
    weights=values.get('w'+usage[1:]);assert weights is not None
    weight_type=field_map['w'+usage[1:]][1];denom=255 if weight_type=='4u8n' else 65535 if weight_type=='4u16n' else None;assert denom
    # Endian reverses 4u8 indices and weights together in the reference implementation;
    # for pairing, weight sum, and bone range it has no effect.
    weight_sums[sum(weights)]+=1;badweight+=abs(sum(weights)-denom)>1;all_bone_ids.update(vs)
    for bone,weight in zip(vs,weights):
     if weight:
      weighted_bone_ids.add(bone);invalid_weighted+=bone>=nbones
  finite=[p for p in positions if all(math.isfinite(x) for x in p)]
  bounds=dict(min=[min(p[i] for p in finite) for i in range(3)],max=[max(p[i] for p in finite) for i in range(3)]) if finite else None
  palette_missing=sorted(weighted_bone_ids-set(palette))
  row=dict(mesh_index=mi,vertex_format=text,vertex_count=nv,vertex_stride=stride,vertex_endianness='little' if endian else 'big',index_count=ni,index_stride=istride,index_min=min(indices,default=None),index_max=max(indices,default=None),out_of_range_indices=invalid_indices,
    primitive_code=primitive,triangle_count=ni//3 if primitive==4 and ni%3==0 else None,degenerate_triangles=degenerate_triangles,nonfinite_position_values=position_nonfinite,nonfinite_uv_values=uv_nonfinite,bounds=bounds,
    skin_matrix_count=nbones,nonfinite_pose_float_values=nonfinite_pose,skin_pose_payload_sha256=digest(skin_data[16:16+64*nbones]),
    first_252_skin_pose_payload_sha256=digest(skin_data[16:16+64*min(252,nbones)]),bone_indices_all=sorted(all_bone_ids),weighted_bone_indices=sorted(weighted_bone_ids),weighted_indices_outside_skin=invalid_weighted,
    blend_weight_sum_integer_histogram=dict(weight_sums),weight_sums_outside_one_quantum=badweight,bone_remap_count=used_count,bone_remap_palette=palette,bone_remap_high_byte_mode=remap_high_byte,
    weighted_bones_missing_from_remap=palette_missing,vertex_payload_sha256=digest(vb[16:16+nv*stride]),index_payload_sha256=digest(index[16:16+ni*istride]))
  if any([invalid_indices,position_nonfinite,uv_nonfinite,nonfinite_pose,invalid_weighted,badweight,palette_missing]):out['issues'].append(dict(mesh=mi,kind='NUMERIC_OR_BINDING_CHECK_REQUIRES_REVIEW'))
  if primitive!=4 or ni%3:out['issues'].append(dict(mesh=mi,kind='NOT_A_DIVISIBLE_TRIANGLE_LIST'))
  out['meshes'].append(row)
 for ti,t in enumerate(groups['texture']):
  tb=t['body'];total,ttype,tformat,flags,pad,width,height,faces,mips=scalar(tb,0,'<IBBBBHHHH');assert width and height and faces and mips
  at=16;levels=[]
  for face in range(faces):
   for level in range(mips):
    pitch,lines,nbytes,padding=scalar(tb,at,'<IIII');at+=16;assert at+nbytes<=len(tb)
    levels.append(dict(face=face,level=level,pitch=pitch,lines=lines,bytes=nbytes,pitch_times_lines_matches=pitch*lines==nbytes));at+=nbytes
  out['textures'].append(dict(texture_index=ti,type=ttype,format_code=tformat,format_name={0:'DXT1',1:'DXT3',2:'DXT5',3:'B8G8R8A8',4:'L8',5:'L8A8',6:'R8G8B8A8',7:'ATI2'}.get(tformat,'UNKNOWN'),data_flags=flags,width=width,height=height,faces=faces,mip_levels=mips,declared_total_size=total,actual_section_size=len(tb),trailing_bytes=len(tb)-at,levels=levels))
 return out
all_files=[]
for p in AUDIT['players']:
 for f in p['files']:
  raw=Path(f['source_path']).read_bytes()
  try:parsed=parse(raw,f['label']);parsed.update(playerid=p['playerid'],name_zh=p['name_zh'],source_path=f['source_path'])
  except Exception as ex:parsed=dict(label=f['label'],playerid=p['playerid'],name_zh=p['name_zh'],parse_error=repr(ex),issues=['UNSUPPORTED_OR_INVALID'])
  all_files.append(parsed)
native=[]
for f in REFERENCE:
 folder=f['label'].split('/')[1];index=3 if folder=='faces' else 6 if folder=='hairlod' else 4;archive=Path(AUDIT['original_archives'][str(index)]['path']);raw=bigdir.read(archive,'data/sceneassets/'+f['label'].split('/',1)[1]);native.append(parse(raw,f['label']))
lod=[]
for pid in [252371,277643]+[x['playerid'] for x in AUDIT['players'] if x['playerid'] not in [252371,277643]]:
 files=[x for x in all_files if x['playerid']==pid];near=next(x for x in files if '/hair_' in x['label'] and 'textures' not in x['label']);far=next(x for x in files if '/hairlod_' in x['label'])
 if 'meshes' not in near or 'meshes' not in far:continue
 nverts=sum(x['vertex_count'] for x in near['meshes']);fverts=sum(x['vertex_count'] for x in far['meshes']);ntri=sum(x['triangle_count'] or 0 for x in near['meshes']);ftri=sum(x['triangle_count'] or 0 for x in far['meshes'])
 lod.append(dict(playerid=pid,name_zh=near['name_zh'],near_vertices=nverts,far_vertices=fverts,near_triangles=ntri,far_triangles=ftri,far_more_vertices_than_near=fverts>nverts,far_more_triangles_than_near=ftri>ntri,invalid_far_indices=sum(x['out_of_range_indices'] for x in far['meshes'])))
report=dict(status='BOUNDED_SOURCE_BASED_MESH_AUDIT_COMPLETE_NATIVE_PENDING',source_manifest=SOURCES,supported_format='RX3l v4 little-endian section headers; raw/chunkzip; explicit vertex offsets; 3f32/4f16 positions, 2f16/2f32 UV, 4u8/4u16 indices, normalized byte/short weights, index strides 2/4, skin matrices and remap palettes; texture mip headers and payload bounds',
 section_semantics_correction='0x5878f4 is INDEX_BUFFER and 0x587aa1 is VERTEX_BUFFER; prior payload-identity comparison did not claim semantic decoding.',
 files=all_files,original_native_mbappe=native,hair_lod_comparison=lod,
 limitations=['Original parser was read only and not installed/executed. This Python decoder is an independent bounded translation.','No identification of engine skeleton bone names/semantic hierarchy or matching animation channels.','Bone transforms may be finite and range-safe yet have incompatible meaning in the game.','Packed normals/tangents remain raw, not semantically decoded.','No material/shader binding, texture compression decompression, silhouette likeness or native runtime proof.','LOD mesh sections are paired by their occurrence ordering, consistent with source parser structure; filename far/near is routing evidence, not observed switching.'],production_written=False,native_verified=False)
(R/'mesh-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(files=len(all_files),parsed=sum('parse_error' not in x for x in all_files),issue_files=[x['label'] for x in all_files if x['issues']],native_issue_files=[x['label'] for x in native if x['issues']],lod=lod),ensure_ascii=False))
