from pathlib import Path
import sys,json,math
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(R.parent/'upstream-review/deps'),str(S/'tools/re'),str(S/'tools/player_import'),str(S),str(R.parent/'season-display')]
from PIL import Image,ImageDraw,ImageFont
import bigdir,build_moments_display as container

def main():
 ns={'__name__':'reviewed_season_icon_helpers','__file__':str(S/'tools/fo4_season.py')}
 exec(compile((R.parent/'upstream-review/upstream-ed08cf1/tools/fo4_season.py').read_text('utf8'),'reviewed_icon_helpers','exec'),ns)
 icon=Image.new('RGBA',(60,48),(0,0,0,0));d=ImageDraw.Draw(icon)
 d.rounded_rectangle((1,1,58,46),radius=8,fill='#9b202d',outline='#f6dc88',width=2)
 font=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',22);d.text((30,28),'CN',font=font,anchor='mm',fill='#ffedb5')
 star=[(30+ (7 if i%2==0 else 3)*math.sin(i*math.pi/5),10-(7 if i%2==0 else 3)*math.cos(i*math.pi/5)) for i in range(10)]
 d.polygon(star,fill='#ffdc70');icon.save(R/'season-327.png')
 p=C/ns['LABEL_BIG'];gfx=bigdir.read(p,ns['LABEL_GFX']);dds=bigdir.read(p,ns['LABEL_DDS'])
 for y in (720,800,880,960):
  ns['ICON_FREE_Y']=y
  try:new_gfx,new_dds=ns['label_with_icons'](gfx,dds,{327:icon});break
  except AssertionError as e:
   if 'atlas space not free' not in str(e):raise
 else:raise ValueError('No empty native atlas region')
 container.replace_ui_member(p,R/'Label-gfx.big',ns['LABEL_GFX'],new_gfx,bigdir)
 container.replace_ui_member(R/'Label-gfx.big',R/'Label.big',ns['LABEL_DDS'],new_dds,bigdir)
 before=p.read_bytes();after=(R/'Label.big').read_bytes()
 a={n:before[o:o+size] for n,o,size,u in bigdir.entries(p)};b={n:after[o:o+size] for n,o,size,u in bigdir.entries(R/'Label.big')}
 assert a.keys()==b.keys() and all(a[n]==b[n] for n in a if n not in (ns['LABEL_GFX'],ns['LABEL_DDS']))
 (R/'badge-proof.json').write_text(json.dumps(dict(status='PASS',native_sprites=[144,735],season=327,atlas_y=y,non_target_members_exact=True,native_verified=False),indent=2),'utf8')
 print('CN future native badge prepared; all unrelated members preserved')

if __name__=='__main__':main()
