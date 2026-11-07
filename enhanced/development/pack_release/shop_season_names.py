"""Exact season lists for the currently issued shop packs; presentation only.

Install after shop_description_brief. Labels use the native season strings and
the published FO3 season catalogue, not the old CP/LP/CC mistranslations.
"""
import functools,html

SEASONS={13: 'FC精选（FC精选移植）', 21: 'Tiger（终极猛虎）', 22: 'CP（队长）', 23: 'LP（忠诚）', 24: 'CC（洲际冠军）', 27: 'EL（欧洲传奇）', 28: 'UB（终极最佳）', 30: 'UL（终极传奇）', 31: 'CEL-A（欧洲联赛传奇A）', 33: 'CEL-B（欧洲联赛传奇B）', 35: '16EC（欧洲杯/美洲杯）', 48: 'MUL（曼联传奇）', 53: '14T（年度最佳）', 55: 'MUA（曼联大使）', 91: 'WB（世界最佳）', 93: 'WL（世界传奇）'}
NAMES={97010001: 'CP/LP/CC等5季·随机+5～+7', 97010002: 'CP/LP/CC等8季·随机+7～+9', 97010010: '前锋8赛季·随机+7～+9', 97010011: '中场6赛季·随机+7～+9', 97010012: '后卫5赛季·随机+7～+9', 97010013: '门将5赛季·随机+7～+9', 97010004: '传奇6赛季·随机+8～+10', 97010005: 'EL/UL/CEL-A/WL·+8～+10', 97010006: '经典8赛季·印记固定+8', 97010100: '14赛季TOP100·随机固定+8', 97010130: '6赛季TOP30·随机固定+9', 97010110: 'EL/UL/WL TOP10·随机+9', 97010007: 'CP/LP/CC/WB·固定+10', 97010209: '经典8赛季·连锁固定+9'}

def install(h):
    if getattr(h,'_shop_season_names_installed',False):return
    if set(h.pack_cadence.items)!=set(NAMES):raise ValueError('Review season-name profile for the new issued catalogue')
    previous=h.item_def;profile={}
    for itemid,name in NAMES.items():
        pool={int(spid) for spid,weight in h.pack_pool(itemid) if weight>0}
        codes=sorted({spid//1000000 for spid in pool})
        if not pool or any(code not in SEASONS for code in codes):raise ValueError('Unverified or empty season list for '+str(itemid))
        grades=[int(grade) for grade,weight in h.pack_grades(itemid) if weight>0]
        if not grades:raise ValueError('Empty grade list for '+str(itemid))
        grade=f'固定+{grades[0]}' if len(grades)==1 else f'强化+{min(grades)}～+{max(grades)}'
        season_lines = ['赛季范围（仅包含以下赛季）：']
        for offset in range(0, len(codes), 2):
            season_lines.append('；'.join(SEASONS[code] for code in codes[offset:offset+2]))
        action = '每包随机获得1名球员；' + grade + '。'
        if len(grades) > 1: action += '最高强化不是保底。'
        extra = []
        if itemid in (97010100,97010130,97010110): extra.append('TOP按本期原生等级1、+1能力排名；每包随机抽1人，不是自选。')
        if itemid == 97010209: extra.append('连锁第3档专属；不含本期能力TOP100。')
        description = '<BR>'.join([action] + season_lines + extra)
        profile[itemid]={'name':name,'description':html.escape(description,quote=False).replace('&lt;BR&gt;','<BR>')}

    @functools.wraps(previous)
    def item_def(itemid):
        out=previous(itemid)
        if itemid in profile:out={**out,**profile[itemid]}
        return out
    h.item_def=item_def
    h._shop_season_names_installed=True
