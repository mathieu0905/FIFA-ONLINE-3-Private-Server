"""Research artifact only: exact existing identities and historical card templates."""
from pathlib import Path
import ast,hashlib,json,sqlite3
ROOT=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
BASE='https://ol.gamersky.com/z/fifaonline3/'
sources={
 'beasts':BASE+'201611/831683.shtml',
 'pro':'https://eafifa.17173.com/news/06142016/223233155_all.shtml',
 'manager':'https://www.gamersky.com/handbook/201408/459570_2.shtml?tag=wap',
 'touch':'https://www.gamersky.com/handbook/201412/501840.shtml?tag=wap',
 'drogba':BASE+'201610/823883.shtml',
 'essien':BASE+'201507/618927.shtml',
 '11妖人':BASE+'201511/684951_16.shtml',
 'emenike':'https://www.gamersky.com/handbook/201412/500222.shtml',
 'smalling':BASE+'201606/764169_12.shtml',
 'chelsea':BASE+'201609/812764_11.shtml',
 'goalkeepers':BASE+'201606/762021.shtml',
 'gkdetail':BASE+'201509/660909.shtml',
 'fullbacks':BASE+'201503/533332_2.shtml',
 'clichy':BASE+'201707/935333_4.shtml',
 'sissoko':'https://www.ppsport.com/360news/news/1106753.html',
 'midfield':'https://eafifa.17173.com/news/10042016/191202520.shtml',
 'diaby':BASE+'201510/670984.shtml',
 'bodmer':'https://www.gamersky.com/handbook/201412/504411.shtml',
}
# zh, exact FIFA PID, existing season code, historical label, group, evidence, certainty, reason
items=[
('博格巴',195864,77,'14W','MID','manager','player-explicit/template-design','高大全能中场，用户点名核心；新卡另建，不动已修改WB'),
('亚亚·图雷',20289,77,'14W','MID','manager','player-explicit/template-design','用户点名核心，早期全能兽腰代表'),
('瓦拉内',201535,77,'14W','DEF','touch','player-explicit/template-design','用户点名核心，速度型高大中卫'),
('埃辛',45674,8,'08','MID','essien','card-explicit','用户点名核心，08水牛模板保留灵活和拦截轮廓'),
('费莱尼',176944,9,'09','MID','pro','card-explicit','用户点名核心，09赛季获职业选秀青睐的空霸中场'),
('马蒂奇',191202,53,'14T','MID','midfield','card-explicit','高大防守支点，史料直接推荐14T'),
('拉米雷斯',184943,77,'14W','MID','chelsea','card-explicit','高体力扫荡，14W车套边路/中场实用卡'),
('迪亚比',163423,10,'10','MID','diaby','card-explicit','10迪亚比专项评测明确推荐，高模型多面手'),
('古斯塔沃',185221,77,'14W','MID','manager','card-explicit','2014年FO3经理人攻略直接推荐W古斯塔沃，防守扫荡路线；替换版本来源不明的西索科'),
('德罗巴',31432,69,'10U','ATT','drogba','card-explicit','用户明确允许；全能魔兽，保留10U模型和头球特点'),
('伊布拉希莫维奇',41236,11,'11','ATT','pro','card-explicit','少量标志性老强卡，11赛季模型与花式特色'),
('本泽马',165153,77,'14W','ATT','beasts','player-explicit/template-design','早期贴吧神兽，跑位型终结者；避免只挑传奇身份'),
('卢卡库',192505,77,'14W','ATT','beasts','player-explicit/template-design','旧引擎力量中锋代表'),
('本特克',184111,77,'14W','ATT','manager','player-explicit/template-design','高模型空战中锋，补充民间实战神兽'),
('哲科',180930,10,'10','ATT','pro','card-explicit','史料明确提及10哲科的模型优势'),
('阿德巴约',53050,8,'08','ATT','pro','card-explicit','08阿德巴约获职业选秀选择的高中锋'),
('敦比亚',188428,11,'11','ATT','11妖人','card-explicit','11赛季前场妖人，速度反击路线'),
('埃梅尼克',199835,14,'14','ATT','emenike','card-explicit','14卡专项妖人评测支持，速度力量型冲击手'),
('伊巴尔博',204550,77,'14W','ATT','manager','player-explicit/template-design','经理人推荐伊巴波，原卡选14W属设计'),
('雷米',179527,11,'11','ATT','11妖人','card-explicit','11前场妖人名单明确收录，补反击型锋线'),
('胡尔克',189362,11,'11','WING','11妖人','card-explicit','11浩克，保留内切重炮和对抗特色'),
('法尔范',158133,11,'11','WING','beasts','player-explicit/template-design','早期法尔范/胡尔克边路组合的怀旧代表，选11模板属设计'),
('拉维奇',159065,11,'11','WING','pro','card-explicit','11拉维奇获职业选秀青睐，灵巧突破路线'),
('博德梅尔',51123,10,'10','MID','bodmer','card-explicit','10博德梅尔在2014年经理人阵型攻略中直接列为CM/CDM推荐，更贴近实战神兽主题'),
('贝纳蒂亚',177509,77,'14W','DEF','touch','card-explicit','W贝内蒂亚，早期强力防守神兽'),
('杰罗姆·博阿滕',183907,77,'14W','DEF','beasts','player-explicit/template-design','速度与模型兼具，保留旧卡的防守轮廓'),
('大卫·路易斯',179944,77,'14W','DEF','chelsea','card-explicit','14W路易斯，侵略型出球中卫'),
('曼加拉',190531,77,'14W','DEF','touch','design-supplement','高模型回追中卫补充；尚缺同卡明确史料，标注设计补充'),
('斯莫林',189881,69,'10U','DEF','smalling','card-explicit','10U高球正面拦截模板，有专项实战评测'),
('科斯切尔尼',165229,77,'14W','DEF','pro','card-explicit','W科斯切尔尼作为性价比高强中卫被推荐'),
('麦孔',135455,10,'10','DEF','touch','card-explicit','10麦孔是旧版典型右路神兽'),
('阿拉巴',197445,77,'14W','DEF','fullbacks','card-explicit','W阿拉巴，史料明确推荐的左路全能卡'),
('克里希',152554,23,'LP','DEF','clichy','card-explicit','LP克里希作为曼城边卫被推荐，补齐左后卫深度'),
('切赫',48940,7,'07','GK','goalkeepers','card-explicit','07切赫为历史门将名单明确选项'),
('诺伊尔',167495,77,'14W','GK','goalkeepers','card-explicit','14W诺伊尔为当年常见顶级门将模板'),
('库尔图瓦',192119,77,'14W','GK','gkdetail','player-explicit/template-design','高大门将模型代表；原文重点14普通卡，本库对应优先用现有14W模板，须标设计选择'),
]
tree=ast.parse((S/'http_config.py').read_text('utf-8'))
weights=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets))
roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split();pos='GK SW RWB RB RCB CB LCB LB LWB RDM CDM LDM RM RCM CM LCM LM RAM CAM LAM RF CF LF RW RS ST LS LW'.split()
cards=[]
for zh,pid,sid,label,group,source,certainty,reason in items:
    spid=sid*1000000+pid;r=db.execute('SELECT * FROM players WHERE spid=?',(spid,)).fetchone()
    assert r is not None,(zh,spid)
    row=dict(r);name=db.execute('SELECT full_eng FROM nameseng WHERE playerid=?',(pid,)).fetchone()[0]
    ovr=sum(row[k]*w for k,w in weights[roles[row['preferredposition1']]].items())//100
    cards.append(dict(name_zh=zh,name_en=name,base_playerid=pid,template_spid=spid,template_season_code=sid,template_season_label=label,
                      group=group,primary_position=pos[row['preferredposition1']],source_url=sources[source],evidence_level=certainty,
                      selection_reason=reason,base_ovr=ovr,height=row['height'],weight=row['weight'],source_row_sha256=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
assert len(cards)==36 and len({c['base_playerid'] for c in cards})==36
assert next(c for c in cards if c['name_zh']=='德罗巴')['template_spid']==69031432
result=dict(schema=1,status='RESEARCH_ROSTER_NOT_INSTALLED',count=len(cards),sources=sources,cards=cards,
            constraints=['保留全部旧卡；怀旧赛季创建新SPID','核心按用户点名；少收已成传奇身份球员','具体原卡有史料则标card-explicit；仅人物依据与设计补充另标，不伪称神兽共识','原始库14普通卡缺失的身份不冒用当前FC移植卡','原季模型/惯用脚/花式/隐藏优先保留，仅主属性升至UL档由主任务设计'])
(ROOT/'roster36.next.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
(ROOT/'roster36.next.json').replace(ROOT/'roster36.json')
print(json.dumps(dict(count=len(cards),groups={g:sum(c['group']==g for c in cards) for g in set(c['group'] for c in cards)},names=[c['name_zh'] for c in cards]),ensure_ascii=True))
