"""Brief player-facing descriptions only; detailed rule helpers stay available."""
import functools,html

def install(h):
    if getattr(h,'_shop_description_brief_installed',False):return
    previous=h.item_def
    esc=lambda text:html.escape(str(text),quote=False)
    seasons={13:'FC移植',91:'世界最佳',93:'世界传奇'}
    for label,codes,_ in getattr(h,'FA_SEASONS',()):
        for code in codes:seasons.setdefault(code,label)

    def pack_text(itemid):
        pool={int(spid) for spid,weight in h.pack_pool(itemid) if weight>0}
        grades=[int(grade) for grade,weight in h.pack_grades(itemid) if weight>0]
        if not pool or not grades:return '当前没有可抽取的球员。'
        cadence=getattr(h,'pack_cadence',None)
        data=cadence.items.get(itemid,{}) if cadence else {}
        if data.get('sale_mode')=='chain_reward_only':
            top=cadence.items.get(97010100,{})
            top_pool={row[0] for tier in top.get('tiers',()) for row in tier['pool']}
            scope='精英赛季球员（不含TOP100）。' if top_pool and pool.isdisjoint(top_pool) else '连锁精选精英球员。'
        elif data.get('rank_basis')=='native_plus1_ovr':
            ranks={row[4] for tier in data['tiers'] for row in tier['pool']}
            scope=f'TOP{len(pool)}球员卡。' if ranks==set(range(1,len(pool)+1)) else '精选赛季球员卡。'
        else:
            codes=sorted({spid//1000000 for spid in pool})
            labels='、'.join(seasons.get(code,str(code)) for code in codes)
            scope=labels+'赛季精选球员。' if len(codes)<=6 and len(labels)<=24 else f'跨{len(codes)}个赛季的精选球员。'
        grade=f'固定+{grades[0]}' if len(grades)==1 else f'强化+{min(grades)}～+{max(grades)}'
        return esc(scope)+'<BR>'+f'{grade}，每包随机获得1名球员。'

    def contents_text(items,prefix=''):
        return '<BR>'.join(prefix+esc(row['staticdata']['name'])+' ×'+str(row['count']) for row in items)

    @functools.wraps(previous)
    def item_def(itemid):
        out=previous(itemid)
        if itemid in h.PACKS:
            out={**out,'description':pack_text(itemid)}
        elif itemid in getattr(h,'MONTHLY',{}):
            text=contents_text(out.get('items',()),'购买获得：')
            daily=contents_text(out.get('dailyitems',()),'每日获得：')
            if daily:text+=f'<BR>有效{out["daily_period"]}天：<BR>'+daily
            out={**out,'description':text}
        elif itemid in getattr(h,'PACKAGES',{}):
            out={**out,'description':contents_text(out.get('items',()))}
        return out

    h.item_def=item_def
    h._shop_description_brief_installed=True
