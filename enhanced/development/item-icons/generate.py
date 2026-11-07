"""Generate native-resolution UI icons from editable vector drawing instructions.
No artwork copies, model output or gameplay data changes are used.
"""
from pathlib import Path
import json,re,hashlib,math,colorsys,collections
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;OUT=R/'native';OUT.mkdir(exist_ok=True)
SCALE=4
FONT=r'C:\Windows\Fonts\msyhbd.ttc'
REG=r'C:\Windows\Fonts\msyh.ttc'
rows=json.loads((R/'catalogue.json').read_text('utf8'))
def font(n,bold=True):return ImageFont.truetype(FONT if bold else REG,round(n*SCALE))
def semantic(row):
 n=row['definition']['name'];typ=row['definition'].get('type','');k=row['kind']
 if typ=='ES':return 'boost',(247,150,66),'强化点数'
 if '保护' in n:return 'shield',(65,211,176),'保级保护'
 if 'TRANSFERENCE' in typ or '转移' in n:return 'transfer',(55,199,225),'经验转移'
 if 'EXP' in typ or '经验' in n:return 'exp',(92,210,125),'球员经验'
 if k=='monthly':return 'calendar',(65,179,242),'每日补给'
 if 'EP' in n:return 'coins',(244,188,67),'EP 资产'
 if '改名' in n or '名称' in n:return 'identity',(123,174,244),'身份道具'
 if '恢复' in n:return 'restore',(99,208,174),'状态恢复'
 if '强' in n and k=='item':return 'boost',(247,150,66),'强化加成'
 if k=='item' and any(x in n for x in ('箱','盒')):return 'box',(233,168,103),'随机礼盒'
 if k=='item':return 'ticket',(119,169,240),'功能道具'
 if '轮' in n or '连锁' in n:return 'chain',(193,139,255),'连锁礼包'
 if k=='package':return 'box',(238,175,89),'组合礼包'
 if any(x in n for x in ('传奇','名宿','殿堂','曼联','皇马','米兰','巴萨','拜仁')):return 'legend',(236,192,98),'传奇招募'
 if '自选' in n:return 'choice',(84,216,198),'自选球员'
 if any(x in n for x in ('冒险','冲击','极限','随机')):return 'risk',(244,100,117),'随机招募'
 if any(x in n for x in ('前锋','前场','锋线')):return 'striker',(245,121,82),'前场招募'
 if any(x in n for x in ('中场','中路')):return 'midfield',(86,202,173),'中场招募'
 if any(x in n for x in ('后卫','后场','防线')):return 'defender',(81,159,238),'后场招募'
 if any(x in n for x in ('门将','守门')):return 'keeper',(204,153,244),'门将招募'
 return 'player',(100,176,247),'球员招募'
