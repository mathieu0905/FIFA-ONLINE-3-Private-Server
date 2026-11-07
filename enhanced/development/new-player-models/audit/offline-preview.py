"""Export original RX3 bind-pose meshes and unchanged BC texture blocks; software preview.

OFFLINE preview only: this is not a game screenshot or shader/animation validation.
"""
from pathlib import Path
import collections,hashlib,json,math,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'offline-preview';O.mkdir(exist_ok=True)
AUDIT=json.loads((R/'audit.json').read_text('utf8'))
REPORT=json.loads((R/'mesh-audit.json').read_text('utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sections(raw):
 assert raw[:4]==b'RX3l';version,size,count=struct.unpack_from('<III',raw,4);assert version==4 and size==len(raw)
 groups=collections.defaultdict(list)
 for i in range(count):
  t,off,n,other=struct.unpack_from('<IIII',raw,16+16*i);assert off+n<=len(raw);groups[t].append(raw[off:off+n])
 return groups
def mesh_data(path):
 groups=sections(Path(path).read_bytes());out=[]
 for fmt,vert,index in zip(groups[3263271920],groups[5798561],groups[5798132]):
  size=struct.unpack_from('<I',fmt,4)[0];descr=fmt[16:16+size].rstrip(b'\0').decode();fields={}
  for token in descr.split():
   parts=token.split(':');fields[parts[0]]=(int(parts[1],16),parts[-1])
  total,count,stride=struct.unpack_from('<III',vert);prefix='<' if vert[12]==1 else '>';positions=[];uvs=[];indices=[];weights=[]
  for i in range(count):
   base=16+i*stride
   off,typ=fields['p0'];p=struct.unpack_from(prefix+('3f' if typ=='3f32' else '4e'),vert,base+off);positions.append(p[:3])
   off,typ=fields['t0'];uvs.append(struct.unpack_from(prefix+('2e' if typ=='2f16' else '2f'),vert,base+off))
   off,typ=fields['i0'];indices.append(struct.unpack_from(prefix+('4B' if typ=='4u8' else '4H'),vert,base+off))
   off,typ=fields['w0'];denom=255 if typ=='4u8n' else 65535;weights.append([v/denom for v in struct.unpack_from(prefix+('4B' if typ=='4u8n' else '4H'),vert,base+off)])
  ni=struct.unpack_from('<I',index,4)[0];idx=np.array(struct.unpack_from('<'+str(ni)+('H' if index[8]==2 else 'I'),index,16),dtype=np.int64).reshape((-1,3))
  out.append(dict(positions=np.array(positions,dtype=float),uv=np.array(uvs,dtype=float),triangles=idx,blend_indices=indices,blend_weights=weights,vertex_format=descr))
 return out
def textures(path,folder,prefix):
 rows=[]
 for i,body in enumerate(sections(Path(path).read_bytes())[2047566042]):
  total,ttype,fmt,flags,pad,w,h,faces,mips=struct.unpack_from('<IBBBBHHHH',body);assert faces==1 and fmt in [0,1,2,7,12] and flags==1,(fmt,flags)
  at=16;blocks=[];sizes=[]
  for m in range(mips):
   pitch,lines,size,padding=struct.unpack_from('<IIII',body,at);at+=16;block=body[at:at+size];assert len(block)==size;blocks.append(block);sizes.append(size);at+=size
  assert at<=len(body)
  code={0:b'DXT1',1:b'DXT3',2:b'DXT5',7:b'ATI2',12:b'ATI1'}[fmt];header=[124,0x81007|(0x20000 if mips>1 else 0),h,w,sizes[0],0,mips]+[0]*11+[32,4,int.from_bytes(code,'little'),0,0,0,0,0]+[0x1000|(0x400008 if mips>1 else 0),0,0,0,0]
  dds=folder/f'{prefix}-{i}.dds';dds.write_bytes(b'DDS '+struct.pack('<31I',*header)+b''.join(blocks))
  image=Image.open(dds).convert('RGBA');assert image.size==(w,h);png=folder/f'{prefix}-{i}.png';image.save(png)
  rows.append(dict(index=i,dds=dds.name,png=png.name,width=w,height=h,format=code.decode(),mips=mips,original_bc_blocks_sha256=hashlib.sha256(b''.join(blocks)).hexdigest(),dds_bc_blocks_sha256=hashlib.sha256(dds.read_bytes()[128:]).hexdigest(),unchanged_bc_blocks=True))
 return rows
def export_obj(meshes,folder,name,texture_rows):
 obj=folder/f'{name}.obj';mtl=folder/f'{name}.mtl';lines=['# OFFLINE bind-pose export; original positions; no coordinate transform.',f'mtllib {mtl.name}'];material=[];base=1;skin=[];primary=max(range(len(meshes)),key=lambda i:len(meshes[i]['positions']))
 for i,m in enumerate(meshes):
  mat=f'{name}_mesh_{i}';lines += [f'o {mat}',f'usemtl {mat}']
  for p in m['positions']:lines.append('v '+' '.join(format(x,'.9g') for x in p))
  # OBJ V is upward; raw DirectX V is downward. Explicitly flip V during export.
  for uv in m['uv']:lines.append('vt '+format(uv[0],'.9g')+' '+format(1-uv[1],'.9g'))
  for f in m['triangles']:lines.append('f '+' '.join(f'{int(x)+base}/{int(x)+base}' for x in f))
  material += [f'newmtl {mat}','Ka 0.15 0.15 0.15','Kd 1 1 1','Ks 0 0 0','illum 1']
  # Only first head mesh has a proposed face diffuse map; eye-mesh shader is unresolved.
  if i==primary and texture_rows:material += [f'map_Kd {texture_rows[0]["png"]}','# First texture on largest mesh is a provisional offline diffuse assignment, not a native shader binding.']
  else:material += ['# Texture/material role unresolved; neutral default.']
  material += [''];base+=len(m['positions']);skin.append(dict(mesh=i,vertex_format=m['vertex_format'],blend_indices=m['blend_indices'],blend_weights=m['blend_weights']))
 obj.write_text('\n'.join(lines)+'\n',encoding='utf8');mtl.write_text('\n'.join(material)+'\n',encoding='utf8');(folder/f'{name}-skin.json').write_text(json.dumps(skin,separators=(',',':')),encoding='utf8')
 return obj.name,mtl.name
def render(mesh,texture,view,path,title):
 # Orthographic software Z-buffer with texture interpolation; no backface culling.
 width,height=600,720;margin=50;verts=mesh['positions'];faces=mesh['triangles'];uvs=mesh['uv'];tex=np.asarray(texture.convert('RGB'),dtype=float)/255
 if view=='front':camera=np.array([[1.,0,0],[0,1,0],[0,0,1]])
 else:camera=np.array([[0.,0,-1],[0,1,0],[1,0,0]])
 transformed=verts@camera.T;lo=transformed.min(0);hi=transformed.max(0);scale=min((width-2*margin)/(hi[0]-lo[0]),(height-150)/(hi[1]-lo[1]));mid=(lo+hi)/2
 xy=np.column_stack(((transformed[:,0]-mid[0])*scale+width/2,(mid[1]-transformed[:,1])*scale+height/2+10));depth=transformed[:,2]
 canvas=np.full((height,width,3),[.085,.105,.135]);zbuf=np.full((height,width),-np.inf);light=np.array([-.25,.4,1.]);light/=np.linalg.norm(light)
 face_normals=np.cross(transformed[faces[:,1]]-transformed[faces[:,0]],transformed[faces[:,2]]-transformed[faces[:,0]]);length=np.linalg.norm(face_normals,axis=1);face_normals/=np.where(length[:,None]>0,length[:,None],1)
 normals=np.zeros_like(transformed)
 for k in range(3):np.add.at(normals,faces[:,k],face_normals)
 length=np.linalg.norm(normals,axis=1);normals/=np.where(length[:,None]>0,length[:,None],1)
 luminance=.55+.45*np.abs(normals@light)
 for f in faces:
  p=xy[f];minx=max(0,int(math.floor(p[:,0].min())));maxx=min(width-1,int(math.ceil(p[:,0].max())));miny=max(0,int(math.floor(p[:,1].min())));maxy=min(height-1,int(math.ceil(p[:,1].max())))
  if maxx<minx or maxy<miny:continue
  xx,yy=np.meshgrid(np.arange(minx,maxx+1)+.5,np.arange(miny,maxy+1)+.5)
  den=(p[1,1]-p[2,1])*(p[0,0]-p[2,0])+(p[2,0]-p[1,0])*(p[0,1]-p[2,1])
  if abs(den)<1e-9:continue
  w0=((p[1,1]-p[2,1])*(xx-p[2,0])+(p[2,0]-p[1,0])*(yy-p[2,1]))/den;w1=((p[2,1]-p[0,1])*(xx-p[2,0])+(p[0,0]-p[2,0])*(yy-p[2,1]))/den;w2=1-w0-w1
  zz=w0*depth[f[0]]+w1*depth[f[1]]+w2*depth[f[2]];sub=zbuf[miny:maxy+1,minx:maxx+1];mask=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(zz>sub)
  if not mask.any():continue
  uv=w0[...,None]*uvs[f[0]]+w1[...,None]*uvs[f[1]]+w2[...,None]*uvs[f[2]]
  tx=np.clip(np.rint(uv[...,0]*(tex.shape[1]-1)).astype(int),0,tex.shape[1]-1);ty=np.clip(np.rint(uv[...,1]*(tex.shape[0]-1)).astype(int),0,tex.shape[0]-1)
  color=tex[ty,tx]*(w0*luminance[f[0]]+w1*luminance[f[1]]+w2*luminance[f[2]])[...,None]
  canvas[miny:maxy+1,minx:maxx+1][mask]=color[mask];sub[mask]=zz[mask]
 image=Image.fromarray(np.uint8(np.clip(canvas,0,1)*255));draw=ImageDraw.Draw(image)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
 draw.text((18,14),'OFFLINE / NATIVE UNVERIFIED',font=font,fill=(255,205,70));draw.text((18,42),title+' | '+view,font=font,fill=(235,240,245))
 draw.text((18,height-51),'MAIN HEAD MESH + FIRST FACE TEXTURE',font=small,fill=(225,225,225));draw.text((18,height-29),'Hair/eye shader and animation not represented.',font=small,fill=(190,195,205));image.save(path)
 return image
players=[];montage=[]
ordered=sorted(AUDIT['players'],key=lambda p:([252371,277643].index(p['playerid']) if p['playerid'] in [252371,277643] else 2+p['playerid']))
for player in ordered:
 pid=player['playerid'];folder=O/str(pid);folder.mkdir(exist_ok=True);files=player['files'];face=next(f for f in files if '/face_' in f['label']);hairtex=next(f for f in files if '/hair_' in f['label'] and 'textures' in f['label']);maps=textures(face['source_path'],folder,'face');hairmaps=textures(hairtex['source_path'],folder,'hair');outputs=[];head=None
 for role,prefix in [('head','/head_'),('hair','/hair_'),('hairlod','/hairlod_')]:
  f=next(f for f in files if prefix in f['label'] and 'textures' not in f['label']);meshes=mesh_data(f['source_path']);obj,mtl=export_obj(meshes,folder,role,maps if role=='head' else hairmaps);outputs.extend([obj,mtl,role+'-skin.json'])
  if role=='head':head=meshes
 image=Image.open(folder/maps[0]['png']);views=[];head_primary=max(range(len(head)),key=lambda i:len(head[i]['positions']))
 for view in ['front','side']:
  output=folder/f'{view}.png';im=render(head[head_primary],image,view,output,player['name_en']);views.append(output.name)
 montage.append(Image.open(folder/'front.png').resize((300,360)))
 players.append(dict(playerid=pid,name_zh=player['name_zh'],name_en=player['name_en'],directory=str(folder),mesh_exports=outputs,face_textures=maps,hair_textures=hairmaps,previews=views,head_preview_mesh_index=head_primary,head_preview_mesh_selection='largest vertex count, inferred primary face; mesh order differs for Saka',source_files=[dict(path=f['source_path'],sha256=f['source_sha256']) for f in files]))
 preview=O/'progress.json';preview.write_text(json.dumps(dict(completed_players=len(players),players=players),ensure_ascii=False,indent=2),encoding='utf8')
 print('EXPORTED',pid,player['name_en'],flush=True)
sheet=Image.new('RGB',(900,1080),(20,25,33))
for i,im in enumerate(montage):sheet.paste(im,((i%3)*300,(i//3)*360))
sheet.save(O/'nine-heads-offline.png')
manifest=dict(status='OFFLINE_BIND_POSE_EXPORT_AND_PREVIEW_NATIVE_UNVERIFIED',players=players,contact_sheet=str(O/'nine-heads-offline.png'),
 limitations=['Not game screenshots; no native renderer, animation or likeness acceptance.','Head preview renders the mesh with largest vertex count, with provisional first face diffuse texture. Saka primary face is mesh1, unlike the others. Hair and eye material shaders are not rendered.','All original head/hair/hairlod geometry and UV are exported; OBJ has no skeleton, so original blend data are saved in separate skin JSON.','Original axes and bind-pose coordinates are preserved. Front looks from +Z and side from +X, Y up. Camera orientation is inferred, not native camera evidence.','OBJ vt flips V (1-rawV); software preview samples raw DirectX UV with image-down V. Winding preserved; offline renderer disables backface culling.','Textures are not painted or replaced. DDS stores the original concatenated BC blocks, and PNG is lossless decoded top mip; source mip headers are represented in manifest.','Only DXT1/3/5 and ATI1/2 linear single-face texture containers supported; proprietary material slot semantics unresolved.'],source_format_reference=str(R/'reference-source/manifest.json'),production_written=False)
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print('DONE',len(players))
