from pathlib import Path
import argparse, json, sqlite3, struct, sys, zlib
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), 'D:/FO3ID/server/tools/re']
import bigdir
from build_moments_display import tags, POLYGONS
import build_moments_display as build


class Reader:
    def __init__(self, data):
        self.data = data; self.pos = 0
    def u(self, n):
        value = 0
        for _ in range(n):
            value = (value << 1) | ((self.data[self.pos // 8] >> (7 - self.pos % 8)) & 1); self.pos += 1
        return value
    def s(self, n):
        value = self.u(n)
        return value - (1 << n) if value & (1 << (n - 1)) else value
    def align(self):
        self.pos = (self.pos + 7) // 8 * 8


parser = argparse.ArgumentParser(); parser.add_argument('--candidate', required=True, type=Path); args = parser.parse_args()
candidate = args.candidate.resolve(); report = json.loads((candidate / 'manifest.json').read_text('utf-8'))
import hashlib
for relative, wanted in report['files'].items():
    assert hashlib.sha256((candidate / relative).read_bytes()).hexdigest() == wanted
with sqlite3.connect((candidate / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    rows = db.execute('select teamid,leagueid,count(*) from players where spid/1000000=84 group by 1,2').fetchall()
    assert rows == [(999984, 2028, 123)]
    assert db.execute('select count(*) from players where teamid=999984 and spid/1000000!=84').fetchone()[0] == 0
    total = db.execute('select count(*) from players').fetchone()[0]; assert total == 60678
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
label = candidate / 'Label.big'; member = next(n for n, *_ in bigdir.entries(label) if n.endswith('.gfx'))
gfx = bigdir.read(label, member); plain = b'FWS' + gfx[3:8] + zlib.decompress(gfx[8:])
start = 8 + (5 + 4 * (plain[8] >> 3) + 7) // 8 + 4
parsed = []
for kind, body, _ in tags(plain, start):
    if kind != 2 or struct.unpack_from('<H', body)[0] not in (59, 648):
        continue
    character = struct.unpack_from('<H', body)[0]
    bits = Reader(body[2:]); n = bits.u(5); bounds = [bits.s(n) for _ in range(4)]; bits.align()
    assert bits.u(8) == 3
    colors = []
    for _ in range(3):
        assert bits.u(8) == 0
        colors.append(tuple(bits.u(8) for _ in range(3)))
    assert bits.u(8) == 0
    fillbits, linebits = bits.u(4), bits.u(4)
    assert fillbits == 2 and linebits == 0
    paths = []; current = None; x = y = 0; fill = 0
    while True:
        edge = bits.u(1)
        if not edge:
            flags = bits.u(5)
            if not flags:
                break
            assert flags == 3
            n = bits.u(5); x, y = bits.s(n), bits.s(n); fill = bits.u(fillbits)
            current = dict(fill=fill, points=[(x, y)]); paths.append(current)
        else:
            assert bits.u(1) == 1
            n = bits.u(4) + 2
            if bits.u(1):
                x += bits.s(n); y += bits.s(n)
            elif bits.u(1):
                y += bits.s(n)
            else:
                x += bits.s(n)
            current['points'].append((x, y))
    assert len(paths) == 4 and all(p['points'][0] == p['points'][-1] for p in paths)
    assert [p['fill'] for p in paths] == [1, 2, 3, 3]
    assert colors == [(225, 182, 78), (25, 32, 47), (255, 239, 187)]
    assert bits.pos <= len(body[2:]) * 8 and len(body[2:]) * 8 - bits.pos < 8
    parsed.append(dict(character=character, bounds=bounds, closed_paths=4, bytecode_tags_changed=False))
assert len(parsed) == 2
for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie'):
    path = candidate / f'{lang}.big'
    member = next(n for n, *_ in bigdir.entries(path) if '/TEAMNAMES_' in n)
    values = json.loads(bigdir.read(path, member))
    assert values['999984'] == ('传奇时刻' if lang == 'chi' else 'Legend Moments')
    big, decrypt, *_ = build.codec.load_codecs(Path('D:/FO3ID/server'))
    raw = bytes(decrypt.decrypt(big.read(candidate / 'data_0.big', f'data/db2/{lang}.db.db2')))
    with sqlite3.connect(':memory:') as db:
        db.deserialize(b'SQLite format 3\0' + raw[16:])
        row = db.execute('SELECT teamname,teamid FROM team WHERE leagueid BETWEEN 2028 AND 2028 AND teamid=999984').fetchone()
        assert row == (values['999984'], 999984)
result = dict(status='PASS_MOMENTS_DISPLAY_STRUCTURE_NOT_NATIVE', cards=123, affiliation_groups=1, vector_badges=parsed,
              six_language_names=True, six_native_team_table_queries_pass=True, total_players=total, native_verified=False, production_written=False)
(ROOT / 'candidate-check-PASS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(dict(status=result['status'], cards=123, vector_badges=len(parsed), affiliation='Legend Moments')))
