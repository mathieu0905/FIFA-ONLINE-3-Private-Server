"""New-sale random editions; issued choice packs/packages remain immutable."""
import copy, hashlib, json
from pathlib import Path

def prepare(h, cfg):
    spec=json.loads(Path(__file__).with_name('draw_first_rules.json').read_text('utf8'))
    unsigned={k:v for k,v in spec.items() if k!='hash'}
    digest=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    if digest!=spec['hash']:raise ValueError('Invalid draw-first rules')
    mapping={int(k):v for k,v in spec['mapping'].items()}
    occupied=set(h.PACKS)|set(h.PACKAGES)|set(h.ITEMS)|set(h.MONTHLY)|set(map(int,cfg['risk_packs']))|set(map(int,cfg.get('strength_packs',{})))|set(map(int,cfg['bundles']))
    if set(mapping.values()) & occupied:raise ValueError('Draw-first ID collision')
    for old,new in mapping.items():
        key=str(new)
        cfg['limits'][key]=copy.deepcopy(cfg['limits'].get(str(old),dict(period='week',count=1)))
        if old not in spec['sale_ids']:cfg.setdefault('chain_only_items',[]).append(new)
    cfg['risk_packs'].update(copy.deepcopy(spec['packs']))
    cfg['bundles'].update(copy.deepcopy(spec['bundles']))
    cfg['retired_sale_items']=sorted(set(cfg.get('retired_sale_items',[]))|set(mapping))
    # Old definitions and their inventory IDs are untouched. Only unbought stages
    # issue the new edition; completed stages and receipts remain in live state.
    retired=set(cfg.get('retired_chains',[]))
    for root,t in cfg['chains'].items():
        if int(root) in retired:continue
        t['name']=t['name'].replace('五档全自选','五档惊喜抽卡')
        for key,d in t['packages'].items():
            d['contents']=[[mapping.get(i,i),n] for i,n in d['contents']]
            d['name']=d['name'].replace('五档全自选','五档惊喜抽卡')
    cfg['draw_first_mapping']={str(k):v for k,v in mapping.items()}
    cfg.setdefault('additional_editions',[]).append('draw-first-v1')

def finish(h,cfg,model):
    if model is None:raise ValueError('Draw-first requires expected-value pricing')
    changed=set(cfg['draw_first_mapping'].values())
    retired=set(cfg.get('retired_chains',[]))
    for root,t in cfg['chains'].items():
        if int(root) in retired:continue
        for key,d in t['packages'].items():
            if not any(i in changed for i,n in d['contents']):continue
            value=model.describe(int(key));value.update(kind='chain',price=value['quotes']['chain'],bp_per_point=1/model.points_per_ep)
            cfg['value_prices'][key]=value
            t['prices'][key]=value['price']
