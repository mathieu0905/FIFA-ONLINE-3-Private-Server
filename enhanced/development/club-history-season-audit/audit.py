"""Read-only audit of club team-colour eligibility for seasons18/19."""
from pathlib import Path
import collections,gzip,hashlib,json,sqlite3,sys
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');E=Path('D:/fifaol3/club-history');sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
before=sha(S/'gamedata/fifadb.sqlite');mapping=read(E/'club-map.json');aliases={131681:47,131682:44,115841:46,115845:39};supported=read(S/'server_display_zh.json')['names_by_id']['TEAMNAMES_CHI.json']
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
players=[dict(r) for r in db.execute('select p.spid,p.playerid,p.teamid,p.historyopen,n.short from players p join nameschi n using(playerid) where p.spid/1000000 in (18,19) order by p.spid')];records=[]
for player in players:
 pid=player['playerid'];history=[dict(r) for r in db.execute('select * from playerhistory where playerid=? order by ordernum',(pid,))];clubs={r['teamid'] for r in history};entry=dict(**player,season=player['spid']//1000000,history_rows=len(history),history_clubs=[dict(teamid=t,name=supported.get(str(t),str(t))) for t in sorted(clubs)],server_club_eligibility=sorted(clubs|{player['teamid']}),client_history_available=bool(player['historyopen']),missing_mapped_official_clubs=[],unmapped_official_clubs=[],unsupported_official_clubs=[])
 source=E/'records'/f'{pid}.json';entry['retained_official_source']='MISSING'
 if source.exists():
  record=read(source);entry['retained_official_source']=record['status']
  if record['status']=='OK':
   raw=gzip.decompress(Path(record['raw_file']).read_bytes());assert hashlib.sha256(raw).hexdigest()==record['raw_sha256'];entry['source_url']=record['url'];entry['source_fetched_utc']=record['fetched_utc']
   for career in record['career']:
    tid=mapping.get(career['club_ko'])
    if tid is None:entry['unmapped_official_clubs'].append(career['club_ko']);continue
    tid=aliases.get(tid,tid)
    if str(tid) not in supported:entry['unsupported_official_clubs'].append(dict(teamid=tid,name_ko=career['club_ko']))
    if tid not in clubs|{player['teamid']}:entry['missing_mapped_official_clubs'].append(dict(teamid=tid,name=supported.get(str(tid),career['club_ko'])))
 records.append(entry)
db.close();assert before==sha(S/'gamedata/fifadb.sqlite'),'Source changed during audit'
sys.path[:0]=[str(S/'tools/re'),str(S)];import bigdir,extract_fifadb
plain=bytes(extract_fifadb.decrypt(bigdir.read(C/'data/data_0.big','data/db2/fifadb.db.db2')));assert hashlib.sha256(b'SQLite format 3\0'+plain[16:]).hexdigest()==before
summary={}
for season,label in [(18,'神童'),(19,'怀旧神兽')]:
 rows=[r for r in records if r['season']==season];summary[label]=dict(cards=len(rows),history_enabled=sum(r['client_history_available'] for r in rows),has_history_rows=sum(r['history_rows']>0 for r in rows),no_history=[dict(spid=r['spid'],name=r['short']) for r in rows if not r['history_rows']],official_evidence_available=sum(r['retained_official_source']=='OK' for r in rows),mapped_source_club_gaps=sum(bool(r['missing_mapped_official_clubs']) for r in rows),unresolved_or_unsupported_source_clubs=sum(bool(r['unmapped_official_clubs'] or r['unsupported_official_clubs']) for r in rows))
result=dict(status='AUDIT_COMPLETE_ELIGIBILITY_INCOMPLETE',definition='Every previously played-for club must activate its club team colour; not merely show a dated career',database_sha256=before,client_ui_database_equal=True,summary=summary,native_proof=dict(source=str(C/'data/ui/libs/Module.big'),source_sha256=sha(C/'data/ui/libs/Module.big'),methods=['PlayerListUtil closure49: history SQL requires A.historyopen=1','PlayerListUtil closure50: false historyopen yields null history']),server_proof='http_config.tc_static/active_teamcolors uses playerhistory regardless of historyopen',full_career_proven=False,formal_files_written=False,state_shop_written=False,gui_used=False,players=records)
(P/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='players'},ensure_ascii=True))
