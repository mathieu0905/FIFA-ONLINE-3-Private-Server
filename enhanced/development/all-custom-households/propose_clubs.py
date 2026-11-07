"""Propose explicitly custom identities for verified clubs absent from installed names.

These IDs are local registrations, NEVER alleged FIFA/EA IDs. A review report
separates school/national academies and possible existing-club aliases.
"""
from pathlib import Path
from collections import defaultdict
import difflib,hashlib,json,sqlite3
import collect as b
import map_clubs as m
def parent(name):
 name=name.strip().split('#')[0]
 name=m.re.sub(r'\s+(?:Reserves and Academy|Under-\d+s and Academy|Youth Academy|Youth Sector|Junior Team|Academy|Cantera|\(youth\))$','',name,flags=m.re.I)
 return m.re.sub(r'\s+(?:B|C|II|III|U-\d+)$','',name)
def main():
 mapping=b.read(b.P/'club-mapping.json');labels=b.read(b.SRC/'english-teamnames.json');used={int(k) for k in labels}
 with sqlite3.connect((b.S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  used.update(r[0] for r in db.execute('select distinct teamid from players'));used.update(r[0] for r in db.execute('select distinct teamid from playerhistory'))
 used.add(999327);assigned={};path=b.P/'proposed-custom-clubs.json'
 if path.exists():assigned={r['canonical_key']:r['teamid'] for r in b.read(path)['clubs']}
 used.update(assigned.values());clubs=defaultdict(list);excluded=[];needs_review=[];name_by_norm=defaultdict(list)
 for tid,name in labels.items():name_by_norm[m.literal(name)].append((int(tid),name))
 # All source rows are required, never the three examples alone.
 missing_names={r['club'] for r in mapping['unresolved']}
 for path in (b.SRC/'wiki').glob('*.json'):
  if not path.stem.isdigit():continue
  r=b.read(path)
  if r.get('status')!='OK':continue
  for spell in r['career']:
   title=spell['wiki_title'] or spell['club_name']
   if title not in missing_names:continue
   record=dict(playerid=r['playerid'],source_url=r['url'],raw_sha256=r['raw_sha256'],**spell)
   if not title.strip():needs_review.append(dict(reason='Unexpanded or missing club name',**record));continue
   if spell['youth'] and (m.re.search(r'\b(?:school|university|college|INF|CNFE)\b|小学|中学|学校|大学|附中|校队|足球协会|足协',title,m.re.I) or title in ('Aspire Academy','Clairefontaine')):
    excluded.append(dict(reason='School, university or national training centre; not club eligibility',**record));continue
   canonical=parent(title);key=m.literal(canonical)
   if not key:needs_review.append(dict(reason='No canonical club identity',**record));continue
   if key in name_by_norm:
    needs_review.append(dict(reason='Existing club names need explicit alias resolution',candidates=name_by_norm[key],**record));continue
   clubs[(key,canonical)].append(record)
 result=[]
 for (key,name),spells in sorted(clubs.items()):
  tid=assigned.get(key)
  if tid is None:
   tid=900000+int(hashlib.sha256(key.encode()).hexdigest()[:12],16)%50000
   while tid in used:tid=900000+(tid-900000+1)%50000
   assigned[key]=tid;used.add(tid)
  suggestions=difflib.get_close_matches(m.literal(name),list(name_by_norm),n=3,cutoff=.78)
  result.append(dict(teamid=tid,canonical_key=key,name=name,id_kind='LOCAL_CUSTOM_CLUB_NOT_EA_ID',source_spells=spells,possible_existing_aliases=[v for n in suggestions for v in name_by_norm[n]]))
 output=dict(status='REVIEW_REQUIRED_NOT_INSTALLABLE',clubs=result,excluded_non_clubs=excluded,unresolved=needs_review,formal_files_written=False)
 b.write(b.P/'proposed-custom-clubs.json',output)
 print(json.dumps(dict(proposed_clubs=len(result),source_spells=sum(len(r['source_spells']) for r in result),excluded=len(excluded),unresolved=len(needs_review),possible_existing_aliases=sum(bool(r['possible_existing_aliases']) for r in result))))
 print('\n'.join(str((r['name'],r['possible_existing_aliases'])) for r in result if r['possible_existing_aliases'])[:8000])
if __name__=='__main__':main()
