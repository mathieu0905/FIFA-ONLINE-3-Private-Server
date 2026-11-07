"""Final native icon adapter, installed after all catalogue/product adapters.
Only image metadata changes; inventory and gameplay rules remain untouched.
"""
import functools,hashlib,json,re
from pathlib import Path

def install(h,manifest=None,assets=None):
    if getattr(h,'_all_item_icons_installed',False):return
    if manifest is None:
        manifest=json.loads((Path(h.HERE)/'gamedata/all_item_icon_manifest.json').read_text('utf8'))
    if manifest.get('schema')!=1:raise ValueError('Invalid item image manifest')
    assets=Path(assets) if assets is not None else Path(h.ASSETS)/'externalAssets/shop'
    mapping={}
    for raw,row in manifest['items'].items():
        i=int(raw);icon=row['icon']
        if row['itemid']!=i or not re.fullmatch(r'FO3N_\d+_V3',icon) or row['filename']!=icon+'.png':
            raise ValueError('Invalid item image identity')
        p=assets/row['filename']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Missing or altered item image: '+str(i))
        mapping[i]=icon
    required=set(h.PACKS)|set(h.ITEMS)|set(h.PACKAGES)|set(h.MONTHLY)|{h.EP_ITEM,h.ES_ITEM,h.LR_TICKET,1000090}
    if required-set(mapping):raise ValueError('Incomplete item image catalogue: '+str(sorted(required-set(mapping))))
    def decorate(value):
        if isinstance(value,list):return [decorate(v) for v in value]
        if not isinstance(value,dict):return value
        out={k:decorate(v) for k,v in value.items()}
        # Only a definition, never the containing inventory row or purchase payload.
        if 'itemicon' in out or ('category' in out and 'itemid' in out):
            try:icon=mapping.get(int(out.get('itemid',out.get('productid',0))))
            except (ValueError,TypeError):icon=None
            if icon:out.update(itemicon=icon,bundleicon=icon)
        return out
    def wrap(fn):
        @functools.wraps(fn)
        def mapped(*args,**kwargs):return decorate(fn(*args,**kwargs))
        return mapped
    for attr in ('item_def','use_item_def','package_def','coach_items'):
        setattr(h,attr,wrap(getattr(h,attr)))
    for attr in ('EP_ITEM_DEF','ES_ITEM_DEF','LR_TICKET_ITEM'):
        setattr(h,attr,decorate(getattr(h,attr)))
    original_static=h.ep_static_item
    @functools.wraps(original_static)
    def static_item(query,body):
        content_type,raw=original_static(query,body)
        return h._json(decorate(json.loads(raw)))
    for key,value in list(h.ENDPOINTS.items()):
        if value is original_static:h.ENDPOINTS[key]=static_item
    h.ep_static_item=static_item
    h.all_item_icons=dict(mapping)
    h._all_item_icons_installed=True
