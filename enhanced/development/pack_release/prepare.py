"""Build and verify an isolated release from the current formal server."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import struct
import sys
import zlib

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'D:\FO3ID\server')
WORK = Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online')
SERVER = ROOT / 'sandbox/server'
SERVER.mkdir(parents=True, exist_ok=True)
for p in [*SOURCE.glob('*.py'), *SOURCE.glob('*.json')]:
    shutil.copyfile(p, SERVER / p.name)
for directory in ('gamedata', 'responses', 'admin', 'tools'):
    shutil.copytree(SOURCE / directory, SERVER / directory, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.log', '*.bak*', 'migration-backups', 'replays'))
os.environ.update(FO3_GAME=r'D:\FO3ID\32795', FO3_LANGUAGE='chi', FO3_MAX_GRADE='20', FO3_ADMIN_PORT='0')
sys.argv = ['http_config.py']
sys.path.insert(0, str(SERVER))
import http_config as h

old_definitions = {i: h.item_def(i) for i in h.PACKS}
old_pools = {i: h.pack_pool(i) for i in h.PACKS}
old_grades = {i: h.pack_grades(i) for i in h.PACKS}

names = {
    97010001: 'CP/LP/CC等5季·随机+5～+7',
    97010002: 'CP/LP/CC等8季·随机+7～+9',
    97010010: '前锋8赛季·随机+7～+9', 97010011: '中场6赛季·随机+7～+9',
    97010012: '后卫5赛季·随机+7～+9', 97010013: '门将5赛季·随机+7～+9',
    97010004: '传奇6赛季·随机+8～+10', 97010005: 'EL/UL/CEL-A/WL·+8～+10',
    97010006: '经典8赛季·印记固定+8', 97010100: '14赛季TOP100·随机固定+8',
    97010130: '6赛季TOP30·随机固定+9', 97010110: 'EL/UL/WL TOP10·随机+9',
    97010007: 'CP/LP/CC/WB·固定+10', 97010209: '经典8赛季·连锁固定+9',
}
old = (SOURCE / 'shop_season_names.py').read_text(encoding='utf-8')
old = old.replace('import functools,html', 'import functools,html')
parsed = ast.parse(old)
assignment = next(n for n in parsed.body if isinstance(n, ast.Assign) and n.targets[0].id == 'NAMES')
lines = old.splitlines(keepends=True)
lines[assignment.lineno-1:assignment.end_lineno] = ['NAMES=' + repr(names) + '\n']
old = ''.join(lines)
spellings = {13:'FC精选（FC精选移植）',21:'Tiger（终极猛虎）',22:'CP（队长）',23:'LP（忠诚）',
    24:'CC（洲际冠军）',27:'EL（欧洲传奇）',28:'UB（终极最佳）',30:'UL（终极传奇）',
    31:'CEL-A（欧洲联赛传奇A）',33:'CEL-B（欧洲联赛传奇B）',35:'16EC（欧洲杯/美洲杯）',
    48:'MUL（曼联传奇）',53:'14T（年度最佳）',55:'MUA（曼联大使）',91:'WB（世界最佳）',93:'WL（世界传奇）'}
parsed = ast.parse(old)
assignment = next(n for n in parsed.body if isinstance(n,ast.Assign) and n.targets[0].id=='SEASONS')
lines=old.splitlines(keepends=True)
lines[assignment.lineno-1:assignment.end_lineno]=['SEASONS='+repr(spellings)+'\n']
old=''.join(lines)
start = old.index("        description='赛季：'")
end = old.index('\n    @functools.wraps', start)
old = old[:start] + '''        season_lines = ['赛季范围（仅包含以下赛季）：']
        for offset in range(0, len(codes), 2):
            season_lines.append('；'.join(SEASONS[code] for code in codes[offset:offset+2]))
        action = '每包随机获得1名球员；' + grade + '。'
        if len(grades) > 1: action += '最高强化不是保底。'
        extra = []
        if itemid in (97010100,97010130,97010110): extra.append('TOP按本期原生等级1、+1能力排名；每包随机抽1人，不是自选。')
        if itemid == 97010209: extra.append('连锁第3档专属；不含本期能力TOP100。')
        description = '<BR>'.join([action] + season_lines + extra)
        profile[itemid]={'name':name,'description':html.escape(description,quote=False).replace('&lt;BR&gt;','<BR>')}
''' + old[end:]
(ROOT / 'shop_season_names.py').write_text(old, encoding='utf-8')

SEASONS = {
    '07': '2007普通赛季', '06': '2006普通赛季', '06U': '2006更新赛季', '06WC': '2006世界杯',
    '08': '2008普通赛季', '08E': '2008欧洲杯', '09': '2009普通赛季', '10': '2010普通赛季',
    '10U': '2010更新赛季', '10WC': '2010世界杯', '11': '2011普通赛季', '14': '2014普通赛季',
    '14WC': '2014世界杯', '14T': '2014年度最佳', '15': '2015普通赛季', '16': '2016普通赛季',
    '17': '2017普通赛季', '16EC': '2016欧洲杯/美洲杯', '16TH': '2016泰国赛季',
    'WB': '世界最佳', 'WL': '世界传奇', 'UB': '终极最佳', 'UL': '终极传奇', 'EL': '欧洲传奇',
    'LP': '忠诚', 'CP': '队长', 'CC': '洲际冠军', '17TH': '2017泰国赛季', 'TCO92': '92班',
    'MUA': '曼联大使', 'ML': '马来西亚传奇', 'TL': '泰国传奇', 'VL': '越南传奇',
    'CL': '中国传奇', 'KL02': '2002韩国传奇', 'CEL': '欧洲联赛传奇', 'U23': '23岁以下',
    'KXI': '韩国最佳十一人', 'MUL': '曼联传奇', 'VS': '越南之星', 'FC精选': 'FC精选移植',
}
market = set(h.market_spids())
ratings = h.card_ovrs(market)
ranked = sorted(market, key=lambda s: (-ratings[s], s))
with sqlite3.connect('file:' + (SOURCE / 'gamedata/fifadb.sqlite').as_posix() + '?mode=ro', uri=True) as db:
    records = {s: {'team': t, 'league': l, 'name': ' '.join(str(n or '') for n in (en, ind))}
               for s, t, l, en, ind in db.execute('SELECT p.spid,p.teamid,p.leagueid,e.full,i.full FROM players p LEFT JOIN nameseng e ON e.playerid=p.playerid LEFT JOIN namesind i ON i.playerid=p.playerid')}

config = dict(schema=1, edition='20261106-season-choice-v1', token_key=secrets.token_hex(32),
              limits={'season_day': 10, 'legend_day': 2, 'choice_week': 2}, items={})
groups = [('07', (7,))] + [(label, codes) for label, codes, _ in h.FA_SEASONS] + [('FC精选', (13,))]
legend_codes = {27, 30, 31, 33, 48, 93}

def add(itemid, title, candidates, mode, season_labels, supply, order):
    assert candidates
    candidates = sorted(candidates, key=lambda s: (-ratings[s], s))
    chinese = '、'.join(f'{label}（{SEASONS[label]}）' for label in season_labels)
    if mode == 'random':
        cost = max(100, min(12000, math.ceil(sum(h.card_price(s, 1) for s in candidates)/len(candidates)/100000 * 1.1)))
        action = f'从{len(candidates)}张赛季卡中等概率随机获得1名球员，固定+1。'
    else:
        cost = max(500, min(96000, math.ceil(max(h.card_price(s, 1) for s in candidates)/100000 * 1.5)))
        action = f'从{len(candidates)}张赛季卡中任选1名球员，固定+1。不是随机抽取。'
    quota = '所有自选包全账号每周共享2包。' if supply == 'choice_week' else '纯传奇随机包全账号每日共享2包。' if supply == 'legend_day' else '单赛季随机包全账号每日共享10包。'
    lines = [action, '包含赛季：' + chinese + '。']
    if 'TOP10' in title: lines.append('TOP10按本期原生等级1、+1能力排序，同分按卡编号排序；同人不同赛季分别排名。')
    if mode == 'choice': lines.append('背包使用后进入球员选择界面，选定1人再确认；取消不消耗。')
    lines.append(quota + '北京时间凌晨1点刷新；周限购每周一刷新。')
    config['items'][str(itemid)] = dict(name=title, pool=candidates, mode=mode, price=cost,
        seasons=sorted({s//1000000 for s in candidates}), icon='2000006', supply=supply, order=order,
        description='<BR>'.join(lines), search={str(s): records[s] for s in candidates} if mode == 'choice' else {})

for index, (label, codes) in enumerate(groups):
    candidates = [s for s in ranked if s//1000000 in codes]
    if not candidates:
        continue
    display = label + SEASONS[label] if label in ('CP','LP','CC','WL','WB','EL','UL','MUL','MUA','UB') else label
    add(97100000 + min(codes), display + '·随机+1', candidates, 'random', [label],
        'legend_day' if set(codes) <= legend_codes else 'season_day', 30 + index)
    if label in ('CP', 'LP', 'CC', 'WB', 'WL', 'UL', 'EL'):
        add(97200000 + min(codes), display + '·球员自选+1', candidates, 'choice', [label], 'choice_week', 10 + index)

legends = [s for s in ranked if s//1000000 in legend_codes]
legend_labels = ['EL','UL','CEL','MUL','WL']
add(97100900, '纯传奇合集·随机+1', legends, 'random', legend_labels, 'legend_day', 0)
add(97200900, '纯传奇合集·球员自选+1', legends, 'choice', legend_labels, 'choice_week', 1)
add(97200910, '纯传奇TOP10·10选1·+1', legends[:10], 'choice',
    [label for label,codes in groups if any(s//1000000 in codes for s in legends[:10])], 'choice_week', 2)
add(97200911, '全服TOP10·10选1·+1', ranked[:10], 'choice',
    [label for label,codes in groups if any(s//1000000 in codes for s in ranked[:10])], 'choice_week', 3)
for label, codes in [('WL',(93,)), ('WB',(91,))]:
    candidates = [s for s in ranked if s//1000000 in codes][:10]
    add(97201000+codes[0], label + SEASONS[label] + 'TOP10·10选1·+1', candidates, 'choice', [label], 'choice_week', 4)
config['hash'] = __import__('pack_catalogue', fromlist=['signature']).signature(config)
(ROOT / 'pack_catalogue.json').write_text(json.dumps(config, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
for filename in ('pack_catalogue.py', 'shop_season_names.py'):
    shutil.copyfile(ROOT / filename, SERVER / filename)
shutil.copyfile(ROOT / 'pack_catalogue.json', SERVER / 'gamedata/pack_catalogue.json')
source = (SERVER / 'http_config.py').read_text(encoding='utf-8')
source = source.replace('if __name__ == "__main__":\n    # Windows', 'import pack_catalogue\npack_catalogue.install(sys.modules[__name__])\n\nif __name__ == "__main__":\n    # Windows')
assert source.count('pack_catalogue.install') == 1
(ROOT / 'http_config.py').write_text(source, encoding='utf-8')
(SERVER / 'http_config.py').write_text(source, encoding='utf-8')
(ROOT / 'baseline.json').write_text(json.dumps({str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [SOURCE/'http_config.py',SOURCE/'shop_season_names.py',SOURCE/'gamedata/state.json',SOURCE/'gamedata/shop.json',SOURCE/'gamedata/pack_cadence.json']}), encoding='utf-8')
print(json.dumps({'new_packs':len(config['items']), 'random':sum(x['mode']=='random' for x in config['items'].values()),
                  'choice':sum(x['mode']=='choice' for x in config['items'].values()), 'sandbox':str(SERVER)}, ensure_ascii=False))
