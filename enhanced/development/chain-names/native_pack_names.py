def clean_pack_definition(host,itemid):
    import copy,re
    out=copy.deepcopy(host.item_def(itemid))
    if itemid not in host.PACKS:return out
    raw=out['name'];top=re.search(r'TOP\s*(\d+)',raw,re.I)
    if '传奇时刻' in raw:family='传奇时刻'
    elif 'ICON' in raw:family='ICON'
    elif '怀旧神兽' in raw or '经典8赛季' in raw:family='经典赛季混合'
    elif '纯传奇' in raw or '经典传奇' in raw:family='传奇混合'
    elif '精选球星' in raw:family='巨星混合'
    else:family=raw.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').split('·')[0]
    grades=[g for g,w in host.pack_grades(itemid) if w>0]
    strength=str(grades[0])+'强' if len(grades)==1 else str(min(grades))+'~'+str(max(grades))+'强'
    kind='指定球员包' if out.get('category')=='DRAFTPACK' else '球员包'
    name=family+('BEST'+top[1] if top else '')+kind+'（'+strength+'）'
    out['name']=name
    description=out.get('description','').replace(raw,name)
    out['description']=description.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').replace('怀旧神兽','经典赛季').replace('经典8赛季','经典赛季')
    return out
