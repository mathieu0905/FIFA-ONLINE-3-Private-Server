"""Source-backed midfield discussion pool, no game data changes."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
sources={
'early':'https://www.gamersky.com/handbook/201408/459570_2.shtml?tag=wap',
'selection':'https://ol.gamersky.com/z/fifaonline3/201501/514660.shtml',
'positions':'https://eafifa.17173.com/news/10042016/191202520.shtml',
'gullit':'https://ol.gamersky.com/z/fifaonline3/201709/952103.shtml',
'vieira':'https://ol.gamersky.com/z/fifaonline3/201707/933166_2.shtml',
'rijkaard':'https://ol.gamersky.com/z/fifaonline3/201708/948692.shtml',
'kaka':'https://ol.gamersky.com/z/fifaonline3/201609/802235.shtml',
'totti':'https://ol.gamersky.com/z/fifaonline3/201503/534286_3.shtml',
'rooney':'https://ol.gamersky.com/z/fifaonline3/201611/831683_2.shtml',
'sneijder':'https://www.9game.cn/news/1416676.html',
'essien':'https://ol.gamersky.com/z/fifaonline3/201507/618927.shtml',
'diaby':'https://ol.gamersky.com/z/fifaonline3/201510/670984.shtml'}
rows=[
('博格巴','CM/CDM','14W／14T','early','core','高大全能、攻防覆盖；用户点名'),
('亚亚·图雷','CM/CDM','14W','early','core','身体、持球推进与远射；用户点名'),
('埃辛','CDM/CM/RB','08','essien','core','扫荡、灵活、体力兼备；用户点名'),
('费莱尼','CDM/CM','09／14W','selection','core','高空争抢、大模型；用户点名'),
('马蒂奇','CDM','14T','positions','core','拦截覆盖与防空'),
('拉米雷斯','CM/CDM','14W','early','core','速度、跑动与补位'),
('迪亚比','CM/CDM','10','diaby','core','高大但灵活的全能中场'),
('博德梅尔','CM/CDM','10／06U','positions','core','大模型、组织防守兼顾'),
('古斯塔沃','CDM','14W','early','core','早期兽腰与防线屏障'),
('维埃拉','CDM','06W／WL','vieira','core','传奇防守型兽腰'),
('古利特','CM/CAM','WL','gullit','core','全能大模型中场'),
('巴拉克','CM/CAM','欧洲传奇','positions','core','前插、远射与身体对抗'),
('里杰卡尔德','CDM/CB','WL','rijkaard','candidate','拦截、防空、补位与传球'),
('杰拉德','CM/CAM','08／06U','positions','core','全能中场和远射代表'),
('德罗西','CDM/CM','08／06U','positions','core','防守、对抗与出球'),
('比达尔','CM/CDM','14W','early','candidate','高参与度与中场拼抢'),
('赫迪拉','CDM/CM','10W／10U','positions','core','高大后腰、拦截与前插'),
('哈维·阿隆索','CDM/CM','10U','positions','candidate','组织型后腰；代表季另有2019平民攻略明确支持'),
('施魏因施泰格','CM/CDM','10W','positions','candidate','体力、传球和中场对抗'),
('瓜林','CM/CDM','代表季待核','early','candidate','大力远射、身体与中场推进'),
('维特塞尔','CM/CDM','14','selection','candidate','高强妖人、模型和均衡属性'),
('穆萨·登贝莱','CM/CDM','代表季待核','early','candidate','持球护球与中场对抗'),
('瓦尼亚马','CDM','14（史料）','early','candidate','身体与防守型妖人；原14卡模板是否在当前库另核'),
('卡卡','CAM/CF','06W／06U','kaka','core','高速推进、传射与远射'),
('鲁尼','CAM/CF','10U／14W','rooney','core','力量、远射、前场组织'),
('托蒂','CAM/CF','06','totti','core','传射、盘带与丰富进攻特性'),
('斯内德','CAM/CM','10W／08E','sneijder','candidate','双脚和组织型前腰'),
('贝隆','CM/CAM','国米欧洲传奇','positions','candidate','传球与全能型中场')]
cards=[]
for name,pos,seasons,key,priority,reason in rows:
    cards.append(dict(name_zh=name,positions=pos.split('/'),representative_seasons=seasons,source_urls=[sources[key]],priority=priority,reason=reason,
                      evidence_level='card-explicit' if '待核' not in seasons and key not in ('early','rooney') else 'player-explicit/season-to-review'))
out=dict(schema=1,status='DISCUSSION_ONLY_NOT_INSTALLED',count=len(cards),cards=cards,
         notes=['候选人物有FO3史料依据不等于全体玩家公认神兽','同一人只入一张新怀旧卡；列表中的多个季为待选原型','玩法评价是当年评测，不保证当前引擎实机效果','原型赛季选择与现库模板可用性分开核实'])
(R/'midfield-expanded.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print('Midfield discussion pool:',len(cards))