def make(row):
 n=row['definition']['name'];theme,color,caption=semantic(row);
 if theme=='chain' and row['kind']=='pack':caption='连锁专属'
 image=Image.new('RGBA',(170*SCALE,120*SCALE));d=ImageDraw.Draw(image)
 def box(b,fill,outline=None,w=1,r=0):
  b=tuple(round(x*SCALE) for x in b)
  if r:d.rounded_rectangle(b,radius=int(r*SCALE),fill=fill,outline=outline,width=max(1,int(w*SCALE)))
  else:d.rectangle(b,fill=fill,outline=outline,width=max(1,int(w*SCALE)))
 def poly(points,fill,outline=None,w=1):
  pts=[(int(x*SCALE),int(y*SCALE)) for x,y in points];d.polygon(pts,fill=fill)
  if outline:d.line(pts+[pts[0]],fill=outline,width=int(w*SCALE),joint='curve')
 def line(points,fill,width=1):d.line([(int(x*SCALE),int(y*SCALE)) for x,y in points],fill=fill,width=int(width*SCALE),joint='curve')
 def oval(b,fill,outline=None,w=1):d.ellipse(tuple(int(x*SCALE) for x in b),fill,outline,width=int(w*SCALE))
 def text(x,y,t,size,fill,anchor=None):d.text((int(x*SCALE),int(y*SCALE)),t,font=font(size),fill=fill,anchor=anchor)
 def star(x,y,rad,fill):
  poly([(x+math.sin(a*math.pi/5)*(rad if a%2==0 else rad*.44),y-math.cos(a*math.pi/5)*(rad if a%2==0 else rad*.44)) for a in range(10)],fill)
 dark=(16,25,40);white=(240,247,255);c=color
 if theme=='chain':
  family=re.split(r'第\d+轮|\d+/\d+',n)[0]
  hue=int(hashlib.sha256(family.encode()).hexdigest()[:6],16)%360/360
  c=tuple(round(x*255) for x in colorsys.hls_to_rgb(hue,.68,.65))
 if row['kind']=='pack' and theme=='player':
  hue=int(hashlib.sha256(re.sub(r'\+\d+','',n).encode()).hexdigest()[:6],16)%360/360
  c=tuple(round(x*255) for x in colorsys.hls_to_rgb(hue,.67,.60))
 box((3,2,167,118),(9,15,25,245),(*c,140),1,9)
 # Low contrast stadium beams leave title and pictogram readable.
 for j in range(5):poly([(8+j*35,3),(22+j*35,3),(90+j*8,88),(65+j*8,88)],tuple(round(v*.07+b*.93) for v,b in zip(c,(9,15,25))))
 box((9,8,12,19),c,r=1);text(17,6,caption,9,c);text(158,7,str(row['id'])[-4:],7,(127,144,166),anchor='ra')
 # Main silhouette: foil sachet, gift chest, or tool medallion.
 if row['kind']=='pack':
  poly([(54,24),(113,24),(120,82),(47,82)],(10,19,32),c,1.3)
  poly([(55,25),(112,25),(116,31),(52,31)],c)
  poly([(49,77),(118,77),(120,82),(47,82)],c)
  poly([(55,33),(63,33),(57,75),(50,75)],tuple(round(v*.25+b*.75) for v,b in zip(c,(10,19,32))))
  poly([(101,32),(111,32),(116,75),(104,75)],tuple(round(v*.12+b*.88) for v,b in zip(c,(10,19,32))))
  for j in range(12):line([(55+j*5,26),(55+j*5,29)],(12,20,32),.5)
 elif theme in ('box','chain'):
  poly([(48,40),(85,27),(125,40),(85,54)],(48,58,76),c)
  poly([(48,41),(85,55),(85,82),(48,68)],(22,33,52),c)
  poly([(85,55),(125,41),(125,68),(85,82)],(34,45,64),c)
  poly([(78,30),(88,27),(95,29),(85,33),(85,80),(77,76)],c)
  poly([(51,39),(60,36),(100,49),(91,53)],c)
 else:
  oval((55,25,115,83),(18,36,54),(*c,150),1)
  oval((60,30,110,78),(21,41,58),(*c,60),1)
 # Semantically different vector pictograms.
 if theme=='coins':
  for x,y in ((70,53),(87,49),(78,43)):
   box((x-13,y,x+13,y+10),(151,103,32),c,1,3);oval((x-13,y-4,x+13,y+5),c)
  oval((86,45,109,68),(237,186,67),(255,227,143),1);text(98,49,'E',12,dark,anchor='ma')
 elif theme in ('shield','defender'):
  poly([(70,43),(85,37),(101,43),(98,61),(85,71),(73,61)],c)
  line([(78,54),(83,59),(94,47)],dark,3)
 elif theme in ('exp','boost','restore'):
  poly([(76,67),(76,51),(68,51),(85,35),(102,51),(94,51),(94,67)],c)
  if theme=='restore':line([(71,71),(100,71)],white,2)
 elif theme=='transfer':
  line([(68,46),(99,46),(93,40)],c,3);line([(101,61),(70,61),(76,67)],c,3)
  text(85,48,'EXP',7,white,anchor='ma')
 elif theme=='calendar':
  box((67,37,105,70),(24,45,63),c,1,3);box((67,37,105,46),c,r=2)
  line([(76,33),(76,41)],white,2);line([(96,33),(96,41)],white,2)
  text(86,46,'30',18,white,anchor='ma')
 elif theme=='identity':
  box((65,40,106,68),(24,45,63),c,1,2);oval((70,45,81,56),c)
  line([(85,48),(101,48)],c,2);line([(85,56),(98,56)],c,2)
 elif theme=='ticket':
  poly([(64,42),(107,42),(107,50),(101,54),(107,58),(107,67),(64,67),(64,58),(70,54),(64,50)],c)
  star(86,54,8,dark)
 elif theme=='legend':
  poly([(73,39),(98,39),(96,54),(85,63),(75,54)],c)
  line([(73,43),(67,43),(68,52),(77,56)],c,2);line([(98,43),(104,43),(102,52),(96,56)],c,2)
  line([(85,62),(85,69)],c,3);line([(77,70),(94,70)],c,3);star(85,48,6,dark)
 elif theme=='chain':
  # Large round and step identifiers are real product metadata, not an arbitrary badge.
  m=re.search(r'第(\d+)轮.*?第(\d+)',n)
  if m:text(86,45,f'{m[1]}·{m[2]}',17,white,anchor='ma')
  else:text(86,46,re.search(r'\d+/\d+',n)[0] if re.search(r'\d+/\d+',n) else '连锁',15,white,anchor='ma')
 elif theme=='box':star(107,58,9,white)
 elif theme=='choice':
  box((69,41,98,64),(15,32,45),c,1,2);line([(75,52),(82,59),(94,44)],c,3)
 elif theme=='risk':
  poly([(85,36),(102,53),(85,71),(68,53)],c);text(85,38,'?',24,dark,anchor='ma')
 else:
  # Football shirt motif; pitch position is visible below it.
  poly([(76,39),(83,43),(89,43),(95,39),(106,47),(100,55),(95,52),(95,68),(76,68),(76,52),(70,55),(65,47)],c)
  pos={'striker':'FW','midfield':'MF','keeper':'GK'}.get(theme,'FO3');text(86,49,pos,9,dark,anchor='ma')
 # Season / strength label derived only from the existing product name.
 badge=''
 grades=re.findall(r'\+\d+',n)
 if grades:badge=grades[0]+'~'+grades[-1][1:] if len(grades)>1 and grades[0]!=grades[-1] else grades[-1]
 elif re.search(r'TOP\s*\d+',n,re.I):badge=re.search(r'TOP\s*\d+',n,re.I)[0].replace(' ','')
 elif row['kind']=='pack':
  match=re.search(r'(?:\d{2}(?:WC|EC|U|T)?|CP|LP|CC|WB|WL|EL|CC|MC|ICON)(?=赛季|球员|[· /]|$)',n,re.I)
  badge=match[0] if match else ''
 if badge:
  box((119,47,161,66),(13,23,37),c,1,4);text(140,49,badge,12 if len(badge)<5 else 8,white,anchor='ma')
 # Fit the full product name into two rows; never substitute labels for different IDs.
 clean=n.replace('（','(').replace('）',')')
 for sz in (10,9.5,9,8.5,8,7.5,7):
  lines=['']
  for ch in clean:
   if d.textlength(lines[-1]+ch,font=font(sz))>154*SCALE:lines.append(ch)
   else:lines[-1]+=ch
  if len(lines)<=2:break
 if len(lines)>2:lines=[''.join(lines)[:21],''.join(lines)[21:42]]
 for j,t in enumerate(lines[:2]):text(85,87+j*12,t,sz,white,anchor='ma')
 return image.resize((170,120),Image.Resampling.LANCZOS),theme
