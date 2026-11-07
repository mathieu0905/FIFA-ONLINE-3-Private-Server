"""Read-only public FO3 source audit; preserves individual region quotes and evidence."""
from pathlib import Path
import collections, datetime, hashlib, html, json, re, time, urllib.request

P=Path(__file__).resolve().parent
C=P/'source-pages'; C.mkdir(parents=True,exist_ok=True)
BASE='https://en.fifaaddict.com/fo3db.php?q=player'
SEASONS='2006,ucl2006,wc2006,2007,2008,eu2008,2009,2010,ucl2010,wc2010,2011,2014,wc2014,tots2014,2015,2016,2017,16ec,16th,wb,wl,ub,ul,el,lp,cp,cc,17th,tco92,mufclegend,ml,tl,vl,cl,kl2002,cel,u23,kxi,mul,vs'.split(',')
POSITIONS='st,cf,lf,rf,lw,rw,cam,cm,cdm,lm,rm,gk,cb,sw,lb,rb,lwb,rwb'.split(',')
AGES=['15-20','21-22','23-24','25-26','27-28','29-30','31-33','34-50']
ROW=re.compile(r'<tr id="player_id(\d+)" class="player-row">(.*?)</tr>',re.S)
PRICE=re.compile(r'stat_cell_price_(kr|th|vn|sg|id)">\s*(\d+)\s*<')
STAT=re.compile(r'stat_cell([2-7]) stat_value" rel="(\d+)"')
FIELDS={3:'finishing',4:'sprintspeed',5:'strength',6:'dribbling',7:'stamina'}
last=0.; quotes={}; pages=[]; inconsistent=[]; saturated=[]
historical=json.loads((P.parent/'historical-data.json').read_text('utf8'))
targets={r['spid']:r for r in historical};code_seasons={}
POSITION_CODES='gk,sw,rwb,rb,cb,cb,cb,lb,lwb,cdm,cdm,cdm,rm,cm,cm,cm,lm,cam,cam,cam,rf,cf,lf,rw,st,st,st,lw'.split(',')
def needed(code,age_range,position=None):
 seasons=code_seasons.get(code)
 if seasons is None:return True
 lo,hi=age_range
 for spid,r in targets.items():
  if spid in quotes or spid//1000000 not in seasons:continue
  if position is not None and 0<=r['preferredposition1']<len(POSITION_CODES) and POSITION_CODES[r['preferredposition1']]!=position:continue
  try:
   born=datetime.datetime.strptime(r['birthdate'].split(' ')[0],'%m/%d/%Y').date();today=datetime.datetime.now(datetime.timezone.utc).date()
   # Verified against cached single-age source rows, including birthdays later
   # in the year: the site's age filter uses completed years, not birth year.
   age=today.year-born.year-((today.month,today.day)<(born.month,born.day))
   if lo<=age<=hi:return True
  except (ValueError,KeyError):return True
 return False

def fetch(url):
 global last
 stem=hashlib.sha256(url.encode()).hexdigest(); f=C/(stem+'.html'); m=C/(stem+'.json')
 if f.exists() and m.exists():return f.read_text('utf8'),json.loads(m.read_text('utf8'))
 for attempt in range(3):
  time.sleep(max(0,2-(time.monotonic()-last)))
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (FO3 historical database audit)'})
   with urllib.request.urlopen(req,timeout=60) as response:body=response.read().decode('utf8','replace')
   last=time.monotonic()
   if 'player-row' not in body and 'fo3' not in body.lower():raise ValueError('unexpected page')
   info=dict(url=url,retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(body.encode()).hexdigest(),file=str(f))
   f.write_text(body,'utf8');m.write_text(json.dumps(info,indent=2),'utf8');return body,info
  except Exception as e:
   last=time.monotonic();print('RETRY',attempt,url,repr(e),flush=True);time.sleep(3*(attempt+1))
 raise RuntimeError('Unable to collect '+url)

def walk(params,depth=0,age_range=(0,99)):
 if depth and not needed(params[0][1],age_range,dict(params).get('position')):return
 url=BASE+''.join('&'+k+'='+v for k,v in params)+'&limit=500'
 body,info=fetch(url); rows=ROW.findall(body);pages.append(dict(info,rows=len(rows)))
 if depth==0:code_seasons[params[0][1]]={int(spid)//1000000 for spid,row in rows}
 for spid,row in rows:
  spid=int(spid);prices={k:int(v) for k,v in PRICE.findall(row)}
  stats={FIELDS[int(k)]:int(v) for k,v in STAT.findall(row) if int(k) in FIELDS}
  ovr=dict(STAT.findall(row)).get('2')
  name=re.search(r'<span class="label_lg">(.*?)</span>',row,re.S)
  item=dict(spid=spid,season_code=params[0][1],prices=prices,summary_attributes=stats,position_overall=int(ovr) if ovr else None,name=html.unescape(name.group(1)) if name else None,limited=bool(re.search(r'\bLimited\b|player_limited|player_limit',row)),source_url=url,source_sha256=info['sha256'],retrieved_at=info['retrieved_at'])
  if spid in quotes:
   old=quotes[spid]
   if old['prices']!=prices or old['summary_attributes']!=stats:inconsistent.append(dict(spid=spid,old=old,new=item))
  quotes[spid]=item
 print('PAGE',params,'rows',len(rows),'unique',len(quotes),flush=True)
 if len(rows)>=500 and needed(params[0][1],age_range,dict(params).get('position')):
  lo,hi=age_range
  if lo<hi:
   mid=(lo+hi)//2
   # Disjoint age partitions avoid the 18 overlapping-position queries and
   # include retired players older than the previous collector's age-50 cap.
   for a,b in ((lo,mid),(mid+1,hi)):
    child=[(k,v) for k,v in params if k!='age']+[('age',f'{a}-{b}')]
    walk(child,depth+1,(a,b))
  elif not any(k=='position' for k,v in params):
   for position in POSITIONS:walk(params+[('position',position)],depth+1,age_range)
  else:saturated.append(url)

if __name__=='__main__':
 for season in SEASONS:walk([('season',season)])
 out=dict(schema=1,region_policy='Keep raw native EP quotes separately; no conversion, imputation or cross-region fallback',quote_time_policy='Retrieval time only; source exposes no per-card quote timestamp',collection_scope='Refresh the historical training cohort; capped queries are partitioned by age, then position; branches with no remaining target cards are pruned. Other cards are incidental coverage, not an exhaustive public-database claim.',historical_cohort_size=len(targets),historical_cohort_observed=sum(s in quotes for s in targets),historical_cohort_missing=[s for s in targets if s not in quotes],quotes=list(quotes.values()),pages=pages,inconsistent_observations=inconsistent,saturated_leaf_queries=saturated,coverage={r:sum(q['prices'].get(r,0)>0 for q in quotes.values()) for r in ('id','kr','th','vn','sg')})
 (P/'regional-source.json').write_text(json.dumps(out,ensure_ascii=False),'utf8')
 print('DONE',json.dumps(dict(cards=len(quotes),pages=len(pages),coverage=out['coverage'],conflicts=len(inconsistent),saturated=len(saturated))),flush=True)
