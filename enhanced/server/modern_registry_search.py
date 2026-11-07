"""Chinese roster aliases for the admin picker; no DB renaming or asset writes."""
from contextlib import closing
from pathlib import Path
import functools,json

def install(hc):
    if getattr(hc,'_modern_registry_search_installed',False):return
    import admin
    previous=admin.API['search']
    registry=Path(hc.HERE)/'gamedata/custom_rosters.json'
    @functools.wraps(previous)
    def search(params):
        q=str(params.get('q') or '').strip()
        if len(q)<2 or not any(ord(c)>127 for c in q):return previous(params)
        aliases={};names={}
        if registry.is_file():
            data=json.loads(registry.read_text(encoding='utf-8'))
            for card in data.get('cards',[]):
                pid=card.get('base_playerid');spid=card.get('fo3_spid');label=card.get('name_zh')
                if isinstance(pid,int) and pid>0 and isinstance(spid,int) and spid>=1000000 and isinstance(label,str) and label:
                    names[spid]=label
                    if q.casefold() in label.casefold():aliases[pid]=label
        ids=sorted(aliases)
        extra=' OR p.playerid IN ('+','.join('?' for _ in ids)+')' if ids else ''
        like='%'+q+'%'
        with closing(hc._db()) as c:
            rows=c.execute(f'''SELECT p.spid,
                    COALESCE(NULLIF(z.full,''),NULLIF(z.short,''),n.full_eng,n.full,n.short),
                    {hc.POSOVR},p.preferredposition1
                FROM players p JOIN nameseng n ON n.playerid=p.playerid
                    LEFT JOIN nameschi z ON z.playerid=p.playerid
                WHERE p.spid>=1000000 AND
                    (n.full LIKE ? OR n.short LIKE ? OR n.full_eng LIKE ? OR n.short_eng LIKE ?
                     OR z.full LIKE ? OR z.short LIKE ? OR z.full_eng LIKE ? OR z.short_eng LIKE ?{extra})
                ORDER BY 3 DESC,p.spid LIMIT 60''',([like]*8)+ids).fetchall()
        return {'rows':[dict(spid=s,name=names.get(s,name),season=s//1000000,ovr=ovr,
            pos=admin.POS_NAMES[pos] if 0<=pos<28 else '?',market=hc.on_market(s),price=hc.card_price(s))
            for s,name,ovr,pos in rows]}
    admin.search=search;admin.API['search']=search
    hc._modern_registry_search_installed=True
