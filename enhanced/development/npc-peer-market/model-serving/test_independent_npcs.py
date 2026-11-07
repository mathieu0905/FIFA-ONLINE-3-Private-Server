from pathlib import Path
import copy,gzip,hashlib,json,sys,tempfile,types
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from market_price_store import initialize
from npc_exchange import NpcExchange,MAX_VISIBLE_LISTINGS,AGENTS,INITIAL_WALLET
from market_simulation import Market
TMP=P/'tmp';TMP.mkdir(exist_ok=True);checks=[]
def check(v,s):assert v,s;checks.append(s)
with tempfile.TemporaryDirectory(prefix='npc-independent-',dir=TMP) as temp:
 root=Path(temp).resolve();assert root.is_relative_to(TMP.resolve());rows=[[i,100000] for i in range(101,501)];seed=root/'seed.gz';db=root/'prices.sqlite'
 with gzip.open(seed,'wt',encoding='utf8') as f:json.dump(dict(schema=1,price_region='kr',model_sha256='0'*64,seed_prices_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),rows=rows),f)
 initialize(db,seed,'npc-unit')
 m=Market.__new__(Market);m.h=types.SimpleNamespace(HERE=str(root),MARKET_PRICE_DB_PATH=db);m.reference=lambda spid,g:100000*(1090 if g==8 else 1)
 m.exchange=NpcExchange(m);m.exchange.profile=lambda spid:{f:80 for f in ('acceleration','sprintspeed','agility','ballcontrol','dribbling','shortpassing','strength','headingaccuracy','jumping','standingtackle','interceptions','stamina')}
 public=[dict(spid=i,grade=8,price=109000000,count=1) for i in range(101,151)];original_public=copy.deepcopy(public)
 m.featured_rows=lambda st,stamp,limit:public
 def no_public_book(*args,**kwargs):raise AssertionError('NPC must not buy public book inventory')
 m.book=no_public_book;m.quote=lambda spid,grade=1,st=None:100000*(1090 if grade==8 else 1)
 st={'coaches':[{'slot':0,'name':'temporary fixture'}],'teams':{'0':{'players':[{'_id':'fixture','spid':101,'experience':999,'grade':8}]}},'balance':123456,'market_simulation':{'seed':'npc-independent-unit','sales':[],'quotes':{},'price_events':[]}}
 assets=copy.deepcopy({k:v for k,v in st.items() if k!='market_simulation'})
 for i in range(300):
  m.exchange.advance(st,i*15);w=st['market_simulation']['npc_exchange'];owned=sum(m.exchange.quantity(a) for a in w['assets'].values())
  assert owned==w['internal_source_buys']-w['consumed_cards']-w['human_buys']
  assert len(m.exchange.listings(st,i*15))<=MAX_VISIBLE_LISTINGS
  assert all(m.exchange.quantity(a)>=1 and (a.get('listing') is None or m.exchange.quantity(a)>=1) for a in w['assets'].values())
 check(public==original_public,'300 simulation ticks never change public supply count or price')
 check(owned>192,'NPC warehouse grows beyond the former 192-card cap')
 check(max(m.exchange._counts(w).values())>12,'individual NPC can hold more than twelve cards')
 check(w['peer_trades']>0,'actual funded NPC peer trades continue')
 check(w['consumed_cards']>0,'simulated fusion/enhancement consumes NPC inventory')
 check(sum(a['wallet'] for a in w['agents'])+w['supplier_wallet']+w['fees']-w['simulated_income']==AGENTS*INITIAL_WALLET,'all NPC cash movements balance including explicit external income')
 check(all(x.get('buyer')!=x.get('seller') for x in st['market_simulation']['sales']),'price discovery receives cross-owner trades only')
 frozen={k:a['listing'] for k,a in w['assets'].items() if a.get('listing') is not None and a['listed_at']>4485-240}
 m.exchange.advance(st,4500)
 check(all(k in w['assets'] and w['assets'][k].get('listing') is row for k,row in frozen.items()),'NPC trading and consumption cannot remove reserved player-visible offers')
 key=next(k for k,a in w['assets'].items() if a.get('listing') is not None);a=w['assets'][key];a['quantity']=10000;before=m.exchange.quantity(a);row=a['listing'];owner=a['owner'];wallet=w['agents'][owner]['wallet'];fee=row['price']//100
 m.exchange.human_purchase(st,row,4501)
 check(m.exchange.quantity(w['assets'][key])==before-1,'player purchase removes exactly one reserved unit from a bulk lot')
 check(w['agents'][owner]['wallet']==wallet+row['price']-fee,'player purchase credits the NPC seller once')
 check(m.exchange.quantity(w['assets'][key])==9999,'large warehouse quantity is retained without truncation')
 check({k:v for k,v in st.items() if k!='market_simulation'}==assets,'NPC simulation never mutates player cards, experience or balance')
 status=m.exchange.status(st,4501);check(status['inventory_cap'] is None and status['public_pool_purchases_since_v2']==0,'status exposes independent unbounded warehouse policy')
 m.exchange.price_store.close()
report=dict(status='PASS',checks=len(checks),details=checks,simulation_ticks=300,real_state_written=False)
(P/'independent-npc-regression.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report,indent=2))
