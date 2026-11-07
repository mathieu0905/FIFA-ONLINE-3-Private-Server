import json,pathlib,sqlite3,sys
sys.path[:0]=['D:/FO3ID/server/tools/re']
import bigdir
C=pathlib.Path('D:/FO3ID/32795');R=pathlib.Path(__file__).resolve().parent
names={n for n,*_ in bigdir.entries(C/'data/data_4.big')}
probes=['data/sceneassets/heads/head_'+str(i)+'_'+str(cls)+'.rx3' for i in [250,1505,5467,2001,167198,530] for cls in [0,1]]
print('head resources',[(n,n in names) for n in probes])
source=pathlib.Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/modern_player_integration_v2')
for p in source.glob('*.py'):
    text=p.read_text('utf8')
    for n,line in enumerate(text.splitlines()):
        if 'skillmove' in line.lower():print(str(p),n+1,line)
catalog=json.loads(pathlib.Path('D:/FO3QA/modern_player_integration_v2/model19-v4/model_catalog24.json').read_text('utf8'))
print('catalog acquired',json.dumps(next(p for p in catalog['players'] if p['playerid']==252371),ensure_ascii=True)[:2500])
