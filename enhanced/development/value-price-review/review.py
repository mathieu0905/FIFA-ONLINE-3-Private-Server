"""Read-only current ability/price review. No game modules are imported."""
from pathlib import Path
from contextlib import closing
import ast,collections,datetime,gzip,hashlib,json,sqlite3,sys,urllib.request
S=Path('D:/FO3ID/server');W=Path('D:/fifaol3');P=Path(__file__).resolve().parent
V=W/'npc-peer-market/identity-anchor-v11'
sys.path.insert(0,str(V))
from predict import IdentityValueModel
from features import ability_fields

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def gz(p):
 with gzip.open(p,'rt',encoding='utf8') as f:return json.load(f)
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def money(n):
 if n>=100000000:return f'{n/100000000:.2f}亿'
 if n>=10000:return f'{n/10000:.2f}万'
 return f'{n:,}'
def main():
 out=P/datetime.datetime.now().strftime('review-%Y%m%d-%H%M%S');out.mkdir()
 baseline={str(p):sha(p) for p in [S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'http_config.py',S/'market_price_store.py',S/'npc_exchange.py']}
 tree=ast.parse((S/'http_config.py').read_text('utf8'));literal={}
 for n in tree.body:
  if isinstance(n,ast.Assign):
   for target in n.targets:
    if isinstance(target,ast.Name) and target.id in ['ROLE_WEIGHTS','FA_SEASONS']:literal[target.id]=ast.literal_eval(n.value)
 weights=literal['ROLE_WEIGHTS'];roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 season_names={7:'07'}
 for label,codes,_ in literal['FA_SEASONS']:
  for code in codes:season_names[code]=label
 registry=read(S/'gamedata/custom_rosters.json')
 for row in registry['seasons']:season_names[row['id']]=row['label']
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row
  raw={r['spid']:dict(r) for r in db.execute('select p.*,n.short as name_zh,n.full_eng as name_en from players p left join nameschi n using(playerid)')}
  eligible={r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m USING(spid) WHERE m.transferable=1 AND p.spid>=1000000 AND p.playerid IN(SELECT playerid FROM namesind)')}
 eligible|={int(x) for x in read(S/'gamedata/fa_prices.json')}
 # A coherent SQLite read transaction; there is no write to the live database.
 with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.execute('begin');prices={r[0]:dict(current=r[1],basis=r[2],last_event=r[3]) for r in db.execute('select spid,current_price,basis_price,last_event from prices')}
  meta=dict(db.execute('select key,value from metadata'))
  calibration={r[0]:r[1] for r in db.execute("select spid,after_price from price_events where reason='model_recalibration' and event_id like 'valuation:identity-anchor-v11-mul63:%'")}
  event_count=db.execute('select count(*) from price_events').fetchone()[0]
 model=IdentityValueModel(expected_sha256=meta['valuation_model_sha256']);fields=ability_fields(model.config)
 previous={r['spid']:r for r in gz(V.with_name('anchor-retraining-v10')/'current-profiles.json.gz')}
 state=read(S/'gamedata/state.json');quotes=state.get('market_simulation',{}).get('quotes',{})
 rows=[];missing=[];changed=[]
 for sid in sorted(eligible):
  if sid<1000000 or sid not in raw:continue
  r=raw[sid];role=roles[r['preferredposition1']];native=sum(r[k]*v for k,v in weights[role].items())/100
  if sid not in prices:missing.append(sid);continue
  q=quotes.get(str(sid),{}).get('basis_price');effective=round(q) if q is not None else prices[sid]['current']
  delta=[k for k,v in previous.get(sid,{}).items() if r.get(k)!=v]
  row=dict(spid=sid,playerid=r['playerid'],name=r['name_zh'] or r['name_en'] or str(r['playerid']),season_id=sid//1000000,
           season=season_names.get(sid//1000000,str(sid//1000000)),role=role,ability=int(native)+5,native_primary=native,
           current_price_ep=effective,stored_price_ep=prices[sid]['current'],calibrated_price_ep=calibration.get(sid),
           weakfoot=r['weakfootabilitytypecode'],skill_stars=min(4,r['skillmoves'])+1,
           attributes_changed_since_v11=bool(delta),new_since_v11=sid not in previous,changed_fields=delta,
           last_price_event=prices[sid]['last_event'])
  if delta:
   row['same_model_recomputed_ep']=model.predict(r);row['recomputed_to_current_ratio']=row['same_model_recomputed_ep']/max(1,effective);changed.append(row)
  rows.append(row)
 rows.sort(key=lambda r:(-r['ability'],-r['current_price_ep'],r['spid']))
 grouped=collections.defaultdict(list)
 for r in rows:grouped[r['playerid']].append(r)
 dominance=[];pairs=0;ovr_inversions=[]
 for pid,cards in grouped.items():
  for i,a in enumerate(cards):
   for b in cards[i+1:]:
    if a['ability']>b['ability'] and a['current_price_ep']<b['current_price_ep']:
     ovr_inversions.append(dict(player=a['name'],higher=a,lower=b,price_ratio=b['current_price_ep']/max(1,a['current_price_ep'])))
    for high,low in [(a,b),(b,a)]:
     h,l=raw[high['spid']],raw[low['spid']]
     if high['weakfoot']<low['weakfoot'] or high['skill_stars']<low['skill_stars']:continue
     if not all(h[k]>=l[k] for k in fields):continue
     if high['weakfoot']==low['weakfoot'] and high['skill_stars']==low['skill_stars'] and all(h[k]==l[k] for k in fields):continue
     pairs+=1
     if high['current_price_ep']<low['current_price_ep']:
      dominance.append(dict(higher=high,lower=low,price_ratio=low['current_price_ep']/max(1,high['current_price_ep'])))
 dominance.sort(key=lambda r:-r['price_ratio']);ovr_inversions.sort(key=lambda r:-r['price_ratio'])
 bands=[]
 for ability,cards in sorted(collections.defaultdict(list,{}).items()):pass
 by_ability=collections.defaultdict(list)
 for row in rows:by_ability[row['ability']].append(row)
 for ability,cards in sorted(by_ability.items(),reverse=True):
  ps=sorted(r['current_price_ep'] for r in cards)
  bands.append(dict(ability=ability,cards=len(cards),minimum=ps[0],median=ps[len(ps)//2],maximum=ps[-1],spread=ps[-1]/max(1,ps[0])))
 probes=[]
 for sid in [84000250,84121939,84037576,84214100,84238380,48167905]:
  with urllib.request.urlopen('http://127.0.0.1:8088/api/market_price_store?spid='+str(sid)+'&grade=1',timeout=15) as response:probe=json.load(response)
  r=next(x for x in rows if x['spid']==sid);probes.append(dict(spid=sid,snapshot_ep=r['current_price_ep'],live_value=probe['value'],live_stored=probe['current_price'],active_model=probe['active_valuation_model_sha256']))
 assert baseline=={p:sha(p) for p in baseline},'Inputs changed during audit; retry snapshot'
 result=dict(at=datetime.datetime.now().astimezone().isoformat(),scope='Current eligible cards, primary-position native integer rating +5 for level1/grade1, no team colour/season feature/level/enhancement beyond grade1. Price is current base reference, not an outstanding listing ask.',
             eligible_cards=len(rows),missing_prices=missing,market_metadata=meta,event_count=event_count,top30=rows[:30],
             changed_since_v11=len(changed),changed_by_season=dict(collections.Counter(r['season'] for r in changed)),
             stale_recomputed_above_2x=sum(r['recomputed_to_current_ratio']>=2 for r in changed),
             stale_recomputed_below_half=sum(r['recomputed_to_current_ratio']<=.5 for r in changed),
             changed_cards=sorted(changed,key=lambda r:-r['recomputed_to_current_ratio']),bands=bands,
             same_player_attribute_dominance_pairs=pairs,strict_dominance_inversions=len(dominance),worst_dominance_inversions=dominance[:30],
             same_player_primary_rating_inversions=len(ovr_inversions),worst_primary_rating_inversions=ovr_inversions[:20],
             live_probes=probes,input_hashes=baseline,formal_written=False,game_actions=False)
 save(out/'review.json',result);save(out/'all-cards.json',rows)
 lines=['当前卡价按能力降序（只读快照）',result['at'],'口径：1级＋1、主位置整数能力；含＋1的5点强化加成，不含等级/队色/赛季组合加成。','价格为当前身价/行情参考EP，不是既有挂单合同价。同分再按价格降序排列。','','序号｜能力｜赛季｜球员｜位置｜当前价EP｜原生主位置精确值｜SPID']
 for i,r in enumerate(rows,1):lines.append(f"{i}｜{r['ability']}｜{r['season']}｜{r['name']}｜{r['role']}｜{money(r['current_price_ep'])}（{r['current_price_ep']:,}）｜{r['native_primary']:.2f}｜{r['spid']}")
 (out/'能力降序与当前卡价.txt').write_text('\n'.join(lines)+'\n','utf8')
 lines=['属性已改变但价格未同步：同一v11模型现属性重算对照（不是已修改价格）','球员｜能力｜当前价｜现属性重算｜差额倍率｜SPID']
 for r in result['changed_cards']:lines.append(f"{r['name']}｜{r['ability']}｜{money(r['current_price_ep'])}｜{money(r['same_model_recomputed_ep'])}｜{r['recomputed_to_current_ratio']:.2f}｜{r['spid']}")
 (out/'123张变更属性与旧价格对照.txt').write_text('\n'.join(lines)+'\n','utf8')
 save(P/'latest-review.json',dict(path=str(out),formal_written=False))
 print(json.dumps({k:result[k] for k in ['eligible_cards','changed_since_v11','changed_by_season','stale_recomputed_above_2x','stale_recomputed_below_half','same_player_attribute_dominance_pairs','strict_dominance_inversions','same_player_primary_rating_inversions','live_probes']},ensure_ascii=False))
 print('TOP_CHANGED',json.dumps(result['changed_cards'][:5],ensure_ascii=False));print('DOMINANCE',json.dumps(dominance[:3],ensure_ascii=False));print('OUTPUT',str(out))

if __name__=='__main__':main()
