"""Rank currently tradeable native season cards with the trained v9 value model."""
from pathlib import Path
import ast
import collections
import gzip
import hashlib
import html
import json
import sqlite3
from predict import MonotoneValueModel
from features import ability_fields, role_rating

P = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')


def read_gz(name):
    with gzip.open(P / name, 'rt', encoding='utf8') as f:
        return json.load(f)


def money(value):
    if value >= 100_000_000:
        return f'{value / 100_000_000:.2f}亿'
    if value >= 10_000:
        return f'{value / 10_000:.2f}万'
    return f'{value:,}'


def main():
    model = MonotoneValueModel()
    preview = read_gz('current-price-preview.json.gz')
    snapshot = {r['spid']: r for r in read_gz('current-profiles.json.gz')}
    trained = json.loads((P / 'training-report.json').read_text('utf8'))
    assert model.sha256 == trained['model_sha256']
    names = {7: '07'}
    for file, wanted in [('http_config.py', 'FA_SEASONS'), ('shop_season_names.py', 'SEASONS')]:
        for node in ast.parse((S / file).read_text('utf8')).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == wanted for t in node.targets):
                value = ast.literal_eval(node.value)
                if wanted == 'FA_SEASONS':
                    for label, codes, _ in value:
                        for code in codes:
                            names[code] = label
                else:
                    names.update(value)
    custom = json.loads((S / 'gamedata/custom_rosters.json').read_text('utf8'))
    custom_ids = set()
    for season in custom['seasons']:
        names[season['id']] = season['label']
        custom_ids.add(season['id'])
    fa = {int(s) for s in json.loads((S / 'gamedata/fa_prices.json').read_text('utf8'))}
    with sqlite3.connect((S / 'gamedata/fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        own = {s for (s,) in db.execute('SELECT p.spid FROM players p JOIN permid m USING(spid) WHERE m.transferable=1 AND p.spid>=1000000 AND p.playerid IN(SELECT playerid FROM namesind)')}
        rows = [dict(r) for r in db.execute('SELECT p.*,n.short AS name_zh,n.full AS full_name_zh,n.full_eng AS name_eng FROM players p LEFT JOIN nameschi n USING(playerid)')]
    eligible = own | fa
    fields = ability_fields(model.config) + ['weakfootabilitytypecode', 'skillmoves']
    groups = collections.defaultdict(list)
    refreshed = []
    for raw in rows:
        spid = raw['spid']
        if spid < 1_000_000 or spid not in eligible:
            continue
        if spid not in snapshot or any(raw[f] != snapshot[spid][f] for f in fields):
            price = model.predict(raw)
            refreshed.append(spid)
        else:
            price = preview[str(spid)]['price']
        role = model.config['position_roles'][raw['preferredposition1']]
        rating = sum(raw[k] * w for k, w in model.config['role_weights'][role].items()) / 100
        row = dict(spid=spid, playerid=raw['playerid'], name=raw['name_zh'] or raw['name_eng'],
                   full_name=raw['full_name_zh'], season_id=spid // 1_000_000, fair_price_ep=price,
                   primary_role=role, primary_role_rating=rating, best_role_rating=role_rating(raw, model.config),
                   weakfoot=raw['weakfootabilitytypecode'], native_skill_code=raw['skillmoves'], raw=raw)
        groups[spid // 1_000_000].append(row)
    result = []
    for season_id, group in sorted(groups.items()):
        group.sort(key=lambda r: (-r['fair_price_ep'], r['spid']))
        cutoff = group[0]['fair_price_ep'] * .98
        candidates = [r for i, r in enumerate(group) if i < 10 or r['fair_price_ep'] >= cutoff]
        # Independently price the leading contenders using portable inference.
        # The cached native-GPU prediction agreement was verified separately.
        for row in candidates:
            row['fair_price_ep'] = model.predict(row['raw'])
        candidates.sort(key=lambda r: (-r['fair_price_ep'], r['spid']))
        maximum = candidates[0]['fair_price_ep']
        clean = lambda r: {k: v for k, v in r.items() if k != 'raw'}
        winners = [clean(r) for r in candidates if r['fair_price_ep'] == maximum]
        second = next((r for r in candidates if r['fair_price_ep'] < maximum), None)
        result.append(dict(season_id=season_id, season=names.get(season_id, '编号' + str(season_id)),
                           custom=season_id in custom_ids, cards=len(group), winners=winners,
                           top3=[clean(r) for r in candidates[:3]],
                           gap_to_next_distinct=None if second is None else maximum / second['fair_price_ep']))
    output = dict(model='monotone-v9-strict-same-player', model_sha256=model.sha256,
                  scope='Current tradeable market cards only; physical season IDs; level-1 +1 fair base valuation, no grade investment or market drift. Engine season 0 excluded.',
                  eligible_cards=sum(len(g) for g in groups.values()), seasons=len(result),
                  refreshed_changed_profiles=refreshed, formal_prices_written=False,
                  source_price_accuracy_note='Historical price median error factor 2.56 vs old 2.21; hard ordering passed. Rankings are model estimates, not native match results.',
                  results=result)
    (P / 'season-kings.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), 'utf8')
    lines = ['新价值模型各赛季卡皇（统一1级+1基础估值，未上线）',
             f"模型：{output['model']}，覆盖{output['eligible_cards']}张可交易卡、{output['seasons']}个实际赛季编号。",
             '每个实际赛季单独排名；不把MUL等合并筛选池当成同一赛季。引擎模板卡不参与。',
             '卡皇指该模型估值最高，不等于已完成比赛强度验收。', '', '赛季｜卡皇｜新估值EP｜可交易卡数｜SPID']
    for season in result:
        winners = season['winners']
        lines.append(f"{season['season']}（{season['season_id']}）｜{' / '.join(w['name'] for w in winners)}｜{money(winners[0]['fair_price_ep'])}｜{season['cards']}｜{' / '.join(str(w['spid']) for w in winners)}")
    (P / '各赛季卡皇.txt').write_text('\n'.join(lines) + '\n', 'utf8')
    compact = [{k: s[k] for k in ('season_id', 'season', 'cards')} | dict(
        winner=' / '.join(w['name'] for w in s['winners']), price_ep=s['winners'][0]['fair_price_ep'],
        price=money(s['winners'][0]['fair_price_ep']), role=s['winners'][0]['primary_role'],
        primary=s['winners'][0]['primary_role_rating'], best=s['winners'][0]['best_role_rating']) for s in result]
    print(json.dumps(dict(cards=output['eligible_cards'], seasons=output['seasons'], refreshed=len(refreshed), results=compact), ensure_ascii=False))


if __name__ == '__main__':
    main()
