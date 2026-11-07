from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).resolve().parent
reports={name:json.loads((R/file).read_text(encoding='utf8')) for name,file in {
    'opening_sequence':'nonce-sequence-results.json',
    'frozen_rights':'moments-rights-results.json',
    'controlled_moments':'controlled-moments-results.json',
    'chain_integration':'test-results.json',
}.items()}
assert all(v['status']=='PASS' for v in reports.values())
addon=json.loads((R/'product_chain_elite.json').read_text(encoding='utf8'))
shock=addon['risk_packs']['97310011']
assert {s//1000000 for tier in shock['tiers'] for s in tier['pool']}<={27,30,31,33,48,93}
assert shock['grades']==[0]*5+[30,28,25,10,6,1]
track=addon['chains']['71231901']
assert len(track['round_steps'])==10
for steps in track['round_steps']:
    counts={}
    for step in steps:
        contents=track['packages'][str(step)]['contents']
        assert len({i for i,n in contents})==len(contents)
        for i,n in contents:counts[i]=counts.get(i,0)+n
    assert counts=={97819000:50,97819011:1,97819084:1}
for key in ('71230101','71230201'):
    for definition in addon['chains'][key]['packages'].values():
        assert len({i for i,n in definition['contents']})==len(definition['contents'])
        assert not any(i in (97300011,97300012,97819084,97310084) for i,n in definition['contents'])
status=dict(status='TESTED_NOT_INSTALLED_RESTART_HOLD',observed_at=datetime.datetime.now().astimezone().isoformat(),formal_writes=False,
    reason='Human requires a new restart notification; no automatic installation while root coordination is paused.',
    tests={key:dict(status=value['status'],count=value['count']) for key,value in reports.items()},
    pure_legend_pool_size=sum(len(tier['pool']) for tier in shock['tiers']),grade_weights=shock['grades'],
    chains={key:dict(name=value['name'],rounds=10,first_round_packs=sum(n for step in value['steps'] for _,n in value['packages'][str(step)]['contents'])) for key,value in addon['chains'].items()},
    source_sha256=hashlib.sha256((R/'product_packs.py').read_bytes()).hexdigest(),addon_sha256=hashlib.sha256((R/'product_chain_elite.json').read_bytes()).hexdigest())
(R/'candidate-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(status,ensure_ascii=True))
