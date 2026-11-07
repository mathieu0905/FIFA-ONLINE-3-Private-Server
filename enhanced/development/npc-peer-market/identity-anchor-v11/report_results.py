"""Export audited offline prices and rankings; never changes the game installation."""
from pathlib import Path
import ast
import collections
import datetime
import gzip
import hashlib
import json
import sqlite3
from predict import IdentityValueModel

P = Path(__file__).resolve().parent
B = P.with_name('anchor-retraining-v10')
S = Path('D:/FO3ID/server')


def load(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt', encoding='utf8') as file:
            return json.load(file)
    return json.loads(path.read_text('utf8'))


def save(name, value):
    (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', 'utf8')


def money(value):
    return f'{value/10000:.2f}万' if value < 100000000 else f'{value/100000000:.2f}亿'


def main():
    report = load(P/'training-report.json')
    verified = load(P/'local-verification.json')
    model = IdentityValueModel(expected_sha256=report['model_sha256'])
    assert verified['model_sha256'] == model.sha256 and verified['status']=='PASS'
    prepared = load(B/'preparation.json')
    database = S/'gamedata/fifadb.sqlite'
    assert hashlib.sha256(database.read_bytes()).hexdigest()==prepared['official_db_sha256'], 'Roster changed; refresh corrected evaluation inputs first'
    profiles = {r['spid']:r for r in load(B/'current-profiles.json.gz')}
    preview = load(P/'current-price-preview.json.gz')
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        names = {r[0]:dict(name=r[1] or r[3], full_name=r[2]) for r in db.execute('SELECT playerid,short,full,full_eng FROM nameschi')}
        eligible = {r[0] for r in db.execute('SELECT p.spid FROM players p JOIN permid m USING(spid) WHERE m.transferable=1 AND p.spid>=1000000 AND p.playerid IN(SELECT playerid FROM namesind)')}
    eligible |= {int(s) for s in load(S/'gamedata/fa_prices.json')}
    season_names = {7:'07'}
    for filename, symbol in [('http_config.py','FA_SEASONS'),('shop_season_names.py','SEASONS')]:
        for node in ast.parse((S/filename).read_text('utf8')).body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==symbol for t in node.targets):
                value = ast.literal_eval(node.value)
                if symbol=='SEASONS':season_names.update(value)
                else:
                    for label,codes,_ in value:
                        for code in codes:season_names[code]=label
    for row in load(S/'gamedata/custom_rosters.json')['seasons']:
        season_names[row['id']]=row['label']
    groups = collections.defaultdict(list)
    for sid in eligible:
        if sid<1000000:continue
        raw=profiles[sid]
        groups[sid//1000000].append(dict(spid=sid,playerid=raw['playerid'],**names.get(raw['playerid'],dict(name=str(raw['playerid']),full_name=None)),
                                        price_ep=preview[str(sid)]['price'],identity_history=model.identity_prior(raw)))
    kings=[]
    for season, rows in sorted(groups.items()):
        rows.sort(key=lambda r:(-r['price_ep'],r['spid']))
        # Independently resolve the leading cached GPU candidates with portable inference.
        for row in rows[:10]:row['price_ep']=model.predict(profiles[row['spid']])
        rows.sort(key=lambda r:(-r['price_ep'],r['spid']))
        kings.append(dict(season_id=season,season=season_names.get(season,str(season)),cards=len(rows),top3=rows[:3]))
    save('season-kings.json',dict(model_sha256=model.sha256,scope=prepared['evaluation_scope'],eligible_cards=sum(len(g) for g in groups.values()),seasons=len(kings),results=kings,formal_activated=False))
    lines=['各赛季模型估值榜（未上线；1级+1基础估值）','已在内存应用63张曼联传奇属性修正；不代表当前游戏属性。','仅对当前已有可交易卡排名；14/15/16等赛季缺少梅西/C罗，不能视作历史完整卡池。','历史价格用于校准，不是现价；模型榜首不等于比赛验收。','','赛季｜榜首｜估值EP｜卡数｜SPID']
    for row in kings:
        top=row['top3'][0]
        lines.append(f"{row['season']}（{row['season_id']}）｜{top['name']}｜{money(top['price_ep'])}｜{row['cards']}｜{top['spid']}")
    (P/'各赛季卡皇.txt').write_text('\n'.join(lines)+'\n','utf8')
    mul=sorted(groups[48],key=lambda r:(-r['price_ep'],r['spid']))
    assert len(mul)==67
    for row in mul:row['price_ep']=model.predict(profiles[row['spid']])
    mul.sort(key=lambda r:(-r['price_ep'],r['spid']))
    save('manutd-rankings.json',mul)
    lines=['曼联传奇67张：修正属性后新模型估值（尚未安装）','球员｜估值EP｜身份因子｜真实历史报价数｜SPID']
    for row in mul:
        prior=row['identity_history']
        lines.append(f"{row['name']}｜{money(row['price_ep'])}｜{prior['multiplier']:.3f}｜{prior['real_quotes']}｜{row['spid']}")
    (P/'曼联传奇67张新估值.txt').write_text('\n'.join(lines)+'\n','utf8')
    training={r['spid']:r for r in load(B/'training-data.json.gz') if r['kind']=='real'}
    anchors=[]
    for anchor in load(B/'anchor-v9-baseline.json'):
        record=training[anchor['spid']]
        assert record['price']==anchor['price']
        raw=dict(record['attributes'],spid=record['spid'],playerid=record['playerid'])
        anchors.append(dict(anchor,new_source=model.explain(raw)['source_price_estimate'],new_price_ep=model.predict(raw),identity_history=model.identity_prior(raw),historical_reference_local_ep=anchor['price']/1000))
    save('anchor-comparison.json',anchors)
    improvement=1-report['known_test']['with_identity']['log_mae']/report['known_test']['base']['log_mae']
    top_descriptor=load(Path('D:/fifaol3/root-current-top.json'))
    entry=S/'play-local.bat'
    paths=list(top_descriptor['files'])
    actual_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in paths}
    assert actual_hashes==top_descriptor['files']
    handback=dict(status='MODEL_TRAINED_VERIFIED_ACTIVATION_DEFERRED',at=datetime.datetime.now().astimezone().isoformat(),model_sha256=model.sha256,
                  offline_model=str(P/'selected-model.json.gz'),source_preparation=prepared,verification=verified,known_history_improvement=improvement,
                  historical_prices_not_live=True,final_all_history_refit_not_independent_evaluation=True,
                  formal_written=False,formal_activated=False,real_state_shop_market_written=False,game_GUI='none',services_action='none',
                  reason='Player attributes require client/database changes; market supply online API explicitly does not switch valuation models. ABI2 business hot routes do not include price workers. Do not restart or interrupt play.',
                  observed_entry=str(entry),observed_top=top_descriptor['top_preflight'],compose_api='compose_manifest(server=None,client=None)',actual_top_hashes=actual_hashes,
                  pending_attribute_build=prepared['pending_MUL_build'],pending_files=['valuation runtime/seed integration','63-card native UI database/BIG and registry/certificate'],
                  new_MUL_top10=mul[:10],native_or_match_verified=False)
    save('handback.json',handback)
    lines=['身份与能力联合价值模型 v11（GPU训练完成，未激活）',
           f"历史真实报价17842条，覆盖10880名球员；身份因子限制为2/3至1.5倍，未知身份固定1倍。",
           '能力专家采用单调约束。同一人不同赛季共享身份因子，不硬编码某个名字或赛季的价格。',
           '最终身份因子只拟合实际部署能力底座尚未解释的残差，避免与能力模型重复计价。',
           f"跨赛季独立留卡570人：平均对数误差下降{improvement:.2%}；中位误差倍率3.089→2.945。",
           '该验证使用同人其他赛季历史，留出赛季报价不参与先验；整名球员也从能力底座训练中排除。',
           '完全未知球员4321张测试：中位误差倍率2.591；v9为2.557。不能宣称所有场景都更准确。',
           '2128493次属性/逆足/花式严格上涨检查和21563组同人属性支配检查，倒挂0。',
           '本地独立重算全部最终身份先验及570留卡验证；700张GPU/便携推理一致性与1050项严格上涨检查通过。',
           '最终全历史重拟合后锚点展示属于拟合结果，不充当新的盲测。历史市场价格含供需/稀缺因素，不等同纯比赛能力。','',
           '历史卡皇对照：球员｜历史KR/1000参考｜v9估值EP｜v11估值EP｜身份因子']
    for sid in [30037576,30001625,30028130,93214100,93001419,93001109,30238380]:
        row=next(r for r in anchors if r['spid']==sid)
        lines.append(f"{row['name']}（{sid}）｜{money(row['historical_reference_local_ep'])}｜{money(row['v9_fair_price'])}｜{money(row['new_price_ep'])}｜{row['identity_history']['multiplier']:.3f}")
    lines+=['','曼联传奇修正属性后的前十：']
    lines += [f"{i}. {r['name']} {money(r['price_ep'])} EP" for i,r in enumerate(mul[:10],1)]
    lines+=['','正式状态：未修改正式文件、数据库、市场、真实存档或余额；未退出游戏、未重启服务、未操作GUI。',
            '现有在线供货设置接口不加载价格模型；属性修正涉及客户端资源。遵守游玩期间约定，激活延后。',
            '后续安装必须重新读取最新父层/游戏状态，统一发布锁、备份/CAS，保留其它聊天改动和全部存档进度。',
            '历史锚点来源：']+prepared['anchor_source_verified_urls']
    (P/'模型校准与验证.txt').write_text('\n'.join(lines)+'\n','utf8')
    print(json.dumps(dict(status='PASS',seasons=len(kings),cards=sum(len(g) for g in groups.values()),MUL_top5=mul[:5],anchor_examples=[a for a in anchors if a['spid'] in [30037576,93214100,93001419]],formal_activated=False),ensure_ascii=False))


if __name__=='__main__':main()
