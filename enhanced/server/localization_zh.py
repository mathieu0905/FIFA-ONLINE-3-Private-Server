"""Optional display-only Chinese adapter. Call install(http_config_module) before main startup.
Does not write state/shop config, translate protocol identifiers, or alter card pools/prices.
"""
import functools, json, pathlib, re

DISPLAY_FIELDS=frozenset(('name','title','description','desc','jerseyname','message','msg','text','subject'))

def install(hc):
    if hc.LANGUAGE!='chi' or getattr(hc,'_chinese_display_installed',False):return
    data=json.loads(pathlib.Path(__file__).with_name('server_display_zh.json').read_text(encoding='utf-8'))
    exact=data['exact'];catalog=data['catalog_by_id'];tables=data['names_by_id']
    original_json=hc._json

    def text(s):
        if s in exact:return exact[s]
        m=re.fullmatch(r'Hadiah login harian - hari ke-(\d+)',s)
        if m:return f'每日登录奖励·第{m[1]}天'
        m=re.fullmatch(r'Login (\d+) hari berturut-turut\. Login lagi besok untuk hadiah hari ke-(\d+)\.',s)
        if m:return f'已连续登录 {m[1]} 天。明日登录可领取第 {m[2]} 天奖励。'
        m=re.fullmatch(r'Hadiah harian (.+)\.',s)
        if m:return '每日奖励：'+exact.get(m[1],m[1])+'。'
        return s

    def walk(o,key=None):
        if isinstance(o,list):return [walk(v,key) for v in o]
        if isinstance(o,tuple):return tuple(walk(v,key) for v in o)
        if isinstance(o,dict):
            # Coach names are user-authored. Both /coaches entries and /coach/me
            # carry a slot and a coach identity; their teamid names the chosen club,
            # not the coach. Preserve the literal name even if it matches a builtin.
            coach_context='slot' in o and ('id' in o or '_id' in o)
            result={k:(v if coach_context and k=='name' else walk(v,k)) for k,v in o.items()}
            # Contextual maps avoid confusing different entities with identical numeric IDs.
            for field,tablename in [('nation','NATIONNAMES_CHI.json'),('league','LEAGUENAMES_CHI.json'),('stadium','STADIUMNAMES_CHI.json')]:
                v=result.get(field)
                if isinstance(v,dict) and 'name' in v:
                    v['name']=tables[tablename].get(str(v.get('id')),v['name'])
            player_or_color=any(field in o for field in ('spid','playerid','teamcolorid'))
            if 'name' in result and not coach_context and not player_or_color:
                teamid=result.get('teamid')
                # coach_me's real team summary has id+ovr, without teamid.
                if teamid is None and key=='summary' and 'ovr' in o:
                    teamid=o.get('id')
                if teamid is not None:
                    result['name']=tables['TEAMNAMES_CHI.json'].get(str(teamid),result['name'])
            return result
        if isinstance(o,str) and key in DISPLAY_FIELDS:return text(o)
        return o

    @functools.wraps(original_json)
    def chinese_json(obj):return original_json(walk(obj))
    hc._json=chinese_json
    original_file=hc.from_file

    @functools.wraps(original_file)
    def chinese_file(path):
        result=original_file(path)
        if result is None:return None
        ctype,raw=result
        if ctype=='application/json':
            return original_json(walk(json.loads(raw)))
        return result
    hc.from_file=chinese_file
    original_apply=hc.apply_shop

    def rename_catalog():
        for table in [hc.PACKS,hc.ITEMS,hc.PACKAGES,hc.MONTHLY]:
            for i,value in list(table.items()):
                entry=catalog.get(str(i))
                # Translate only the original builtin strings; preserve later admin custom names.
                v=list(value);v[0]=text(v[0])
                if isinstance(v[-1],str):v[-1]=text(v[-1])
                table[i]=tuple(v)

    @functools.wraps(original_apply)
    def chinese_apply(cfg=None):
        result=original_apply(cfg);rename_catalog();return result
    hc.apply_shop=chinese_apply
    rename_catalog()
    hc._chinese_display_installed=True
