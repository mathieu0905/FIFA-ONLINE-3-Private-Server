"""Full current roster replay, strict attribute tests and cross-season gaps."""
from pathlib import Path
import collections,gzip,hashlib,json,math,sqlite3
import fair_value_model as m
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def save(name,v):(P/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 config=json.loads((P/'model.json').read_text('utf8'));database=S/'gamedata/fifadb.sqlite';before=hashlib.sha256(database.read_bytes()).hexdigest()
 raw=m.catalogue_rows(database,config);cat=m.build_catalogue(database,config);byid={r['spid']:r for r in cat['rows']};fields=m.fields(config)
 with gzip.open(P/'catalogue.json.gz','wt',encoding='utf8') as f:json.dump(cat,f,ensure_ascii=False,separators=(',',':'))
 checks=0;failures=[];weights={field:[w.get(field,0)/sum(w.values()) for w in config['role_weights'].values()] for field in fields}
 for i,r in enumerate(raw):
  detail=byid[r['spid']];scores=list(m.role_scores(r,config).values());bonus=config['grade1_boost']+(r['weakfootabilitytypecode']-3)*config['weakfoot_score_per_star']+(min(4,r['skillmoves'])-2)*config['skill_score_per_star']
  for field in fields:
   if r[field]>=255:continue
   gain=1 if r[field]>=0 else 0
   score=max(old+gain*w for old,w in zip(scores,weights[field]))+bonus
   price=round(m.economic_curve(score,config)*detail['identity_factor'])+detail['strict_floor_ep']+1
   checks+=1
   if price<detail['fair_price_ep']+1:failures.append([r['spid'],field])
  for key,limit,step in [('weakfootabilitytypecode',5,config['weakfoot_score_per_star']),('skillmoves',4,config['skill_score_per_star'])]:
   if r[key]>=limit:continue
   price=round(m.economic_curve(detail['effective_score']+step,config)*detail['identity_factor'])+detail['strict_floor_ep']+25
   checks+=1
   if price<detail['fair_price_ep']+25:failures.append([r['spid'],key])
  if i%15000==0:print('AUDIT',i,len(raw),flush=True)
 assert not failures,failures[:10]
 groups=collections.defaultdict(list)
 for r in raw:
  if r['spid']>=1000000:groups[r['playerid']].append(r)
 dominance=0;gap_checks=0;inversions=[]
 for pid,cards in groups.items():
  for i,a in enumerate(cards):
   for b in cards[i+1:]:
    da,db=byid[a['spid']],byid[b['spid']];gap=abs(da['effective_score']-db['effective_score'])
    ratio=max(da['economic_value'],db['economic_value'])/min(da['economic_value'],db['economic_value']);gap_checks+=1
    assert math.log(ratio)<=.28*gap+1e-10,(a['spid'],b['spid'],gap,ratio)
    for h,l in [(a,b),(b,a)]:
     if h['weakfootabilitytypecode']<l['weakfootabilitytypecode'] or min(4,h['skillmoves'])<min(4,l['skillmoves']):continue
     if not all(h[k]>=l[k] for k in fields):continue
     if h['weakfootabilitytypecode']==l['weakfootabilitytypecode'] and min(4,h['skillmoves'])==min(4,l['skillmoves']) and all(h[k]==l[k] for k in fields):continue
     dh,dl=byid[h['spid']],byid[l['spid']];dominance+=1
     for factor in [.85,1.,1.15]:
      if round(dh['economic_value']*factor)+dh['strict_floor_ep']<=round(dl['economic_value']*factor)+dl['strict_floor_ep']:inversions.append([h['spid'],l['spid'],factor])
 assert not inversions,inversions[:10]
 with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;names={r[0]:r[1] for r in db.execute('select playerid,short from nameschi')};records={r['spid']:dict(r) for r in db.execute('select * from players')}
 with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:current=dict(db.execute('select spid,current_price from prices'))
 for detail in cat['rows']:detail['name']=names.get(detail['playerid'],str(detail['playerid']));detail['old_price_ep']=current.get(detail['spid'])
 examples=[]
 for pid in [250,121939,37576,214100,238380,20801,158023,167905,7289]:
  cards=[dict(r,display_ability=int(sum(records[r['spid']][k]*w for k,w in config['role_weights'][('GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split())[records[r['spid']]['preferredposition1']]].items())/100)+5) for r in cat['rows'] if r['playerid']==pid and r['spid']>=1000000]
  cards.sort(key=lambda r:-r['effective_score']);examples.append(dict(player=names.get(pid),cards=cards))
 assert hashlib.sha256(database.read_bytes()).hexdigest()==before,'Roster changed during audit; rebuild'
 result=dict(status='PASS',rows=len(raw),strict_checks=checks,strict_failures=failures,dominance_pairs=dominance,market_factors_checked=[.85,1,1.15],dominance_inversions=inversions,cross_season_gap_checks=gap_checks,maximum_economic_price_ratio_per_effective_point=math.exp(.28),same_player_5point_ratio_bound=math.exp(1.4),source_db_sha256=before,profile_sha256=cat['profile_sha256'],model_sha256=cat['model_sha256'],price_range=[min(r['fair_price_ep'] for r in cat['rows']),max(r['fair_price_ep'] for r in cat['rows'])],examples=examples,formal_activated=False)
 save('audit.json',result);save('preview-prices.json',cat['rows'])
 print(json.dumps({k:v for k,v in result.items() if k!='examples'},ensure_ascii=False))
 for e in examples:print('EXAMPLE',e['player'],[(r['spid'],round(r['effective_score'],2),r['old_price_ep'],r['fair_price_ep']) for r in e['cards'][:3]],flush=True)
 lines=['新定价v12：同人跨赛季关系（未激活）','主位置展示能力和有效能力分分别列出；基础价按统一多位置能力曲线，逆足/花式另计。','同一人有效能力相差1分，经济价值倍率至多exp(0.28)=1.323；高能力100分以上价格线性延伸。严格属性保底按每点至少1EP、每星至少25EP计算，不随行情折价。','行情因子同人所有赛季共用，范围0.85—1.15；姓名因子范围0.85—1.15。','','球员｜SPID｜展示能力｜有效能力分｜当前旧价EP｜新基础价EP']
 for e in examples:
  for r in e['cards']:lines.append(f"{e['player']}｜{r['spid']}｜{r['display_ability']}｜{r['effective_score']:.2f}｜{r['old_price_ep']}｜{r['fair_price_ep']}")
 (P/'同球员跨赛季价差.txt').write_text('\n'.join(lines)+'\n','utf8')

if __name__=='__main__':main()
