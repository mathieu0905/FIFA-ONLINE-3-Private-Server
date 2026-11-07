"""Descriptions only for the new five-stage quality track and its exclusive +9.

Install after quality_chain, the frozen base descriptions and native icon adapter.
Other issued product descriptions and all economy/state rules are untouched.
"""
import functools,html

GROUPS={'legend_week':'每周传奇','peak_week':'每周巅峰','classic_month':'经典精选固定+10月供应'}

def install(h):
    if getattr(h,'_quality_chain_descriptions_installed',False):return
    tracks=h.quality_chain_tracks
    steps={int(i):(int(root),index,data) for root,data in tracks.items() for index,i in enumerate(data['steps'])}
    exclusive={i for i,d in h.pack_cadence.items.items() if d.get('sale_mode')=='chain_reward_only'}
    original=h.item_def
    esc=lambda value:html.escape(str(value),quote=False)
    def pack_description(itemid):
        description=h.describe_player_pack(itemid)
        if itemid in exclusive:
            pool={row[0] for tier in h.pack_cadence.items[itemid]['tiers'] for row in tier['pool']}
            top100={row[0] for tier in h.pack_cadence.items[97010100]['tiers'] for row in tier['pool']}
            description=description.replace('不包含本期能力前100。','')
            if pool.isdisjoint(top100):description+='<BR>不包含原生等级1、+1能力TOP100赛季卡。'
            description+='<BR>仅通过本期高品质连锁第3档获得，不在商城单独出售。'
        return description
    def quota_lines(itemid):
        units,closed=h.pack_cadence.policy(itemid)
        lines=[]
        for group,used in sorted(units.items()):
            period='自然WIB月' if group.endswith('_month') else '每周' if group.endswith('_week') else '每日'
            cap=h.pack_cadence.config['limits'][group]
            lines.append(f'{GROUPS.get(group,esc(group))}：全账号{period}{cap}份，本档占{used}份，与商城和其他礼包共享。')
        if not units:lines.append('本档不占每日、每周或每月共享供应额度。')
        if any(g.endswith('_week') for g in units):lines.append('周供应每周一北京时间凌晨1点刷新；余量不足时须等待，不能超额购买。')
        if any(g.endswith('_month') for g in units):lines.append('月供应按自然WIB月计算，每月月初北京时间凌晨1点刷新；本月已用则须等下月。')
        if closed:lines.append('当前规则下本档暂不可购买，请等待发行或供应恢复。')
        return lines
    def describe_stage(itemid,out):
        root,index,track=steps[itemid]
        price=h.product_price(itemid,1)
        cumulative=sum(h.product_price(i,1) for i in track['steps'][:index+1])
        lines=[esc(out['name']),f'新一期高品质连锁第{index+1}/5档；本档实际价格{price:,}点券。',
               f'从第1档买到本档累计{cumulative:,}点券；本期五档实际总价{track["total_cash"]:,}点券。',
               '全账号每档终生一次，由本期首次购买的经理继续购买；切换经理或重建经理不重置已购次数。',
               '必须按第1至第5档顺序解锁；本期奖励版本固定，不随商城位置主题轮换。',
               '本档完整奖励如下：卡包发到背包，需自行开启，不会自动抽球员。']
        for child in out['items']:
            i,count=child['itemid'],child['count']
            lines.append(f'{esc(child["staticdata"]["name"])} ×{count}（每包开启获得1名球员）。')
            description=pack_description(i)
            # Omit standalone/reference prices entirely. The exclusive +9 has
            # an internal compatibility valuation, never an advertised price.
            selected=('本发行卡池','实际赛季','本期排名','进阶档','常规档','基础OVR','先按档位',
                      '定向位置','强化概率','最低+','最高+','固定获得','连续','保底只','每次成功开包',
                      '不包含','仅通过')
            lines.extend(line for line in description.split('<BR>') if line.startswith(selected))
        lines.extend(quota_lines(itemid))
        lines.append('规划提示：第4、5档都占每周巅峰供应；每周总量1份，须分不同WIB周购买。')
        lines.append('末档另占经典固定+10的自然月供应，若本月已在商城用掉，须等下月；请提前预留共享额度。')
        lines.append('按点券余额逐步推进；共享供应或余额不足时等待，不保证每天连续购买或固定天数买齐。')
        return '<BR>'.join(lines)
    @functools.wraps(original)
    def item_def(itemid):
        out=original(itemid)
        if itemid in steps:out={**out,'description':describe_stage(itemid,out)}
        elif itemid in exclusive:out={**out,'description':pack_description(itemid)}
        return out
    h.item_def=item_def
    h._quality_chain_descriptions_installed=True
