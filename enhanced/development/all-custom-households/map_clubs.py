"""Resolve retained club facts against exact installed/official club identities."""
from pathlib import Path
from collections import defaultdict,Counter
import html,json,re,sqlite3,unicodedata,sys,importlib.util
import collect as b
P=b.P;S=b.S;PRE=P.parent/'team-balance-household'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def norm(s):
 s=unicodedata.normalize('NFKD',html.unescape(s).translate(str.maketrans({'Ł':'L','ł':'l','Ø':'O','ø':'o','Đ':'D','đ':'d','Ð':'D','ð':'d','ß':'ss'}))).encode('ascii','ignore').decode().lower().replace('utd','united')
 s=re.sub(r'\b(?:f\.?c\.?|a\.?f\.?c\.?|c\.?f\.?|s\.?c\.?|a\.?c\.?|club de futbol|football club)\b',' ',s)
 return re.sub('[^a-z0-9]','',s)
def literal(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',html.unescape(s).translate(str.maketrans({'Ł':'L','ł':'l','Ø':'O','ø':'o','Đ':'D','đ':'d','Ð':'D','ð':'d','ß':'ss'}))).encode('ascii','ignore').decode().lower())
def maps():
 manual=load(PRE/'manual.py','household_manual_mapping');kor=defaultdict(set);eng=defaultdict(set)
 for tid,name in re.findall(r"DataCenter.SetAbilitySearch\('(\d+)', 'n4TeamId'\);[^<]*\"><span>([^<]+)</span>",(PRE/'sources/search-current.html').read_text('utf8')):kor[html.unescape(name).strip()].add(int(tid))
 for lang,dest in [('kor',kor),('eng',eng)]:
  with sqlite3.connect((PRE/f'sources/{lang}.sqlite').as_uri()+'?mode=ro',uri=True) as db:
   for tid,name in db.execute('select teamid,teamname from team'):dest[name].add(tid)
 for name,(tid,_) in manual.EXACT_CLUB_ALIASES.items():kor[name]={tid}
 for tid,name in b.read(b.SRC/'english-teamnames.json').items():eng[name].add(int(tid))
 coverage=b.read(PRE/'build-extended/coverage-report.json')
 for name,row in coverage['recovered_club_aliases'].items():kor[name]={row['teamid']}
 aliases={131681:47,131682:44,115841:46,115845:39}
 km={k:aliases.get(next(iter(v)),next(iter(v))) for k,v in kor.items() if len(v)==1}
 for path in b.SRC.glob('ea-*.json'):
  for r in b.read(path).get('items',[]):
   if r.get('team') and r.get('gender',{}).get('id')==0:eng[r['team']['label']].add(r['team']['id'])
 normalized=defaultdict(set)
 for name,ids in eng.items():normalized[norm(name)].update(aliases.get(x,x) for x in ids)
 em={k:next(iter(v)) for k,v in normalized.items() if len(v)==1 and k}
 exact=defaultdict(set)
 for name,ids in eng.items():exact[literal(name)].update(aliases.get(x,x) for x in ids)
 for k,v in exact.items():
  if len(v)==1:em['literal:'+k]=next(iter(v))
 return km,em
def main():
 km,em=maps();reviewed=b.read(P/'club_aliases.json');labels=b.read(b.SRC/'english-teamnames.json');official=defaultdict(set)
 for path in b.SRC.glob('ea-*.json'):
  for row in b.read(path).get('items',[]):
   if row.get('team') and row.get('gender',{}).get('id')==0:official[row['team']['id']].add(row['team']['label'])
 for name,(tid,expected) in reviewed.items():
  if labels.get(str(tid))!=expected and expected not in official[tid]:raise RuntimeError('Reviewed installed/official club identity changed: '+name)
 active={c['base_playerid'] for c in b.read(S/'gamedata/custom_rosters.json')['cards']}
 careers={int(p.stem):b.read(p) for p in (b.SRC/'careers').glob('*.json') if int(p.stem) in active};wiki={int(p.stem):b.read(p) for p in (b.SRC/'wiki').glob('*.json') if p.stem.isdigit() and int(p.stem) in active};votes=defaultdict(list)
 for pid,w in wiki.items():
  if w.get('status')!='OK':continue
  native=careers.get(pid,{})
  if native.get('status')!='OK':continue
  for spell in w['career']:
   if spell['youth'] or spell['joinedyear']<1850:continue
   same=[s for s in w['career'] if not s['youth'] and s['joinedyear']==spell['joinedyear'] and s['loan']==spell['loan']]
   matches={km[s['club_ko']] for s in native['career'] if s['joinedyear']==spell['joinedyear'] and s['loan']==spell['loan'] and s['club_ko'] in km}
   if len(same)==1 and len(matches)==1:
    key=spell['wiki_title'] or spell['club_name'];votes[key].append(dict(playerid=pid,teamid=next(iter(matches)),year=spell['joinedyear']))
 exact={}
 conflicts={}
 for name,items in votes.items():
  ids={r['teamid'] for r in items}
  if len(ids)==1 and len({r['playerid'] for r in items})>=3:exact[name]=dict(teamid=next(iter(ids)),evidence=items)
  elif len(ids)>1:conflicts[name]=items
 resolved=[];missing=defaultdict(list)
 for pid,w in wiki.items():
  if w.get('status')!='OK':continue
  for spell in w['career']:
   title=spell['wiki_title'] or spell['club_name'];tid=None;basis=None
   if title in reviewed:tid=reviewed[title][0];basis='reviewed historical/current club alias'
   choices={em['literal:'+literal(n)] for n in (title,spell['club_name']) if 'literal:'+literal(n) in em}
   if not choices:choices={em[norm(n)] for n in (title,spell['club_name']) if norm(n) in em}
   if tid is None and len(choices)==1:tid=next(iter(choices));basis='exact unambiguous installed/official English name'
   if tid is None and title in exact:tid=exact[title]['teamid'];basis='independent career alignment'
   if tid is None:
    parent_names=[]
    for n in (title,spell['club_name']):
     parent=re.sub(r'\s+(?:Reserves and Academy|Under-\d+s and Academy|Youth Academy|Youth Sector|Junior Team|Academy|Cantera|\(youth\))$','',n,flags=re.I)
     parent=re.sub(r'\s+(?:B|C|II|III|U-\d+)$','',parent)
     parent=re.sub(r'(?:B队|二队|青年队|梯队|预备队)$','',parent)
     if parent!=n:parent_names.append(parent)
    known={'Real Madrid Castilla':'Real Madrid','FC Bayern Munich Junior Team':'FC Bayern Munchen','Bayern Munich Junior Team':'FC Bayern Munchen','FC Bayern Munich II':'FC Bayern Munchen','Jong Ajax':'Ajax','Jong PSV':'PSV','Athletic Bilbao':'Athletic Club','Bilbao Athletic':'Athletic Club','RC Celta de Vigo':'RC Celta','RCD Espanyol Cantera':'RCD Espanyol','S.L. Benfica':'SL Benfica','FC Barcelona Atlètic':'FC Barcelona'}
    if title in known:parent_names.append(known[title])
    reviewed_parents={reviewed[n][0] for n in parent_names if n in reviewed}
    if len(reviewed_parents)==1:tid=next(iter(reviewed_parents));basis='reviewed reserve/academy parent alias'
    choices={em['literal:'+literal(n)] for n in parent_names if 'literal:'+literal(n) in em}
    if not choices:choices={em[norm(n)] for n in parent_names if norm(n) in em}
    if tid is None and len(choices)==1:tid=next(iter(choices));basis='reviewed club academy/reserve parent identity'
   row=dict(playerid=pid,**spell,teamid=tid,basis=basis if tid is not None else None)
   if tid is None:missing[title].append(row)
   else:resolved.append(row)
 unresolved=[dict(club=k,count=len(v),examples=v[:3]) for k,v in sorted(missing.items(),key=lambda x:(-len(x[1]),x[0]))]
 b.write(P/'club-mapping.json',dict(korean=km,english=em,aligned=exact,alignment_conflicts=conflicts,resolved=resolved,unresolved=unresolved))
 print(json.dumps(dict(wiki_ok=sum(w.get('status')=='OK' for w in wiki.values()),mapped_spells=len(resolved),unresolved_clubs=len(missing),unresolved_spells=sum(map(len,missing.values())))))
 print('\n'.join(str((r['club'],r['count'])) for r in unresolved[:90]))
if __name__=='__main__':main()
