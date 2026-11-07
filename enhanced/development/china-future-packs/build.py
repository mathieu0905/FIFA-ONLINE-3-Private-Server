"""Two additive frozen-pool +1 packs using the existing product engine."""
from pathlib import Path
import copy,hashlib,json,sqlite3,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(R.parent/'upstream-review/deps')]
from PIL import Image,ImageDraw,ImageFont
RANDOM=98432701;CHOICE=98432702
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def signed(v):v['hash']=signature({k:x for k,x in v.items() if k!='hash'});return v
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 cfgpath=S/'gamedata/club_season_products.json';iconpath=S/'gamedata/all_item_icon_manifest.json'
 baseline={str(p):sha(p) for p in [cfgpath,iconpath,S/'gamedata/custom_rosters.json',S/'gamedata/fifadb.sqlite',S/'product_packs.py',S/'all_item_icons.py',S/'pack_value.py']}
 cfg=json.loads(cfgpath.read_text('utf8'));manifest=json.loads(iconpath.read_text('utf8'));registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'))
 cards=[r for r in registry['cards'] if r['fo3_spid']//1000000==327];assert len(cards)==32
 pool=sorted(c['fo3_spid'] for c in cards);con=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
 names={c['fo3_spid']:c for c in cards};search={str(s):dict(team=t,league=l,name=names[s]['name_zh']+' '+names[s]['name_en']) for s,t,l in con.execute('select spid,teamid,leagueid from players where spid/1000000=327')};con.close()
 out=R/'icons';out.mkdir(exist_ok=True)
 font=ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc',17);small=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',13)
 for i,choice in [(RANDOM,False),(CHOICE,True)]:
  assert str(i) not in manifest['items']
  label='自选' if choice else '随机';band='+8' if choice else '+8～+12';name='中国明日之星·'+label+'包·'+band
  img=Image.new('RGBA',(170,120),(0,0,0,0));d=ImageDraw.Draw(img)
  d.rounded_rectangle((12,3,158,115),radius=12,fill='#8f1e2b' if not choice else '#28384c',outline='#e7bf65',width=3)
  d.text((85,14),'中国明日之星',font=font,anchor='mt',fill='#ffdf8b');d.text((85,44),label+'球员包',font=font,anchor='mt',fill='white')
  d.text((85,76),'32人'+('任选1人' if choice else '等概率'),font=small,anchor='mt',fill='#ffe6ba')
  d.rounded_rectangle((95,91,159,115),radius=4,fill='#edc66b');d.text((127,102),band,font=small,anchor='mm',fill='#391c15')
  icon=f'FO3N_{i}_V3';img.save(out/(icon+'.png'))
  desc=('从本期32名中国明日之星球员中任选1人，固定强化+8；选定后确认，取消不消耗。' if choice else '随机获得本期32名中国明日之星球员中的1人，每人概率1/32（3.125%）。<BR>强化概率：+8 50%、+9 25%、+10 15%、+11 8%、+12 2%；球员与强化分别独立抽取。')+'<BR>等级1；本卡种+1、1级无套装主位置能力85～92。<BR>包含王钰栋、李昊炎、邝兆镭、万项等；本期名单固定，不随以后扩充。<BR>享受现有传奇套与传奇时刻额外加成。'
  cfg['strength_packs'][str(i)]=dict(name=name,description=desc,mode='choice' if choice else 'random',price=1,grades=[0]*7+([1] if choice else [50,25,15,8,2]),tiers=[dict(name='中国明日之星32人固定池',weight=1,pool=pool)],search=copy.deepcopy(search))
  cfg['limits'][str(i)]=dict(period='week' if choice else 'day',count=3 if choice else 100)
  manifest['items'][str(i)]=dict(itemid=i,icon=icon,filename=icon+'.png',sha256=sha(out/(icon+'.png')),size=[170,120],name=name,theme='China Future red-gold '+label,source_type='Code-native pack UI built for existing FO3 icon system',grade_values=[8] if choice else list(range(8,13)),grade_badge=band,grade_mode='固定' if choice else '随机',composition='Independent Chinese season, pack mode, frozen pool count and grade layers')
 write(R/'club_season_products.json',signed(cfg));write(R/'all_item_icon_manifest.json',manifest);write(R/'baseline.json',baseline)
 write(R/'definitions.json',dict(random=RANDOM,choice=CHOICE,cards=pool,random_grades=[0]*7+[50,25,15,8,2],choice_grades=[0]*7+[1],random_probability='1/32 each',choice_count=1,legacy_definitions_preserved=True))
 print(json.dumps(dict(status='BUILT_NOT_INSTALLED',random=RANDOM,choice=CHOICE,cards=len(pool))))
if __name__=='__main__':main()
