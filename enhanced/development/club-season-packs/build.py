"""Prepare six frozen random season packs using the current formal price model."""
from pathlib import Path
import copy,hashlib,json,math,os,sys
from decimal import Decimal,ROUND_CEILING
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(R/'deps'),str(S)];sys.dont_write_bytecode=True
os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and args[2]&0x243 and not Path(os.fsdecode(args[0])).resolve().is_relative_to(R):raise RuntimeError('Build write outside work resources')
 if event in ('socket.bind','socket.connect'):raise RuntimeError('Build cannot start/contact a service')
sys.addaudithook(guard)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,events:0
import http_config as h
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[S/'product_packs.py',S/'gamedata/fifadb.sqlite',S/'gamedata/all_item_icon_manifest.json',S/'draw_first_rules.json',S/'pack_value.py']+list((S/'gamedata').glob('*products.json'))+[S/'gamedata/all_pack_expected_prices.json']
baseline={str(p):sha(p) for p in paths};coefficient=h.product_packs['valuation']['points_per_ep'];cfg=dict(schema=1,edition='manutd67-wonderkid40-surprise-strength-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},value_prices={})
icons=json.loads((S/'gamedata/all_item_icon_manifest.json').read_text('utf8'));oldicons=copy.deepcopy(icons);products=[]
for season,label,count,root in [(48,'曼联传奇',67,98448000),(18,'神童',40,98418000)]:
 with h._db() as db:pool=sorted(p[0] for p in db.execute('select spid from players where spid/1000000=?',(season,)))
 assert len(pool)==count and set(pool)<=h.market_spids()
 for suffix,title,weights,limit,period in [(81,'惊喜强化+8～+12',{8:50,9:25,10:15,11:8,12:2},100,'day'),(82,'高阶惊喜+10～+15',{10:50,11:25,12:12,13:7,14:4,15:2},30,'day'),(10,'限量固定+10',{10:100},3,'week')]:
  itemid=root+suffix;assert itemid not in set(h.PACKS)|set(h.PACKAGES)|set(h.ITEMS)|set(h.MONTHLY)
  grade=max(weights);grades=[weights.get(g,0) for g in range(1,grade+1)];assert sum(grades)==100
  expected=math.fsum(h.player_value_price(s,g)*weight for s in pool for g,weight in weights.items())/(len(pool)*100);assert expected>0
  ceiling=lambda factor:int((Decimal(str(expected))*Decimal(str(coefficient))*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
  standard=max(3,ceiling(1));quotes=dict(ordinary=standard,chain=min(standard-1,max(2,ceiling(.65))),once=min(standard-2,max(1,ceiling(.45))))
  odds='、'.join(f'+{g}：{weight}%' for g,weight in weights.items());name=f'{label}·{title}'
  description=f'随机获得1名{label}赛季球员。<BR>强化概率：{odds}。<BR>本期冻结{count}人，逐卡等概率，每人1/{count}；球员与强化独立抽取，不能指定球员，无指定球员保底。<BR>'+('每日' if period=='day' else '每周')+f'限购{limit}包。'
  cfg['limits'][str(itemid)]=dict(period=period,count=limit)
  cfg['strength_packs'][str(itemid)]=dict(name=name,description=description,mode='random',price=standard,grades=grades,tiers=[dict(name=f'{label}·{count}人冻结卡池',weight=100,pool=pool)])
  cfg['value_prices'][str(itemid)]=dict(expected_ep=expected,standard_points=expected*coefficient,quotes=quotes,kind='ordinary',price=standard,bp_per_point=1/coefficient)
  # Reuse an installed native pack image. No client image replacement is needed.
  candidates=[]
  for candidate in h.PACKS:
   support=[g for g,w in h.pack_grades(candidate) if w>0]
   if support==sorted(weights) and str(candidate) in icons['items']:
    n=h.item_def(candidate)['name'];rank=(0 if '全赛季' in n else 1 if '精选' in n else 2,candidate);candidates.append((rank,candidate))
  donor=min(candidates)[1] if candidates else 98248008
  icon=copy.deepcopy(icons['items'][str(donor)]);icon['itemid']=itemid;icons['items'][str(itemid)]=icon
  products.append(dict(id=itemid,name=name,season=season,pool_size=count,grades=weights,price=standard,expected_bp=expected,bp_per_point=1/coefficient,limit=limit,period=period,icon_source=donor))
native=R.parent/'item-icons/native-style';ns={'__file__':str(native/'build.py')};exec(compile((native/'build.py').read_text('utf8').split('\nitems={}')[0],str(native/'build.py'),'exec'),ns)
iconout=R/'icons';iconout.mkdir(exist_ok=True)
for p in products:
 row=dict(id=p['id'],kind='pack',definition=cfg['strength_packs'][str(p['id'])],grades=sorted(map(int,p['grades'])))
 image,source,theme,badge,mode=ns['build'](row);key=f'FO3N_{p["id"]}_V3';dest=iconout/(key+'.png');image.save(dest)
 icons['items'][str(p['id'])]=dict(itemid=p['id'],icon=key,filename=dest.name,sha256=sha(dest),size=[170,120],name=p['name'],theme=theme,source_path=str(source),source_sha256=sha(source),source_type='Existing native artwork; code-native season and grade labels',grade_values=row['grades'],grade_badge=badge,grade_mode=mode)
cfg['hash']=h.product_packs_signature(cfg) if hasattr(h,'product_packs_signature') else __import__('product_packs').signature(cfg)
write(R/'club_season_products.json',cfg);write(R/'all_item_icon_manifest.json',icons)
source=(S/'product_packs.py').read_text('utf8');needle="'reward_upgrade_products.json')";assert source.count(needle)==1
source=source.replace(needle,"'reward_upgrade_products.json','club_season_products.json')");compile(source,'product_packs.py','exec');(R/'product_packs.py').write_text(source,encoding='utf8')
legacy={str(i):dict(pool=h.pack_pool(i),grades=h.pack_grades(i),category=h.item_def(i)['category']) for i in h.PACKS};write(R/'legacy.json',legacy)
for p,digest in baseline.items():assert sha(Path(p))==digest,('Concurrent build source changed',p)
outputs={p.name:sha(p) for p in (R/'club_season_products.json',R/'product_packs.py',R/'all_item_icon_manifest.json')};outputs.update({str(p.relative_to(R)).replace('\\','/'):sha(p) for p in iconout.glob('*.png')})
write(R/'build.json',dict(status='BUILT',baseline=baseline,outputs=outputs,products=products,points_per_bp=coefficient,prior_pack_count=len(legacy),existing_icons_unchanged=all(icons['items'][k]==v for k,v in oldicons['items'].items()),real_assets_written=False))
print(json.dumps(dict(products=products,old_packs=len(legacy)),ensure_ascii=True))
