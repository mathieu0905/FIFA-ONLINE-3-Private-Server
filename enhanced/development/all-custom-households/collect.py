"""Collect auditable careers for every registered custom identity, never formal files."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import defaultdict,Counter
import datetime,difflib,gzip,hashlib,importlib.util,json,re,sqlite3,sys,time,unicodedata,urllib.request
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');OLD=Path('D:/fifaol3/club-history');RECENT=Path('D:/fifaol3/team-balance-household/sources/refreshed');SRC=P/'sources';SRC.mkdir(exist_ok=True);(SRC/'careers').mkdir(exist_ok=True);sys.dont_write_bytecode=True
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def read(p):return json.loads(Path(p).read_text('utf8'))
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def date(s):
 m,d,y=map(int,s.split(' ')[0].split('/'));return f'{y:04}-{m:02}-{d:02}'
def fetch(url,path):
 if path.exists():return read(path)
 for attempt in range(3):
  try:
   raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 FO3-career-eligibility-audit/1.0'}),timeout=25).read();value=json.loads(raw);path.write_bytes(raw);return value
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)
def main():
 registry=read(S/'gamedata/custom_rosters.json');pids=sorted({c['base_playerid'] for c in registry['cards']});db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;people=[]
 for pid in pids:
  rows=[dict(r) for r in db.execute('select p.playerid,p.birthdate,p.nationality,p.teamid,n.full_eng,n.short_eng from players p join nameseng n using(playerid) where p.playerid=?',(pid,))];assert rows
  identities={(date(r['birthdate']),r['nationality']) for r in rows}
  if pid>=700000:assert len(identities)==1,('Conflicting custom identity',pid,identities)
  dob,nation=sorted(identities)[0];cards=[c for c in registry['cards'] if c['base_playerid']==pid];people.append(dict(playerid=pid,birthdate=dob,nation=nation,original_identity_variants=sorted(identities),names=sorted({r['full_eng'] for r in rows if r['full_eng']}|{r['short_eng'] for r in rows if r['short_eng']}|{c['name_en'] for c in cards if c.get('name_en')}),custom_cards=[c['fo3_spid'] for c in cards],current_teams=sorted({r['teamid'] for r in rows if r['teamid']>0})))
 db.close();write(SRC/'people.json',people)
 # EA's official English identities bridge custom700xxx IDs to exact Nexon IDs.
 base='https://drop-api.ea.com/rating/ea-sports-fc?locale=en&limit=100&offset='
 first=fetch(base+'0',SRC/'ea-0.json');total=first['totalItems'];pages={0:first}
 def page(offset):return offset,fetch(base+str(offset),SRC/f'ea-{offset}.json')
 with ThreadPoolExecutor(max_workers=5) as pool:
  futures=[pool.submit(page,n) for n in range(100,total,100)]
  for future in as_completed(futures):
   offset,data=future.result();pages[offset]=data
 print('EA_IDENTITIES',sum(len(p['items']) for p in pages.values()),flush=True)
 ea_by_birth=defaultdict(dict)
 for page in pages.values():
  for p in page['items']:
   if p.get('gender',{}).get('id')!=0:continue
   ea_by_birth[(date(p['birthdate']),p['nationality']['id'])][int(p['id'])]=p
 metadata=read(Path('D:/fifaol3/team-balance-household/sources/spid-current.json'));choices=defaultdict(list)
 for row in metadata:choices[row['id']%1000000].append(row)
 links=[]
 for person in people:
  pid=person['playerid'];source=pid if pid<700000 else None;matches=[]
  if source is None:
   for eid,p in ea_by_birth.get((person['birthdate'],person['nation']),{}).items():
    names={p.get('commonName') or '',(p.get('firstName') or '')+' '+(p.get('lastName') or ''),p.get('lastName') or ''};scores=[]
    for a in person['names']:
     for n in names:
      if not n:continue
      an,bn=norm(a),norm(n);score=difflib.SequenceMatcher(None,an,bn).ratio()
      if an==bn:score=1.
      # Explicit initial+surname abbreviation, corroborated by exact DOB+country.
      words=a.replace('.',' ').split()
      if len(words)>=2 and len(words[0])==1 and norm(words[-1])==norm(p.get('lastName') or '') and norm(p.get('firstName') or '').startswith(norm(words[0])):score=1.
      scores.append(score)
    score=max(scores or [0])
    if score>=.90:matches.append((score,eid,p))
   matches.sort(key=lambda r:(-r[0],r[1]))
   if matches and (len(matches)==1 or matches[0][0]>matches[1][0]+.05):source=matches[0][1]
  link=dict(**person,source_playerid=source,identity_basis='existing exact EA identity' if pid<700000 else 'official EA exact date-of-birth and nationality plus reviewed full/abbreviated name',candidates=[dict(id=eid,score=score,name=(p.get('firstName') or '')+' '+(p.get('lastName') or '')) for score,eid,p in matches]);links.append(link)
 write(SRC/'identity-links.json',links);print('IDENTITY_LINKS',dict(Counter('LINKED' if p['source_playerid'] is not None else 'UNRESOLVED' for p in links)),flush=True)
 spec=importlib.util.spec_from_file_location('career_parser',OLD/'collect.py');parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 def career(link):
  pid=link['playerid'];eid=link['source_playerid'];dest=SRC/'careers'/f'{pid}.json'
  if dest.exists() and read(dest).get('status')=='OK':return read(dest)
  if eid is None:result=dict(status='IDENTITY_UNRESOLVED',playerid=pid)
  else:
   cached=next((read(path) for path in (RECENT/f'{eid}.json',OLD/'records'/f'{eid}.json') if path.exists() and read(path).get('status')=='OK'),None)
   if cached:result={**cached,'playerid':pid,'source_playerid':eid,'identity_link':link};write(dest,result);return result
   result=dict(status='NO_EXACT_SOURCE' if not choices[eid] else 'FETCH_FAILED',playerid=pid,source_playerid=eid,errors=[])
   for candidate in sorted(choices[eid],key=lambda p:p['id'],reverse=True)[:3]:
    url='https://fconline.nexon.com/DataCenter/PlayerInfo?spid='+str(candidate['id'])
    try:
     raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read();rows=parser.parse(raw.decode('utf-8-sig'));assert rows
     path=SRC/'careers'/f'{pid}.html.gz';path.write_bytes(gzip.compress(raw,mtime=0));result=dict(status='OK',playerid=pid,source_playerid=eid,source_spid=candidate['id'],url=url,name_ko=candidate['name'],career=rows,raw_sha256=hashlib.sha256(raw).hexdigest(),raw_file=str(path),fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity_link=link);break
    except Exception as e:result['errors'].append(str(e))
  write(dest,result);return result
 counts=Counter()
 with ThreadPoolExecutor(max_workers=5) as pool:
  futures=[pool.submit(career,p) for p in links]
  for index,future in enumerate(as_completed(futures),1):
   result=future.result();counts[result['status']]+=1
   if index%100==0:print('CAREERS',index,dict(counts),flush=True)
 summary=dict(registered_cards=len(registry['cards']),unique_players=len(people),ea_identity_count=sum(len(p['items']) for p in pages.values()),outcomes=dict(counts),formal_files_written=False);write(SRC/'collection-summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

