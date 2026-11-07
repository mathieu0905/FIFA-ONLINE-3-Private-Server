"""Version low-grade sale/chain packs; keep issued old definitions untouched."""
import collections,copy,importlib.util,json,re
import host
from build import signed,write,sha
from PIL import Image,ImageDraw,ImageFont
R=host.R;h=host.h;S=host.S
try:
 active=json.loads((S/'hot_updates/active.json').read_text('utf8'))
 spec=importlib.util.spec_from_file_location('current_business',(S/active['code']));business=importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
 volume=business.volume_data();write(R/'volume-before.json',volume)
 cfg=json.loads((R/'club_season_products.json').read_text('utf8'));manifest=json.loads((R/'all_item_icon_manifest.json').read_text('utf8'))
 sale={int(r['itemid']) for r in json.loads((R/'live-sale-audit.json').read_text('utf8')) if r['itemid'] in h.PACKS}
 children={int(i) for track in volume.values() for p in track['packages'].values() for i,n in p['contents'] if i in h.PACKS}
 mapping={};review=[]
 font=ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc',16);small=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',12)
 for i in sorted(sale|children):
  pool=h.pack_pool(i);grades=[g for g,w in h.pack_grades(i) if w>0]
  if min(grades)>=8 or {s//1000000 for s,w in pool}=={84}:continue
  new=98632700+len(mapping);assert str(new) not in manifest['items'] and new not in h.PACKS
  old=h.item_def(i);choice=old.get('category')=='DRAFTPACK';weights=collections.defaultdict(list)
  for s,w in pool:
   if w>0:weights[float(w)].append(int(s))
  tiers=[dict(name='保留原球员概率组'+str(k+1),weight=w*len(spids),pool=sorted(spids)) for k,(w,spids) in enumerate(sorted(weights.items()))]
  band='+8' if choice else '+8～+12'
  stem=re.sub(r'(?:固定)?\+\d+(?:[～~–-]\+?\d+)?','',old['name']).strip('· ')
  name=stem+'·'+band+'·新版'
  description=('从本期冻结名单任选1名，固定+8；取消不消耗。' if choice else '随机获得1名球员；保留原卡包逐球员概率。<BR>强化独立抽取：+8 50%、+9 25%、+10 15%、+11 8%、+12 2%。')+'<BR>本期具体球员名单冻结；已持有旧编号卡包仍按原规则兑现。'
  search={str(s):dict(team=0,league=0,name='') for s,w in pool}
  with h.closing(h._db()) as c:
   for s,t,l,en,zh in c.execute('select p.spid,p.teamid,p.leagueid,n.full_eng,z.full from players p join nameseng n on n.playerid=p.playerid left join nameschi z on z.playerid=p.playerid'):
    if str(s) in search:search[str(s)]=dict(team=t,league=l,name=(zh or '')+' '+en)
  cfg['strength_packs'][str(new)]=dict(name=name,mode='choice' if choice else 'random',description=description,tiers=tiers,grades=[0]*7+([1] if choice else [50,25,15,8,2]),price=1,search=search)
  cfg['limits'][str(new)]=copy.deepcopy(h.item_purchase_limit(i))
  cfg.setdefault('retired_sale_items',[]).append(i)
  if i not in sale:cfg.setdefault('chain_only_items',[]).append(new)
  icon=f'FO3N_{new}_V3';image=Image.new('RGBA',(170,120),(0,0,0,0));d=ImageDraw.Draw(image)
  d.rounded_rectangle((9,3,161,116),radius=10,fill='#26364d',outline='#d5b363',width=3)
  d.text((85,14),'高强球员包',font=font,anchor='mt',fill='#ffe4a5')
  title=stem[:9];d.text((85,43),title,font=small,anchor='mt',fill='white')
  d.text((85,69),'自选' if choice else '随机',font=font,anchor='mt',fill='#ffe4a5')
  d.rounded_rectangle((94,93,160,116),radius=4,fill='#edc66b');d.text((127,104),band,font=small,anchor='mm',fill='#3b2110')
  path=R/'icons'/(icon+'.png');image.save(path)
  manifest['items'][str(new)]=dict(itemid=new,icon=icon,filename=icon+'.png',sha256=sha(path),size=[170,120],name=name,grade_values=[8] if choice else list(range(8,13)),grade_badge=band,grade_mode='固定' if choice else '随机',source_type='Code-native high-grade pack UI',composition='Frozen family title, mode and explicit grade band')
  mapping[i]=new;review.append(dict(old=i,new=new,old_name=old['name'],name=name,old_grades=h.pack_grades(i),new_grades=cfg['strength_packs'][str(new)]['grades'],sale=i in sale,chain=i in children,pool_size=len(pool)))
 cfg['retired_sale_items']=sorted(set(cfg.get('retired_sale_items',[])))
 cfg['chain_only_items']=sorted(set(cfg.get('chain_only_items',[])))
 write(R/'club_season_products.json',signed(cfg));write(R/'all_item_icon_manifest.json',manifest);write(R/'upgrade-mapping.json',{str(k):v for k,v in mapping.items()});write(R/'upgrade-review.json',review)
 baseline=json.loads((R/'baseline.json').read_text('utf8'));baseline[str(S/'hot_updates/active.json')]=sha(S/'hot_updates/active.json');baseline[str(S/active['code'])]=sha(S/active['code']);write(R/'baseline.json',baseline)
 print(json.dumps(dict(new_versions=len(mapping),sale=sum(x['sale'] for x in review),chain=sum(x['chain'] for x in review),legacy_issued_definitions_preserved=True)))
finally:host.close()
