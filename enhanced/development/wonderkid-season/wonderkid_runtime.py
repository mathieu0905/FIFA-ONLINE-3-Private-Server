"""Wonderkids season: preserve issued pack pools while exposing new market cards."""
from pathlib import Path
import json

def install(h):
    if getattr(h,'_wonderkid_runtime_installed',False):return
    frozen=json.loads((Path(h.HERE)/'gamedata/wonderkid_legacy_pools.json').read_text('utf-8'))
    old_pool=h.pack_pool
    def pool(i):
        if str(i) in frozen['pools']:return [tuple(r) for r in frozen['pools'][str(i)]]
        return old_pool(i)
    h.pack_pool=pool
    for name in ('pack_price','pack_expected_value'):
        f=getattr(h,name,None)
        if hasattr(f,'cache_clear'):f.cache_clear()
    h._wonderkid_runtime_installed=True
