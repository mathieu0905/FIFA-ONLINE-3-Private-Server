from pathlib import Path
import sys,os,json,math,ast
sys.dont_write_bytecode=True
W=Path(r'D:\fifaol3\enhancement-progression');S=Path(r'D:\FO3ID\server')
def audit(e,a):
 if e=='open':
  p,m,f=a
  if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(f,int) and f&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))):
   if not Path(os.fsdecode(p)).resolve().is_relative_to(W):raise PermissionError('Read-only production analysis: '+str(p))
sys.addaudithook(audit)
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi');sys.path.insert(0,str(S));sys.argv=['http_config.py']
import http_config as h
ratings=h.card_ovrs(h.market_spids());by={}
for spid,ovr in ratings.items():by.setdefault(ovr,spid)
ranges=[]
for ovr,spid in sorted(by.items()):
 ranges.append(dict(ovr=ovr,spid=spid,plus1=h.player_value_price(spid,1),plus10=h.player_value_price(spid,10),plus20=h.player_value_price(spid,20)))
packs=[]
for itemid in h.PACKS:
 gs=[int(g) for g,w in h.pack_grades(itemid) if w>0]
 if max(gs,default=0)>13:packs.append(dict(itemid=itemid,max_grade=max(gs)))
st=h._state();owned=[(p['spid'],h.grade_of(p)) for t in st['teams'].values() for p in t['players']]
r=dict(ovr_prices=ranges,old_max_plus10=max(v['plus10'] for v in ranges),old_max_plus20=max(v['plus20'] for v in ranges),issued_packs_above13=packs,owned_cards=len(owned),owned_grade_max=max(g for s,g in owned),rates_saved=(S/'gamedata/enhancement_rates.json').is_file())
(W/'analysis.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
