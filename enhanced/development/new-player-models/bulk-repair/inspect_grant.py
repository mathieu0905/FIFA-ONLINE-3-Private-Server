import json,pathlib,urllib.request
R=pathlib.Path(__file__).resolve().parent;O=R/'grant20';O.mkdir(exist_ok=True)
def get(name):
    with urllib.request.urlopen('http://127.0.0.1:8088/api/'+name,timeout=15) as r:return json.load(r)
summary=get('summary');players=get('players');state=pathlib.Path('D:/FO3ID/server/gamedata/state.json').read_bytes();(O/'before-state-observed-readonly.json').write_bytes(state)
(O/'before-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');(O/'before-players.json').write_text(json.dumps(players,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=True));models=json.loads(pathlib.Path('D:/FO3ID/server/gamedata/player-imports.json').read_text('utf8'))['models'];wanted={p['spid'] for p in models};print(json.dumps([p for p in players['players'] if p['spid'] in wanted],ensure_ascii=True));print('count',len(players['players']))