items={};hashes=set()
for row in rows:
 image,theme=make(row);name='FO3UI_'+str(row['id'])+'_V2';p=OUT/(name+'.png');image.save(p)
 sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha not in hashes;hashes.add(sha)
 items[str(row['id'])]=dict(itemid=row['id'],icon=name,filename=p.name,sha256=sha,size=[170,120],name=row['definition']['name'],theme=theme,source_type='Code-native vector UI icon',generator='item-icons/generate.py')
(R/'all_item_icon_manifest.json').write_text(json.dumps(dict(schema=1,items=items,pending=[]),ensure_ascii=False,indent=2),encoding='utf8')
# Review each motif and a representative spread of all products.
selection=[];seen=set()
for row in rows:
 key=semantic(row)[0]
 if key not in seen:selection.append(row);seen.add(key)
selection+=rows[::29]
sheet=Image.new('RGB',(170*6,120*math.ceil(len(selection)/6)),(23,30,42))
for k,row in enumerate(selection):im=Image.open(OUT/items[str(row['id'])]['filename']);sheet.paste(im,(k%6*170,k//6*120),im)
sheet.save(R/'preview.png')
print(json.dumps(dict(icons=len(items),unique_images=len(hashes),themes=dict(collections.Counter(x['theme'] for x in items.values())),preview=str(R/'preview.png'))))
