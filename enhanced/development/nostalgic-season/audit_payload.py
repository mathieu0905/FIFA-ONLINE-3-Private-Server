from pathlib import Path
import json,sqlite3,sys
sys.stdout.reconfigure(encoding='utf-8');R=Path(__file__).resolve().parent
s=json.loads((R/'roster-audit.json').read_text('utf-8'));d=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);d.row_factory=sqlite3.Row
for c in s['cards']:
 r=d.execute('select * from players where spid=?',(c['template_spid'],)).fetchone()
 print(c['name_zh'],c['template_label'],c['template_spid'],'pos',r['preferredposition1'],'team',r['teamid'],'size',r['height'],r['weight'],'ovr',c['base_ovr'],'->',c['target_ovr'],'lift',c['stat_lift'],'99s',sum(v==99 for k,v in c['fo3_overrides'].items() if k not in ('overallrating','preferredposition1')))
reg=json.loads(Path('D:/FO3ID/server/gamedata/custom_rosters.json').read_text('utf-8'));print('registered seasons',[(r['id'],r['label']) for r in reg['seasons']])
