"""Display registry for verified dual-end imported cards; no data mutation or giveaways."""
import json,pathlib,functools

def install(hc):
    if getattr(hc,'_custom_roster_installed',False): return
    import admin
    registry=pathlib.Path(hc.HERE)/'gamedata'/'custom_rosters.json'
    def read():
        try:return json.loads(registry.read_text(encoding='utf-8'))
        except FileNotFoundError:return {'seasons':[],'cards':[]}
    original=admin.API['shop']
    @functools.wraps(original)
    def shop(params):
        out=original(params);seen={s['code'] for s in out['seasons']}
        out['seasons'] += [{'code':s['id'],'label':s['label']} for s in read()['seasons'] if s['id'] not in seen]
        return out
    admin.API['shop']=shop
    admin.READ_ONLY.add('roster_custom_cards')
    admin.API['roster_custom_cards']=lambda params:read()
    hc._custom_roster_installed=True
