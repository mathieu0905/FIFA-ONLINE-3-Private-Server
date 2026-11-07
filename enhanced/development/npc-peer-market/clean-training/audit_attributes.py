"""Compare season-specific attributes against pre-import client DB and public API."""
from pathlib import Path
import collections,datetime,hashlib,http.cookiejar,json,random,re,sqlite3,time,urllib.parse,urllib.request
P=Path(__file__).resolve().parent;R=P.parent
N=Path('D:/fifaol3/releases/bulk-seasons-main-v1/fifadb.db.db2.before.sqlite')
rows=json.loads((R/'historical-data.json').read_text('utf8'))
fields=json.loads((R/'expanded-training/encoder.json').read_text('utf8'))['raw_fields']
with sqlite3.connect(N.as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;native={r['spid']:dict(r) for r in db.execute('select * from players')}
drift=[];same=0;missing=[]
for r in rows:
 n=native.get(r['spid'])
 if n is None:missing.append(r['spid']);continue
 delta={f:[n[f],r[f]] for f in fields if n[f]!=r[f]}
 if delta:drift.append(dict(spid=r['spid'],name=r['name'],differences=delta))
 else:same+=1
by_player=collections.defaultdict(list)
for r in rows:by_player[r['playerid']].append(r)
pairs=0;identical=0;different=0
for rs in by_player.values():
 for i,a in enumerate(rs):
  for b in rs[i+1:]:
   pairs+=1
   if all(a[f]==b[f] for f in fields):identical+=1
   else:different+=1

# Predetermined season-stratified sample, plus every exact conflicting input group.
sample=set([10163705,47163705,6153079,65153079])
by_season=collections.defaultdict(list)
for r in rows:by_season[r['season']].append(r)
rng=random.Random(20261107)
for season,rs in sorted(by_season.items()):sample.add(rng.choice(sorted(rs,key=lambda r:r['spid']))['spid'])
# Multiseason controls: five Mandanda versions with known different native GK attributes.
sample.update([11163705,35163705,53163705,67163705,88163705])
sample.update([10158023,47158023,91195864])
cache=P/'attribute-pages';cache.mkdir(exist_ok=True)
results=[];last=0.
def request(opener,req):
 global last
 time.sleep(max(0,2-(time.monotonic()-last)))
 with opener.open(req,timeout=45) as response:raw=response.read()
 last=time.monotonic();return raw
for spid in sorted(sample):
 f=cache/(str(spid)+'.json');page=cache/(str(spid)+'.html');url=f'https://en.fifaaddict.com/fo3player.php?id={spid}'
 if not f.exists():
  try:
   opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   raw=request(opener,urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}));body=raw.decode('utf8','replace');page.write_bytes(raw)
   token=re.search(r"var araiwaAnyong\s*=\s*['\"]([^'\"]+)['\"]",body).group(1)
   payload=urllib.parse.urlencode(dict(araiwa=token,playerdb=str(spid),mode=1)).encode()
   raw=request(opener,urllib.request.Request('https://en.fifaaddict.com/api/api_fo3db.php',data=payload,headers={'User-Agent':'Mozilla/5.0','Referer':url,'X-Requested-With':'XMLHttpRequest'}));x=json.loads(raw)
   assert isinstance(x.get('attr'),dict) and 'gkdiving' in x['attr'];f.write_bytes(raw)
  except Exception as e:
   results.append(dict(spid=spid,status='FAILED',error=repr(e)));print('FAILED',spid,repr(e),flush=True);continue
 else:x=json.loads(f.read_text('utf8'))
 attrs={('interceptions' if k=='tacticalawareness' else k):int(v) for k,v in x['attr'].items() if str(v).isdigit() and k not in ('poten','perfcon')}
 n=native.get(spid);diff={f:[n.get(f),v] for f,v in attrs.items() if n is not None and n.get(f)!=v}
 results.append(dict(spid=spid,source_url=url,status='MATCH' if n and not diff and len(attrs)==33 else 'MISMATCH',compared_attributes=len(attrs),differences=diff,attributes=attrs,public_response_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
 print('AUDIT',spid,results[-1]['status'],len(attrs),diff,flush=True)
 out=dict(schema=1,native_source=str(N),native_sha256=hashlib.sha256(N.read_bytes()).hexdigest(),historical_training_rows=len(rows),native_58_field_matches=same,native_drift=drift,native_missing=missing,multiseason_player_pair_comparison=dict(pairs=pairs,identical_58=identical,different_58=different),sample_policy='One deterministic random card per historical season; conflicting-input cases and Mandanda multiseason controls added before observing API values',public_results=results,interpretation='Native source and public site agreement rules out a later join/import error for those checked; neither establishes original EA historical correctness independently. Public full attribute check is a sample; all matched listings receive five-stat checks before training.',complete=len(results)==len(sample))
 (P/'attribute-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
print('DONE',len(results),collections.Counter(r['status'] for r in results),flush=True)
