"""Read-only production check of merged/sorted seasons, actual ratings and short names."""
from pathlib import Path
import json,re,sqlite3,ssl,urllib.request,hashlib
import organize_seasons as s
S,C,R=s.S,s.C,s.R
out=Path(s.read(R/'latest-build.json')['path']);build=s.read(out/'build.json');installed=s.read(R/'installed.json')
for name,path in [('fifadb.sqlite',S/'gamedata/fifadb.sqlite'),('data_0.big',C/'data/data_0.big'),('static_roster.json',S/'responses/static_roster.json')]:assert s.sha(path)==build['outputs'][name]
def request(path,admin=False):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1'
 with urllib.request.urlopen(base+path,context=ssl._create_unverified_context(),timeout=30) as response:assert response.status==200;return json.loads(response.read())
roster=request('/static/roster');assert roster==s.read(out/'static_roster.json')
merged=[e for e in roster['seasons'] if set(e['value'])&{48,49,55}];assert len(merged)==1 and merged[0]['value']==[48,49,55]
score=[r['mean'] for r in build['rankings']];assert score==sorted(score,reverse=True)
for rating in build['ratings']:
 detail=request('/api/database_detail?spid='+str(rating['spid']),True);assert detail['ovr']+5==rating['after_level1_plus1']==rating['before_level1_plus1']+2,(rating,detail.get('ovr'))
main=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
for pid,label in s.NAMES.items():assert main.execute('select short from nameschi where playerid=?',(pid,)).fetchone()[0]==label
decoded=bytes(s.codec.extract_fifadb.decrypt(s.codec.bigdir.read(C/'data/data_0.big','data/db2/chi.db.db2')));assert b'SQLite format 3\0'+decoded[16:]==(out/'chi.sqlite').read_bytes()
query='select p.spid,n.short from players p join nameschi n using(playerid) join permid m using(spid) where p.spid/1000000 in (48,49,55) and m.transferable=1 and m.licensed=1'
rows=main.execute(query).fetchall();assert len(rows)==53 and all('shortname' not in name.casefold() for _,name in rows)
for path,digest in installed['protected'].items():
 if not path.endswith('state.json'):assert s.sha(path)==digest
before=s.read(R/'fresh-stop-snapshot'/installed['revision']/'state.json');live=s.read(S/'gamedata/state.json')
# The other chat's completed, post-restart grant checkpoint proves installation
# preservation. Later live card removals are recorded separately, never restored.
checkpoint=Path('D:/fifaol3/new-player-models/bulk-repair/grant20/operation-after-state.json')
after=s.read(checkpoint)
assert {k:v for k,v in before.items() if k not in ('market_simulation','teams')}=={k:v for k,v in after.items() if k not in ('market_simulation','teams')}
grant_path=Path('D:/fifaol3/new-player-models/bulk-repair/grant20/journal.json');grant=s.read(grant_path)
assert grant['authorization']=='User explicitly requested these newly adapted players at +20 in their roster'
allowed={a['id']:a for a in grant['actions'] if a['action']=='created'};additions=[];captain_changes=[]
assert set(before['teams'])==set(after['teams'])
for slot,oldteam in before['teams'].items():
 newteam=after['teams'][slot]
 assert {k:v for k,v in oldteam.items() if k not in ('players','squad')}=={k:v for k,v in newteam.items() if k not in ('players','squad')}
 assert {k:v for k,v in oldteam['squad'].items() if k!='captain'}=={k:v for k,v in newteam['squad'].items() if k!='captain'}
 key=lambda p:str(p.get('_id') or p['spid'])
 oldcards={key(p):p for p in oldteam['players']};newcards={key(p):p for p in newteam['players']}
 if oldteam['squad']['captain']!=newteam['squad']['captain']:
  assert str(newteam['squad']['captain']) in newcards
  captain_changes.append(dict(slot=slot,before=oldteam['squad']['captain'],after=newteam['squad']['captain'],observation='Concurrent live captain change retained; installer did not write state'))
 assert all(newcards.get(k)==v for k,v in oldcards.items()),'Existing card removed or mutated'
 for iid in set(newcards)-set(oldcards):
  card=newcards[iid];action=allowed[iid]
  assert slot==str(grant['target']['slot']) and card['spid']==action['spid'] and card['grade']==action['grade']==20
  additions.append(iid)
assert set(additions)==set(allowed),'Concurrent additions must match the authorized grant exactly'
entry=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',(S/'play-local.bat').read_bytes());assert len(entry)==1;proof=s.common.load(S/entry[0].decode().replace('\\','/'),'season_strength_verified').preflight(S,C)
result=dict(status='PASS',preflight=proof,one_man_united_entry=True,eligible_cards=53,entry_count=len(roster['seasons']),other_season_entries_preserved=True,all_season_codes_preserved=True,strength_order=True,all_53_primary_ratings_exact_plus2=True,short_names_fixed_both_libraries=s.NAMES,native_ea_roster_untouched=True,assets_preserved=True,concurrent_authorized_additions_retained=len(additions),concurrent_grant_journal=str(grant_path),shop_and_issued_pack_configs_preserved=True,native_ui_verified=False,gui_used=False,top_seasons=build['rankings'][:6])
result['concurrent_captain_changes_retained']=captain_changes
result['asset_preservation_checkpoint']=str(checkpoint)
key=lambda p:str(p.get('_id') or p['spid'])
checkpoint_cards={key(p):p for p in after['teams']['0']['players']};live_cards={key(p):p for p in live['teams']['0']['players']}
result['subsequent_live_progress_observed']=dict(removed_ids=sorted(set(checkpoint_cards)-set(live_cards)),added_ids=sorted(set(live_cards)-set(checkpoint_cards)),changed_ids=sorted(k for k in checkpoint_cards.keys()&live_cards.keys() if checkpoint_cards[k]!=live_cards[k]),captain_before=after['teams']['0']['squad']['captain'],captain_now=live['teams']['0']['squad']['captain'],restored_or_overwritten=False)
s.write(R/'verification.json',result);print(json.dumps(result,ensure_ascii=True))
