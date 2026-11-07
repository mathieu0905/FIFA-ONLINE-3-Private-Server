"""Retain senior, loan and club-youth facts with identity and raw-source evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
import datetime,gzip,hashlib,json,re,time,urllib.parse,urllib.request,urllib.error,threading,sys
import collect as base
sys.path.insert(0,str(base.P/'deps'))
import wikitextparser
P=base.P;ROOT=base.SRC/'wiki';ROOT.mkdir(exist_ok=True)
RATE_PAUSED=threading.Event()
REQUEST_LOCK=threading.Lock()
LAST_REQUEST=0.0
def request(url):
 global LAST_REQUEST
 with REQUEST_LOCK:
  time.sleep(max(0,1.5-(time.monotonic()-LAST_REQUEST)))
  if RATE_PAUSED.is_set():raise RuntimeError('Collection paused after HTTP 429')
  LAST_REQUEST=time.monotonic()
 return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 FO3-career-audit/1.0'}),timeout=22).read()
ALIASES={121933:'René Adler',13130:'Wes Brown',135423:'Cicinho',136144:'Robinho',141645:'Eric Abidal',160766:'Jérémy Ménez',162409:'Giuseppe Rossi',163423:'Abou Diaby',167963:'Anderson (footballer, born 1988)',194644:'Martín Montoya',199835:'Emmanuel Emenike',204550:'Víctor Ibarbo',230024:'Bryan Robson',230026:'Denis Law',239:'Andy Cole',245:'Nicky Butt',249:'Phil Neville',2769:'José Bosingwa',36:'Dwight Yorke',51123:'Mathieu Bodmer',53019:'Denis Irwin',7631:'Antonio Cassano',700089:'Ismael Saibari',700108:'Savinho',700128:'Giuliano Simeone',700146:'Abde Ezzalzouli',700220:'Cucho Hernández',700225:'Aleksey Batrakov',700287:'Ange-Yoan Bonny',700300:'Sergio Herrera',700302:'Toni Fruk',700305:'José López (footballer, born 2000)',700310:'Rayan (footballer, born 2006)',700311:'Ayyoub Bouaddi'}
def clean(value):
 value=re.sub(r'<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>','',value,flags=re.S);value=re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]',r'\2',value);value=re.sub(r'\[\[([^]]+)\]\]',r'\1',value);return re.sub(r'<[^>]+>|\{\{.*?\}\}','',value).strip()

def resolve_ill(value):
 for t in reversed(wikitextparser.parse(value).templates):
  if t.name.strip().lower() in ('ill','interlanguage link','interlanguage link multi'):
   args={a.name.strip():a.value.strip() for a in t.arguments};name=args.get('1');label=args.get('lt',name)
   if name:value=value[:t.span[0]]+'[['+name+'|'+label+']]'+value[t.span[1]:]
  elif re.fullmatch(r'link-[a-z]{2,3}',t.name.strip().lower()) or t.name.strip().lower()=='le':
   args={a.name.strip():a.value.strip() for a in t.arguments};name=args.get('2',args.get('1'));label=args.get('3',args.get('1',name))
   if name:value=value[:t.span[0]]+'[['+name+'|'+label+']]'+value[t.span[1]:]
 return value

ALIASES.update({1025:'Rui Costa',1040:'Roberto Carlos',37576:'Ronaldo (Brazilian footballer)',5003:'Cafu',176580:'Luis Suárez (Uruguayan footballer)',189681:'Rafael (footballer, born 1990)',193747:'Koke (footballer, born 1992)',209499:'Fabinho (footballer, born 1993)',210411:'Otávio (footballer, born 1995)',229391:'João Palhinha',231410:'Brahim Díaz'})
ALIASES.update({161840:'Fernando Hierro',173608:'Joselu',184943:'Ramires',190043:'Pelé',190149:'Óscar de Marcos',190871:'Neymar',202477:'Gerard Deulofeu',203038:'Lucas Piazon',205157:'Íñigo Ruiz de Galarreta',208777:'Óliver Torres',210602:'Salem Al-Dawsari',214101:'Paulo Futre',156353:'Luis Hernández (footballer, born 1968)',189513:'Dani Parejo',192123:'Chris Wood (footballer, born 1991)',192638:'Marcos Alonso (footballer, born 1990)',193080:'David de Gea',194957:'Phil Jones (footballer)',201153:'Álvaro Morata',204963:'Dani Carvajal',209297:'Fred (footballer, born 1993)',210035:'Álex Grimaldo',210257:'Ederson (footballer, born 1993)',210385:'Rui Silva (footballer, born 1994)',215590:'Ayoze Pérez',216447:'Álvaro García (footballer, born 1992)',216547:'Rafa Silva',219693:'Diego Carlos (footballer)',220710:'Harry Wilson (footballer)'})
ALIASES.update({194957:'Phil Jones (footballer, born 1992)',219693:'Diego Carlos (footballer, born 1993)',220710:'Harry Wilson (footballer, born 1997)',205157:'Iñigo Ruiz de Galarreta',227236:'André-Frank Zambo Anguissa',227950:'Yeray Álvarez',231184:'Gorka Guruzeta',234579:'Julián Quiñones',237086:'Kim Min-jae',222737:'Malcom (footballer)',224221:'Joachim Andersen (footballer)',225663:'Aleksandr Golovin (footballer)',230142:'Mikel Oyarzabal',231936:'Ben White',232580:'Gabriel Magalhães',233092:'Joaquín Pereyra (footballer, born 1998)',235947:'Juan Brunetta (footballer)',237646:'Daniel Muñoz (footballer)',240690:'Nicolás González (footballer, born 1998)',241084:'Luis Díaz (footballer, born 1997)',700016:'Nuno Mendes (footballer, born 2002)',700020:'Bremer (footballer)',700024:'Fermín López',700025:'Eric García',700050:'Roger Ibañez',700051:'João Pedro (footballer, born 2001)',700060:'Anthony Gordon (footballer)',700062:'James Garner (footballer)'})
ALIASES.update({710002:'李昊 (2004年)',710005:'刘诚宇 (足球运动员)',710009:'杨皓宇 (足球运动员)',710014:'汪士钦'})
ALIASES.update({233092:'Joaquín Pereyra (Argentine footballer)',700020:'Gleison Bremer',700025:'Eric Garcia (footballer, born 2001)',700074:'Oihan Sancet',700075:'Francisco Trincão',700080:'Dani Vivian',700096:'Murillo (footballer, born 2002)',700104:'Jorge de Frutos',700106:'Marc Pubill',700121:'Manu Koné',700150:'Esteban Lepaul',700167:'Lee Kang-in',700181:'Samu Aghehowa',700184:'Youssouf Fofana (footballer, born 1999)',700190:'Chris Richards (soccer)',700207:'Enzo Boyomo',700217:'Alejandro Romero Gamarra',700219:'Isi Palazón',700238:'Diego Gómez (footballer, born 2003)',700254:'Ander Barrenetxea',700271:'Amad Diallo',700274:'Rômulo (footballer, born 2002)',700275:'Bento (footballer, born 1999)',700276:'Estêvão Willian',700299:'Musab Al-Juwayr',700305:'José Manuel López (footballer)',700312:'Mikel Jauregizar',700314:'Wesley França',710005:'刘诚宇'})
ALIASES.update({700096:'Murillo (footballer)',700207:'Flavien Enzo Boyomo',700238:'Diego Gómez (Paraguayan footballer)',700275:'Bento (footballer)',710014:'Wang Shiqin'})
def parse(raw):
 text=raw.decode('utf8');all_templates=wikitextparser.parse(text).templates;templates=[t for t in all_templates if t.name.strip().lower().replace('_',' ') in ('infobox football biography','infobox football biography2','infobox footballer')];fields={a.name.strip():a.value.strip() for a in templates[0].arguments} if templates else {};born=fields.get('birth_date','')
 if not born:
  births={a.value.strip() for t in all_templates if t.name.strip().lower().startswith('infobox') for a in t.arguments if a.name.strip()=='birth_date' and a.value.strip()}
  if len(births)==1:born=next(iter(births))
 match=re.search(r'\{\{\s*(?:birth[ _-]?date(?: and age)?|dob|bda)\s*\|([^{}]+)\}\}',born,re.I)
 dob=None
 if match:
  nums=[int(s) for s in match[1].split('|') if re.fullmatch(r'\s*\d{1,4}\s*',s)]
  if len(nums)>=3 and 1850<=nums[0]<=2026:
   try:dob=datetime.date(*nums[:3]).isoformat()
   except ValueError:pass
 careers=[]
 for key,value in fields.items():
  m=re.fullmatch(r'(youth_?clubs|clubs)(\d+)',key)
  if not m or not value.strip():continue
  value=resolve_ill(value);youth=m[1]!='clubs';n=m[2];years=fields.get('youthyears'+n,fields.get('youth_years'+n,'')) if youth else fields.get('years'+n,'');years=clean(years);numbers=re.findall(r'\b(?:18|19|20)\d{2}\b',years);start=int(numbers[0]) if numbers else -1;end=int(numbers[1]) if len(numbers)>1 else -1
  if numbers and re.match(r'^[^\d]*(?:–|—|-)\s*(?:18|19|20)\d{2}',years):start,end=-1,int(numbers[0])
  if start!=-1 and end==-1 and re.fullmatch(r'\d{4}',years):end=start
  club_links=re.findall(r'\[\[([^]|]+)(?:\|([^]]+))?\]\]',re.sub(r'<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>','',value,flags=re.S))
  club=clean(value);loan='loan' in club.lower() or '租借' in club or '外借' in club or '→' in club;club=re.sub(r'\s*\((?:loan|on loan)\)|\s*（(?:租借|外借)）','',club,flags=re.I).strip(' →')
  careers.append(dict(club_name=club,wiki_title=club_links[0][0] if club_links else None,joinedyear=start,endyear=end,loan=int(loan),youth=youth,years_source=years,source_field=key))
 return dob,careers,fields.get('fullname',fields.get('full_name',fields.get('name','')))
def main():
 people=base.read(base.SRC/'identity-links.json');registry=base.read(base.S/'gamedata/custom_rosters.json');zh={c['base_playerid']:c.get('name_zh') for c in registry['cards'] if c.get('name_zh')};ea={r['id']:r for path in base.SRC.glob('ea-*.json') for r in base.read(path).get('items',[])}
 def one(person):
  pid=person['playerid'];path=ROOT/f'{pid}.json'
  if path.exists() and base.read(path).get('status')=='OK':return base.read(path)
  if RATE_PAUSED.is_set():return dict(status='PAUSED_RATE_LIMIT',playerid=pid)
  official=ea.get(person.get('source_playerid'),{});title=ALIASES.get(pid) or official.get('commonName') or ((official.get('firstName','')+' '+official.get('lastName','')).strip()) or max(person['names'],key=len)
  lang='zh' if pid>=710000 and pid!=710014 else 'en'
  if lang=='zh':title=ALIASES.get(pid) or zh.get(pid,title)
  url=f'https://{lang}.wikipedia.org/w/index.php?'+urllib.parse.urlencode(dict(title=title.replace(' ','_'),action='raw'))
  result=dict(status='FETCH_FAILED',playerid=pid,title=title,lang=lang,url=url,expected_dob=person['birthdate'])
  try:
   rawpath=ROOT/f'{pid}.txt.gz'
   if pid in ALIASES:rawpath=ROOT/f'{pid}-{hashlib.sha256(title.encode()).hexdigest()[:8]}.txt.gz'
   if rawpath.exists():raw=gzip.decompress(rawpath.read_bytes())
   else:
    raw=request(url);rawpath.write_bytes(gzip.compress(raw,mtime=0))
   # Resolve real wiki redirects; this is a URL title, never executable content.
   seen=set()
   for _ in range(5):
    redirect=re.match(r'\s*#(?:REDIRECT|重定向)\s*\[\[([^]]+)\]\]',raw.decode('utf8'),re.I)
    if not redirect:break
    if redirect[1] in seen:raise RuntimeError('Redirect cycle in public source')
    seen.add(redirect[1])
    title=redirect[1].split('#')[0];url=f'https://{lang}.wikipedia.org/w/index.php?'+urllib.parse.urlencode(dict(title=title.replace(' ','_'),action='raw'));raw=request(url);rawpath.write_bytes(gzip.compress(raw,mtime=0));result.update(title=title,url=url)
   dob,careers,name=parse(raw)
   if not careers and re.search(r'may refer to|\{\{(?:disambig|hndis|given name|surname)',raw.decode('utf8'),re.I):
    candidates=set();birthyear=person['birthdate'][:4]
    for line in raw.decode('utf8').splitlines():
     if 'footballer' not in line.lower() or birthyear not in line:continue
     for candidate in re.findall(r'\[\[([^]|]+)(?:\|[^]]+)?\]\]',line):
      if 'footballer' in candidate.lower() or len(re.findall(r'\[\[',line))==1:candidates.add(candidate)
    if len(candidates)==1:
     title=next(iter(candidates));url=f'https://{lang}.wikipedia.org/w/index.php?'+urllib.parse.urlencode(dict(title=title.replace(' ','_'),action='raw'));resolved_path=ROOT/f'{pid}-resolved-{hashlib.sha256(title.encode()).hexdigest()[:8]}.txt.gz'
     raw=gzip.decompress(resolved_path.read_bytes()) if resolved_path.exists() else request(url);resolved_path.write_bytes(gzip.compress(raw,mtime=0));rawpath=resolved_path;result.update(title=title,url=url,disambiguation_basis='Unique football biography for expected birthyear; full DOB still mandatory');dob,careers,name=parse(raw)
   result.update(source_dob=dob,source_name=clean(name),career=careers,raw_file=str(rawpath),raw_sha256=hashlib.sha256(raw).hexdigest(),fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());result['status']='OK' if dob==person['birthdate'] and careers else 'DOB_MISMATCH' if dob and dob!=person['birthdate'] else 'NO_VERIFIED_INFOBOX'
  except urllib.error.HTTPError as e:
   result['error']=str(e)
   if e.code==429:RATE_PAUSED.set();result['status']='PAUSED_RATE_LIMIT'
  except Exception as e:result['error']=str(e)
  base.write(path,result);time.sleep(1.2);return result
 counts=Counter()
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(one,p) for p in people]
  for n,f in enumerate(as_completed(futures),1):
   result=f.result();counts[result['status']]+=1
   if n%100==0:print('WIKI',n,dict(counts),flush=True)
 summary=dict(players=len(people),outcomes=dict(counts),formal_files_written=False);base.write(ROOT/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
