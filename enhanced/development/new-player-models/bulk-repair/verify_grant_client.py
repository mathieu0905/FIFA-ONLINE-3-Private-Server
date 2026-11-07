import json,pathlib,ssl,urllib.request
R=pathlib.Path(__file__).resolve().parent/'grant20';grant=json.loads((R/'result.json').read_text('utf8'));wanted={p['id']:p for p in grant['selected']}
request=urllib.request.Request('https://127.0.0.1/coach/me',headers={'Host':'APSEODESK172'})
with urllib.request.urlopen(request,context=ssl._create_unverified_context(),timeout=20) as r:payload=json.load(r)
found={}
def walk(value):
    if isinstance(value,dict):
        identity=str(value.get('_id') or value.get('id') or '')
        if identity in wanted and value.get('spid')==wanted[identity]['spid'] and 'grade' in value:found[identity]=value
        for item in value.values():walk(item)
    elif isinstance(value,list):
        for item in value:walk(item)
walk(payload)
assert set(found)==set(wanted) and all(p['grade']==20 and p.get('state')=='first' for p in found.values())
result=dict(status='LIVE_GAME_COACH_PAYLOAD_PLUS20_FIRST_TEAM_PASS',coach='ggmu',selected_count=len(found),all_grade20=True,all_first_team=True,gui_used=False,native_rendering_verified=False)
(R/'client-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
