"""Assemble native artwork and separate metadata-driven UI labels/grade badges.
Original and image_gen artwork is preserved unchanged as a source layer.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,re,hashlib,collections,math
R=Path(__file__).resolve().parent;A=Path(r'D:\FO3ID\32795\_cache\games\fo3id\externalAssets\shop');OUT=R/'native';OUT.mkdir(exist_ok=True)
rows=json.loads((R/'catalogue.json').read_text('utf8'));old={x['id']:x for x in json.loads((R.parent/'catalogue.json').read_text('utf8'))}
S=4;F=r'C:\Windows\Fonts\msyhbd.ttc';EF=r'C:\Windows\Fonts\arialbd.ttf'
def font(n,eng=False):return ImageFont.truetype(EF if eng else F,round(n*S))
def source(row):
 i=row['id'];n=row['definition']['name'];typ=row['definition'].get('type','');kind=row['kind'];oldicon=str(old.get(i,{}).get('definition',{}).get('itemicon',''))
 if i==1000090:return R/'protection-source.png','protection'
 if kind=='item':
  if typ=='EP' or re.search(r'\b(?:BP|EP)\b',n):return R/'bp-source.png','bp'
  if i==2:return A/'6.png','points'
  if typ=='ENHANCEMENT_BOOST':return A/'8563.png','boost'
  if (A/(str(i)+'.png')).exists():return A/(str(i)+'.png'),'native'
  if oldicon and not oldicon.startswith('FO3UI_') and (A/(oldicon+'.png')).exists():return A/(oldicon+'.png'),'native'
  if 'EXP' in typ:return A/'9000200.png','exp'
  return A/'701.png','lottery'
 if kind=='monthly':return A/'70013.png','monthly'
 if kind=='package':
  if any(x in n for x in ('冒险','冲击','极限','百包')):key='riskbox'
  elif '自选' in n:key='choicebox'
  elif any(x in n for x in ('传奇','殿堂','名宿')):key='legendbox'
  elif any(x in n for x in ('经典','怀旧')):key='classicbox'
  elif any(x in n for x in ('成长','新手','建队','启航')):key='growthbox'
  else:key='bundle'
  return R/(key+'-source.png'),key
 # Exact shipped artwork takes precedence for original SKUs.
 if (A/(str(i)+'.png')).exists():return A/(str(i)+'.png'),'native'
 if '自选' in n or row['definition'].get('category')=='DRAFTPACK':return R/'choice-source.png','choice'
 if any(x in n for x in ('传奇','名宿','殿堂','曼联','皇马','巴萨','米兰','拜仁')):return A/'418060601.png','legend'
 if any(x in n for x in ('冒险','冲击','极限')):return R/'risk-source.png','risk'
 if row['grades'] and max(row['grades'])>=5:return R/'elite-source.png','elite'
 return R/'season-source.png','season'
def label(row,theme):
 n=row['definition']['name']
 if row['kind']=='package':
  n=re.split(r'第\d+轮',n)[0].replace('·十轮版','').replace('·整轮','')
  n=n.split('·')[0]
 elif row['kind']=='pack':
  n=n.split('·')[0]
 if theme=='bp':n=n.replace('EP','BP')
 return n
cache={}
def artwork(path):
 if path not in cache:
  im=Image.open(path).convert('RGBA');bbox=im.getchannel('A').point(lambda x:255 if x>12 else 0).getbbox();im=im.crop(bbox)
  factor=min(140*S/im.width,110*S/im.height);im=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.LANCZOS);cache[path]=im
 return cache[path].copy()
def plate(d,b,color=(226,188,105),radius=2):
 b=tuple(round(x*S) for x in b);d.rounded_rectangle(b,radius=radius*S,fill=(9,13,20,246),outline=(*color,255),width=S)
 # Bevel highlight, rather than the flat full-image panels of V2.
 x,y,x2,y2=b;d.line([(x+3*S,y+S),(x2-3*S,y+S)],fill=(255,236,183,220),width=S)
def tx(d,xy,text,size,fill=(255,246,217),anchor=None,eng=False):
 d.text(tuple(round(v*S) for v in xy),text,font=font(size,eng),fill=fill,stroke_width=max(1,round(.45*S)),stroke_fill=(2,4,8,255),anchor=anchor)
def build(row):
 p,theme=source(row);im=Image.new('RGBA',(170*S,120*S));art=artwork(p);im.alpha_composite(art,((160*S-art.width)//2,(111*S-art.height)//2))
 d=ImageDraw.Draw(im);n=row['definition']['name'];grades=row['grades'];badge='';mode=''
 if grades:
  badge='+'+str(grades[0]) if len(grades)==1 else '+'+str(min(grades))+'～+'+str(max(grades))
  mode=('固定' if len(grades)==1 else '随机') if row['kind']=='pack' else '内含'
  width=max(46,min(84,math.ceil(d.textlength(badge,font=font(15)))//S+12));x=169-width
  plate(d,(x,90,169,119),(245,197,86) if min(grades)>=8 else (188,208,224))
  tx(d,(x+5,90),mode,7,(214,222,232));tx(d,((x+169)/2,100),badge,15 if len(badge)<7 else 13,anchor='ma',eng=False)
 # Standalone season/family plate: existing descriptive native art remains uncovered.
 lab=label(row,theme)
 # Short explicit family names; the full exact name stays in the game's native product label.
 lab=lab.replace('普通限购','').replace('一次限购','').strip('·')
 if not lab:lab=n.split('·')[-1]
 widthlimit=82 if grades else 160;size=10
 while size>7 and d.textlength(lab,font=font(size))>widthlimit*S:size-=.5
 if d.textlength(lab,font=font(size))>widthlimit*S:
  while d.textlength(lab+'…',font=font(size))>widthlimit*S:lab=lab[:-1]
  lab+='…'
 w=math.ceil(d.textlength(lab,font=font(size))/S)+8
 plate(d,(1,105,min(w+1,89 if grades else 168),119),(151,169,192));tx(d,(5,105),lab,size,(235,242,248))
 stage=re.search(r'第(\d+)轮.*?第(\d+)',n)
 if stage:
  t=stage[1]+'轮·'+stage[2]+'档';w=math.ceil(d.textlength(t,font=font(9))/S)+9;plate(d,(169-w,1,169,17),(180,189,204));tx(d,(169-w+4,1),t,9)
 return im.resize((170,120),Image.Resampling.LANCZOS),p,theme,badge,mode
items={}
for row in rows:
 im,p,theme,badge,mode=build(row);key='FO3N_'+str(row['id'])+'_V3';dest=OUT/(key+'.png');im.save(dest)
 items[str(row['id'])]=dict(itemid=row['id'],icon=key,filename=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),size=[170,120],name=row['definition']['name'],theme=theme,source_path=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_type='Built-in image_gen' if p.parent==R else 'Existing native client artwork reused',grade_values=row['grades'],grade_badge=badge,grade_mode=mode,composition='Unchanged artwork layer, aspect-preserving resize; separate code-native season/family and bottom-right grade UI layers')
(R/'all_item_icon_manifest.json').write_text(json.dumps(dict(schema=1,items=items,pending=[]),ensure_ascii=False,indent=2),encoding='utf8')
selected=[]
for i in (28001,97010002,97010100,98248008,98248018,97300001,70000001,1000090,60000001,1):
 if str(i) in items:selected.append(items[str(i)])
seen=set(x['theme'] for x in selected)
for row in items.values():
 if row['theme'] not in seen:selected.append(row);seen.add(row['theme'])
selected=selected[:24];sheet=Image.new('RGB',(680,math.ceil(len(selected)/4)*145),(32,36,44));d=ImageDraw.Draw(sheet);f=ImageFont.truetype(F,10)
for k,row in enumerate(selected):
 im=Image.open(OUT/row['filename']);x=k%4*170;y=k//4*145;sheet.paste(im,(x,y),im);name=row['name'];d.text((x+3,y+122),name[:16],font=f,fill=(225,230,235))
sheet.save(R/'preview.png')
print(json.dumps(dict(items=len(items),art_sources=len(cache),grade_icons=sum(bool(x['grade_values']) for x in items.values()),grade_rules=dict(collections.Counter(x['grade_mode'] for x in items.values())),preview=str(R/'preview.png'))))
