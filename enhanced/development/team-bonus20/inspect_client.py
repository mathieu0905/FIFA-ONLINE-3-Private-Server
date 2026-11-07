"""Read current official Module archive without executing or modifying the game."""
from pathlib import Path
import sys, struct, zlib, json, hashlib
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels', r'D:\FO3ID\server\tools\re']
from avm_patch import ABC, dis
import bigdir

def tags(data, p):
    while p + 2 <= len(data):
        at = p
        h = struct.unpack_from('<H', data, p)[0]; p += 2
        t, n = h >> 6, h & 63
        if n == 63: n = struct.unpack_from('<I', data, p)[0]; p += 4
        yield t, data[p:p+n], at, p+n
        p += n
        if t == 0: break

def inspect():
    path = Path(r'D:\FO3ID\32795\data\ui\libs\Module.big')
    member = next(n for n, *_ in bigdir.entries(path) if n.endswith('.gfx'))
    gfx = bigdir.read(path, member)
    swf = b'FWS' + gfx[3:8] + zlib.decompress(gfx[8:])
    start = 8 + (5 + 4 * (swf[8] >> 3) + 7) // 8 + 4
    methods = {}; inventory = []
    for kind, b, at, end in tags(swf, start):
        if kind != 82: continue
        pos = b.index(b'\0', 4) + 1
        a = ABC(b[pos:])
        for cls, sup, ii, it, ci, ct in a.A['cls']:
            if 'TeamColor' not in cls: continue
            mids = {name: mid for k, name, mid in it + ct if k in ('method', 'get', 'set')}
            inventory.append(dict(cls=cls, offset=at, methods=mids))
            for name, mid in mids.items():
                if mid in a.A['body']: methods[f'{cls}.{name} ({mid})'] = '\n'.join(dis(a.A, a.A['body'][mid]))
            (ROOT / f'{cls}.abc').write_bytes(b[pos:])
    (ROOT / 'client-methods.txt').write_text('\n\n'.join(k+'\n'+v for k,v in methods.items()), 'utf8')
    (ROOT / 'client-inventory.json').write_text(json.dumps(dict(module_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), member=member, classes=inventory), indent=2), 'utf8')
    print(json.dumps(inventory))

if __name__ == '__main__': inspect()
