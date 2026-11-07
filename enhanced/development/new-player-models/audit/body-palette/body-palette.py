"""Original body color-map extraction and bounded texture-only neck/arm comparison.

No native shader/tint/lighting evidence and no installed resource modifications.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,sys,urllib.request
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;AUDIT=R.parent
scope=dict(Path=Path,collections=collections,struct=struct,Image=Image,np=np,hashlib=hashlib)
for node in ast.parse((AUDIT/'offline-preview.py').read_text('utf8')).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['sections','textures','mesh_data']:exec(compile(ast.Module(body=[node],type_ignores=[]),'existing-own-preview-functions','exec'),scope)
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
archive=Path('D:/FO3ID/32795/data/data_2.big')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def lab(rgb):
 a=np.asarray(rgb,dtype=float)/255;linear=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
 xyz=linear@np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]]).T
 xyz/=np.array([.95047,1.,1.08883]);e=6/29;v=np.where(xyz>e**3,np.cbrt(xyz),xyz/(3*e*e)+4/29)
 return np.array([116*v[1]-16,500*(v[0]-v[1]),200*(v[1]-v[2])])
def names(raw):
 rows=[]
 for body in scope['sections'](raw)[1285267122]:
  total,count=struct.unpack_from('<II',body);at=16
  for i in range(count):
   kind,n=struct.unpack_from('<II',body,at);at+=8;label=body[at:at+n-1].decode('ascii');at+=n;rows.append(dict(type=hex(kind),name=label))
 return rows
palette=[];entries={e[0]:e for e in bigdir.entries(archive)}
# Same normalized forearm patch in every original atlas: outside palms/nails.
body_roi=[.04,.24,.12,.58] # x0,x1,y0,y1, image origin upper-left
for index in range(1,11):
 member=f'data/sceneassets/body/skin_{index}_textures.rx3';entry=entries[member];raw=bigdir.read(archive,member);source=R/f'skin_{index}_textures.rx3';source.write_bytes(raw)
 table=names(raw);assert any(x['name']==f'body_{index}_cm' for x in table),table
 maps=scope['textures'](source,R,f'skin{index}');assert len(maps)==1
 image=Image.open(R/maps[0]['png']).convert('RGB');arr=np.asarray(image);h,w=arr.shape[:2];x0,x1,y0,y1=body_roi;patch=arr[int(y0*h):int(y1*h),int(x0*w):int(x1*w)].reshape((-1,3));median=np.median(patch,axis=0)
 palette.append(dict(index=index,archive=str(archive),member=member,archive_member_directory_entry=dict(offset=entry[1],stored_bytes=entry[2],uncompressed_size_field=entry[3]),rx3_sha256=hashlib.sha256(raw).hexdigest(),name_table=table,textures=maps,
  sample_roi_xyxy_normalized=[x0,y0,x1,y1],sample_roi_description='same left upper-atlas forearm patch; no palms/nails; hair/shadow remains',sample_pixel_count=len(patch),median_srgb=median.tolist(),median_lab_d65=lab(median).tolist(),srgb_p10=np.percentile(patch,10,axis=0).tolist(),srgb_p90=np.percentile(patch,90,axis=0).tolist()))
j=json.loads((AUDIT/'audit.json').read_text('utf8'));players=[]
for p in j['players']:
 head=next(f for f in p['files'] if '/head_' in f['label']);face=next(f for f in p['files'] if '/face_' in f['label']);meshes=scope['mesh_data'](head['source_path']);mi=max(range(len(meshes)),key=lambda i:len(meshes[i]['positions']));m=meshes[mi]
 # Use source diffuse already extracted losslessly by the previous offline exporter.
 facepng=AUDIT/'offline-preview'/str(p['playerid'])/'face-0.png';image=np.asarray(Image.open(facepng).convert('RGB'));h,w=image.shape[:2]
 tris=m['positions'][m['triangles']];centers=tris.mean(axis=1);mask=(centers[:,1]<160)&(centers[:,1]>148)&(centers[:,2]>0)&(np.abs(centers[:,0])<8)
 faceids=np.flatnonzero(mask);assert len(faceids)>0,p['name_zh']
 uv=m['uv'][m['triangles'][mask]].mean(axis=1);tx=np.clip(np.rint(uv[:,0]*(w-1)).astype(int),0,w-1);ty=np.clip(np.rint(uv[:,1]*(h-1)).astype(int),0,h-1);colors=image[ty,tx];median=np.median(colors,axis=0);l=lab(median)
 ranked=sorted([dict(index=c['index'],delta_e76=float(np.linalg.norm(l-np.asarray(c['median_lab_d65']))),body_median_srgb=c['median_srgb']) for c in palette],key=lambda d:d['delta_e76'])
 players.append(dict(playerid=p['playerid'],name_zh=p['name_zh'],name_en=p['name_en'],head_source=head['source_path'],head_source_sha256=head['source_sha256'],face_source=face['source_path'],face_source_sha256=face['source_sha256'],face_texture_index=0,head_mesh_index=mi,
  neck_sampling_window='triangle centroid: 148<Y<160, Z>0, abs(X)<8 in original bind-pose units',sampling_method='one diffuse UV sample per selected triangle centroid, raw DirectX V-down, clamped edges; unweighted median across triangles',neck_sample_triangle_count=len(faceids),sampled_uv_min=uv.min(axis=0).tolist(),sampled_uv_max=uv.max(axis=0).tolist(),neck_median_srgb=median.tolist(),neck_median_lab_d65=l.tolist(),neck_srgb_p10=np.percentile(colors,10,axis=0).tolist(),neck_srgb_p90=np.percentile(colors,90,axis=0).tolist(),all_skin_distances=ranked,texture_only_top3_skin_indices=[d['index'] for d in ranked[:3]],current_inherited_skin6_distance=next(d['delta_e76'] for d in ranked if d['index']==6),recommendation_scope='Compare these original skin textures in native game; do not automatically modify skintonecode.'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
cardw,cardh=220,315;sheet=Image.new('RGB',(cardw*5,cardh*2+70),(22,27,34));draw=ImageDraw.Draw(sheet);draw.text((12,8),'ORIGINAL BODY TEXTURES / TEXTURE-ONLY PALETTE',font=font,fill=(245,210,80));draw.text((12,34),'No shader, tint, lighting or native acceptance. Colored blocks = sampled original patch medians.',font=small,fill=(220,220,220))
for i,c in enumerate(palette):
 x=(i%5)*cardw;y=70+(i//5)*cardh;im=Image.open(R/c['textures'][0]['png']).convert('RGB').resize((200,200));sheet.paste(im,(x+10,y+25));draw.text((x+10,y+3),f'skin_{c["index"]} / body_{c["index"]}_cm',font=small,fill='white');rgb=tuple(int(v) for v in c['median_srgb']);draw.rectangle((x+10,y+235,x+80,y+285),fill=rgb);draw.text((x+88,y+240),'RGB '+str(rgb),font=small,fill='white');draw.text((x+88,y+261),'fixed forearm ROI',font=small,fill=(190,195,205))
sheet.save(R/'original-body-palette.png')
sheet=Image.new('RGB',(900,110*len(players)+75),(22,27,34));draw=ImageDraw.Draw(sheet);draw.text((12,8),'TEXTURE-ONLY LOWER NECK vs ORIGINAL FOREARM',font=font,fill=(245,210,80));draw.text((12,36),'Approximate DeltaE76 suggestions; unchanged textures; native shader/tint may change the match.',font=small,fill=(220,220,220))
for i,p in enumerate(players):
 y=75+i*110;draw.text((12,y+4),p['name_en'],font=font,fill='white');draw.rectangle((12,y+32,100,y+86),fill=tuple(int(v) for v in p['neck_median_srgb']));draw.text((112,y+37),'neck RGB '+str(tuple(int(v) for v in p['neck_median_srgb'])),font=small,fill='white');draw.text((112,y+60),f'{p["neck_sample_triangle_count"]} triangle samples',font=small,fill=(185,190,200))
 for k,rank in enumerate(p['all_skin_distances'][:3]):
  x=400+k*160;draw.rectangle((x,y+30,x+65,y+85),fill=tuple(int(v) for v in rank['body_median_srgb']));draw.text((x,y+3),f'skin {rank["index"]}',font=small,fill='white');draw.text((x+72,y+46),'dE '+format(rank['delta_e76'],'.1f'),font=small,fill='white')
sheet.save(R/'neck-to-body-suggestions.png')
url='https://raw.githubusercontent.com/tokke001/FIFALibrary22/006bbeefdae2fc77010a0e55a4ca246c89b504fc/Rx3/Other/Rx3NameTable.vb';source=urllib.request.urlopen(url).read();(R/'Rx3NameTable.vb').write_bytes(source)
result=dict(status='ORIGINAL_BODY_PALETTE_AND_TEXTURE_ONLY_SUGGESTIONS',body_archive=str(archive),body_archive_sha256=sha(archive),body_members=palette,players=players,
 original_name_table_parser_reference=dict(url=url,commit_sha='006bbeefdae2fc77010a0e55a4ca246c89b504fc',sha256=hashlib.sha256(source).hexdigest(),third_party_code_executed=False),
 limits=['Texture digital color comparison is not a physiological or rendered skin-color judgment.','Forearm atlas and lower-neck diffuse have different baked hair/shadow/AO; medians and DeltaE76 are approximate only.','No native shader/tint/lighting or dynamic-body UV mapping was observed.','Main head mesh selected by greatest vertex count; material0 diffuse assignment is provisional.','Body textures are the original body_N_cm maps identified in RX3 name tables; compressed BC blocks were not changed.','No skin/bodytype field was modified; all source model textures unchanged.'],production_written=False,skintonecode_modified=False)
(R/'palette-and-suggestions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps([dict(name=p['name_zh'],samples=p['neck_sample_triangle_count'],neck_rgb=p['neck_median_srgb'],top3=p['texture_only_top3_skin_indices'],skin6_distance=p['current_inherited_skin6_distance']) for p in players],ensure_ascii=False))
