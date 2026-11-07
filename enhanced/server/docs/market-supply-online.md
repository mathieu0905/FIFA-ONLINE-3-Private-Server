# 市场供货在线配置

首次接入市场后台代码需要在游戏自行结束后正常重启一次。接入后概率、单次供货数量、常规刷新周期、重点供货轮换周期、后台检查间隔和高强化分档配置均可在线调整，不重启服务，不重载模块。

正式目录命令：

    .venv\Scripts\python.exe -B market_supply_control.py
    .venv\Scripts\python.exe -B market_supply_control.py --set D:\path\settings.json --expected-revision <刚读取的revision>

JSON 文件仅包含读取结果的 settings 对象。概率使用 0..1，数量为整数；regular_counts 对应 +1..+10；regular_chances 分 low/mid/high/elite 四档，按 +1、1级能力分段（≤80、81..86、87..90、≥91）。IM 最高 +5 是独立边界，不能被在线概率绕过。

rare_overrides 可按 elite_15、elite_16 等键设置完整规则：period_seconds、slots、chance、quantity。slots 是该周期内全档共享的抽取机会，quantity 是一次成功机会的卡数，chance 是单次机会概率。省略的键使用原有按池大小缩放的供货模型；概率不是每位球员独享。

只读接口 GET http://127.0.0.1:8088/api/market_supply_config 返回 revision、active_revision、error、settings。写入接口 POST /api/market_supply_config_set 使用 X-FO3-Admin: 1，正文为 {revision, settings}；同一 STATE_LOCK 内校验磁盘版本，原子保存后激活。多人编辑时旧 revision 拒绝，避免覆盖新设置。配置位于 gamedata/market-supply-config.json，属于可变在线配置，不纳入固定文件哈希；每次启动仍检查其格式和数值范围。配置不改 state/shop，不调用价格模型，也不重置行情数据库。

常规当前挂单保留价格、余量和到期时间，修改周期不能提前补回售罄卡。新概率/数量在旧书到期后使用。稀有已抽取结果（包括售罄、已展示和未来机会）保留；当前周期的供货机会增加时，仅增加尚未开始的时段，错过的时段不追补，失败机会不重抽。减量、概率调整、单次卡数和周期的完整规则从下一新批次使用。轮换周期在线读取；后台间隔从当前一次等待完成后使用。

外部原子替换配置文件也可由后台下一 tick 读取；建议使用带 revision 的接口。非法文件保留运行中最后一份有效配置并显式报告 error；新进程启动预检会拒绝非法文件，不能把回退到默认配置称为已应用新设置。

验证证据只代表配置/事务/供货回归及正式接口结果；游戏显示和比赛另行验收。后台对象不属于现有 ABI2 业务路由，禁止用热包修改类、重跑 install hooks、重启/断线伪装热更新。


## 挂单存续与刷卡频率分离

rare_listing_seconds 和 npc_listing_seconds 默认均为1800秒，可在线调整。每分钟概率上新不再意味着一分钟撤单。未售出、未过期的稀有挂单在五分钟批次换代时原样转入现有库存账本，保留价格、数量和到期时间；购买仍从同一库存扣减。迁移只延长仍有效的旧挂单，不恢复已售或已过期卡。新配置兼容缺少这两项的既有JSON，首次接入在游戏结束后重启，之后调参不重启。
