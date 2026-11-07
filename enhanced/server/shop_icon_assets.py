"""Validated native image mapping; does not change product pools, prices or state."""
import functools,hashlib,json,re
from pathlib import Path

def install(hc, manifest=None):
    if getattr(hc,'_shop_icon_assets_installed',False):return
    if manifest is None:
        manifest=json.loads((Path(hc.HERE)/'gamedata/shop_icon_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema')!=1:raise ValueError('Unsupported shop icon manifest')
    mapping={}
    for key,row in manifest['items'].items():
        itemid=int(key);icon=row['icon']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',icon):raise ValueError('Invalid native shop icon name')
        if row['filename']!=icon+'.png':raise ValueError('Native icon filename mismatch')
        target=Path(hc.ASSETS)/'externalAssets/shop'/row['filename']
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Missing or unverified shop image: '+str(target))
        mapping[itemid]=icon
    original=hc.item_def
    @functools.wraps(original)
    def item_def(itemid):
        out=original(itemid)
        if itemid in mapping:out={**out,'itemicon':mapping[itemid],'bundleicon':mapping[itemid]}
        return out
    hc.item_def=item_def
    hc.shop_icon_assets=dict(mapping)
    hc._shop_icon_assets_installed=True
