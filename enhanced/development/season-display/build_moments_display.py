"""Fix season84's native badge and unify its affiliation without changing abilities."""
from pathlib import Path
import argparse, hashlib, json, shutil, sqlite3, struct, sys, zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
TEAM = 999984
sys.path.insert(0, str(WORK / 'work/season_expansion'))
import roster_import as codec


def read(p):
    return json.loads(p.read_text('utf-8-sig'))


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


def tag(kind, body):
    return struct.pack('<HI', kind << 6 | 63, len(body)) + body


def tags(data, pos):
    while pos + 2 <= len(data):
        start = pos
        header = struct.unpack_from('<H', data, pos)[0]; pos += 2
        kind, size = header >> 6, header & 63
        if size == 63:
            size = struct.unpack_from('<I', data, pos)[0]; pos += 4
        body = data[pos:pos + size]; pos += size
        yield kind, body, data[start:pos]
        if kind == 0:
            break


def replace_ui_member(source, target, member, replacement, big):
    """Repack this UI container locally; keep all other compressed member bytes exact.

    UI sources may legitimately append a newer GFX at the end of the file. The strict
    ordered data0 helper is not applicable to that layout and is deliberately unchanged.
    """
    original = source.read_bytes(); records = []
    for name, offset, size, usize in big.entries(source):
        records.append((name, replacement if name == member else original[offset:offset + size], 0 if name == member else usize))
    minimum = 17 + sum(17 + len(name.encode('latin1')) for name, _, _ in records)
    header_size = max(len(big.table(source)), (minimum + 127) // 128 * 128)
    output = bytearray(header_size)
    table = bytearray(b'BIg4' + bytes(4) + struct.pack('>II', big.enc(len(records)), big.enc(header_size)) + b'\0')
    for name, payload, usize in records:
        offset = (len(output) + 127) // 128 * 128
        output += bytes(offset - len(output)) + payload
        table += struct.pack('>4I', big.enc(offset), big.enc(len(payload)), big.enc(usize), big.enc(len(name)))
        key = len(payload) & 255
        for character in name.encode('latin1'):
            value = character ^ key
            table.append(((value << 4) | (value >> 4)) & 255)
            key = ((value or len(payload) & 255) - 0x66) & 255
        table.append(0)
    struct.pack_into('<I', table, 4, len(output)); output[:len(table)] = table
    target.write_bytes(output)
    before, after = big.entries(source), big.entries(target)
    assert [r[0] for r in before] == [r[0] for r in after]
    assert all(a[1] + a[2] <= b[1] for a, b in zip(after, after[1:]))
    for a, b in zip(before, after):
        if a[0] != member:
            assert original[a[1]:a[1] + a[2]] == output[b[1]:b[1] + b[2]], a[0]


class Bits:
    def __init__(self):
        self.bits = ''
    def u(self, value, size):
        self.bits += format(value & ((1 << size) - 1), f'0{size}b')
        return self
    def done(self):
        padding = (len(self.bits) + 7) // 8 * 8
        return int(self.bits.ljust(padding, '0'), 2).to_bytes(padding // 8, 'big')


def nbits(values):
    return max(abs(value).bit_length() + 1 for value in values)


# Repository-native vectors, no external texture/font/resource ID. Units are normalized 0..1000.
POLYGONS = [
    (1, [(80, 30), (920, 30), (1000, 130), (1000, 800), (500, 1000), (0, 800), (0, 130)]),
    (2, [(115, 100), (885, 100), (930, 160), (930, 750), (500, 920), (70, 750), (70, 160)]),
    (3, [(180, 250), (380, 250), (380, 330), (325, 330), (325, 660), (380, 660), (380, 740), (180, 740), (180, 660), (235, 660), (235, 330), (180, 330)]),
    (3, [(440, 740), (440, 250), (540, 250), (635, 450), (730, 250), (830, 250), (830, 740), (735, 740), (735, 430), (635, 620), (535, 430), (535, 740)])
]


def shape(character, bounds):
    x, xend, y, yend = bounds
    rect = Bits().u(nbits(bounds), 5)
    for value in bounds:
        rect.u(value, nbits(bounds))
    # DefineShape1: three solid RGB fills, no strokes, then edge records.
    styles = bytes([3, 0, 225, 182, 78, 0, 25, 32, 47, 0, 255, 239, 187, 0])
    records = Bits().u(2, 4).u(0, 4)
    for fill, polygon in POLYGONS:
        points = [(round(x + px * (xend - x) / 1000), round(y + py * (yend - y) / 1000)) for px, py in polygon]
        first = points[0]
        records.u(0, 1).u(3, 5)
        n = nbits(first)
        records.u(n, 5).u(first[0], n).u(first[1], n).u(fill, 2)
        for a, b in zip(points, points[1:] + points[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = max(2, nbits([dx, dy]))
            records.u(1, 1).u(1, 1).u(n - 2, 4)
            if dx and dy:
                records.u(1, 1).u(dx, n).u(dy, n)
            else:
                records.u(0, 1).u(int(bool(dy)), 1).u(dx or dy, n)
    records.u(0, 6)
    return struct.pack('<H', character) + rect.done() + styles + records.done()


def build(out):
    out = out.resolve()
    assert out.is_relative_to(ROOT) and not out.exists()
    out.mkdir(parents=True)
    big, decrypt, replace, refpack, encrypt = codec.load_codecs(SERVER)
    inputs = [SERVER / 'gamedata/fifadb.sqlite', SERVER / 'gamedata/custom_rosters.json', SERVER / 'server_display_zh.json',
              CLIENT / 'data/data_0.big', CLIENT / 'data/ui/components/Label.big']
    inputs.extend(CLIENT / f'data/ui/localization/{lang}.big' for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie'))
    protected = {str(p): codec.sha(p) for p in inputs}
    database = out / 'fifadb.sqlite'
    shutil.copyfile(SERVER / 'gamedata/fifadb.sqlite', database)
    with sqlite3.connect(database.resolve().as_uri(), uri=True) as db:
        db.row_factory = sqlite3.Row
        assert db.execute('select count(*) from players where teamid=?', (TEAM,)).fetchone()[0] == 0
        originals = [dict(r) for r in db.execute('select * from players where spid/1000000=84')]
        assert len(originals) == 123
        # Affiliation is a virtual legend team, consistent with original WL/UL cards.
        # Real nationality, club history, model, stats, grades and owned instances remain intact.
        db.execute('update players set teamid=?,leagueid=2028 where spid/1000000=84', (TEAM,))
        db.commit()
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        db.execute('attach database ? as before', ((SERVER / 'gamedata/fifadb.sqlite').as_uri() + '?mode=ro',))
        for (table,) in db.execute("select name from before.sqlite_master where type='table'").fetchall():
            if table != 'players':
                assert not db.execute(f'select * from before."{table}" except select * from main."{table}"').fetchone(), table
        assert not db.execute('select * from before.players where spid/1000000!=84 except select * from main.players').fetchone()
        for row in originals:
            after = dict(db.execute('select * from players where spid=?', (row['spid'],)).fetchone())
            assert {k: v for k, v in after.items() if k not in ('teamid', 'leagueid')} == {k: v for k, v in row.items() if k not in ('teamid', 'leagueid')}
    write(out / 'affiliation-before.json', [dict(spid=r['spid'], teamid=r['teamid'], leagueid=r['leagueid']) for r in originals])
    archive = out / 'data_0.big'
    shutil.copyfile(CLIENT / 'data/data_0.big', archive)
    raw = bytes(decrypt.decrypt(big.read(archive, codec.MEMBER)))
    payload = encrypt(raw[:16] + database.read_bytes()[16:])
    replace(archive, codec.MEMBER, refpack(payload), len(payload))
    assert b'SQLite format 3\0' + bytes(decrypt.decrypt(big.read(archive, codec.MEMBER)))[16:] == database.read_bytes()
    team_contracts = []
    for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie'):
        member = f'data/db2/{lang}.db.db2'
        old = bytes(decrypt.decrypt(big.read(archive, member)))
        local = out / f'{lang}.sqlite'
        local.write_bytes(b'SQLite format 3\0' + old[16:])
        with sqlite3.connect(local) as db:
            before = {table: db.execute(f'select * from "{table}"').fetchall() for (table,) in db.execute("select name from sqlite_master where type='table'").fetchall()}
            assert not db.execute('select 1 from team where teamid=?', (TEAM,)).fetchone()
            label = '传奇时刻' if lang == 'chi' else 'Legend Moments'
            db.execute('insert into team(teamid,teamname,leagueid) values(?,?,2028)', (TEAM, label))
            db.commit()
            assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
            for table, rows in before.items():
                after = db.execute(f'select * from "{table}"').fetchall()
                assert set(rows) <= set(after)
                if table != 'team':
                    assert rows == after
            found = db.execute('SELECT teamname,teamid FROM team WHERE leagueid BETWEEN ? AND ? AND teamid=?', (2028, 2028, TEAM)).fetchone()
            assert found == (label, TEAM)
        encoded = encrypt(old[:16] + local.read_bytes()[16:])
        replace(archive, member, refpack(encoded), len(encoded))
        assert b'SQLite format 3\0' + bytes(decrypt.decrypt(big.read(archive, member)))[16:] == local.read_bytes()
        team_contracts.append(dict(language=lang, teamid=TEAM, leagueid=2028, teamname=label, native_team_query_pass=True))
    a, b = big.entries(CLIENT / 'data/data_0.big'), big.entries(archive)
    assert [r[0] for r in a] == [r[0] for r in b]
    assert all(x[1] + x[2] <= y[1] for x, y in zip(b, b[1:]))
    oldbytes = (CLIENT / 'data/data_0.big').read_bytes(); newbytes = archive.read_bytes()
    for old, new in zip(a, b):
        if old[0] not in {codec.MEMBER} | {f'data/db2/{lang}.db.db2' for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie')}:
            assert oldbytes[old[1]:old[1] + old[2]] == newbytes[new[1]:new[1] + new[2]], old[0]
    names = []
    for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie'):
        source = CLIENT / f'data/ui/localization/{lang}.big'
        target = out / f'{lang}.big'
        shutil.copyfile(source, target)
        member = next(n for n, *_ in big.entries(source) if '/TEAMNAMES_' in n)
        values = json.loads(big.read(source, member))
        assert str(TEAM) not in values
        values[str(TEAM)] = '传奇时刻' if lang == 'chi' else 'Legend Moments'
        replace(target, member, json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode(), 0)
        after = json.loads(big.read(target, member))
        assert all(after[k] == v for k, v in json.loads(big.read(source, member)).items())
        names.append(dict(language=lang, member=member, old_entries=len(values) - 1, new_entries=len(values)))
    display = read(SERVER / 'server_display_zh.json')
    assert str(TEAM) not in display['names_by_id']['TEAMNAMES_CHI.json']
    display['names_by_id']['TEAMNAMES_CHI.json'][str(TEAM)] = '传奇时刻'
    write(out / 'server_display_zh.json', display)
    registry = read(SERVER / 'gamedata/custom_rosters.json')
    for row in registry['cards']:
        if row['fo3_spid'] // 1000000 == 84:
            row['affiliation_teamid'] = TEAM
            row['affiliation_label'] = '传奇时刻'
    write(out / 'custom_rosters.json', registry)
    source = CLIENT / 'data/ui/components/Label.big'
    target = out / 'Label.big'
    shutil.copyfile(source, target)
    member = next(n for n, *_ in big.entries(source) if n.endswith('.gfx'))
    gfx = big.read(source, member)
    plain = b'FWS' + gfx[3:8] + zlib.decompress(gfx[8:])
    start = 8 + (5 + 4 * (plain[8] >> 3) + 7) // 8 + 4
    parts = []; changed = []
    for kind, body, rawtag in tags(plain, start):
        cid = struct.unpack_from('<H', body)[0] if kind == 2 else None
        if cid in (59, 648):
            body = shape(cid, (-40, 720, -20, 700) if cid == 59 else (-40, 400, -40, 440))
            rawtag = tag(kind, body); changed.append(cid)
        parts.append(rawtag)
    assert changed == [59, 648]
    updated = bytearray(plain[:start] + b''.join(parts)); struct.pack_into('<I', updated, 4, len(updated))
    replace_ui_member(source, target, member, b'CFX' + updated[3:8] + zlib.compress(updated[8:], 9), big)
    before_tags = list(tags(plain, start)); after_tags = list(tags(updated, start))
    assert len(before_tags) == len(after_tags)
    assert all(oldraw == newraw for (kind, body, oldraw), (_, _, newraw) in zip(before_tags, after_tags)
               if not (kind == 2 and struct.unpack_from('<H', body)[0] in changed))
    assert zlib.decompress(big.read(target, member)[8:]) == updated[8:]
    # A code-native preview/crest source matching the two SWF vector definitions.
    colors = {1: '#e1b64e', 2: '#19202f', 3: '#ffefbb'}
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="-60 -40 1120 1120">' + ''.join('<polygon fill="' + colors[fill] + '" points="' + ' '.join(f'{x},{y}' for x, y in points) + '"/>' for fill, points in POLYGONS) + '</svg>'
    (out / 'legend-moments-badge.svg').write_text(svg, 'utf-8')
    # Compile the same code-native polygons to the CDN crest sizes used by the game.
    from PIL import Image, ImageDraw
    crest_dir = out / 'crests'; crest_dir.mkdir()
    for folder, prefix, size in [('small', 's', 32), ('large', 'l', 128)]:
        image = Image.new('RGBA', (size * 4, size * 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for fill, points in POLYGONS:
            draw.polygon([(round((x + 60) / 1120 * size * 4), round((y + 40) / 1120 * size * 4)) for x, y in points], fill=colors[fill])
        image = image.resize((size, size), Image.Resampling.LANCZOS)
        directory = crest_dir / folder; directory.mkdir()
        image.save(directory / f'{prefix}{TEAM}.png')
    for path, digest in protected.items():
        assert codec.sha(Path(path)) == digest, 'Live source changed during candidate build'
    report = dict(status='MOMENTS_DISPLAY_CANDIDATE_NOT_INSTALLED', scope_cards=123, affiliation_teamid=TEAM, affiliation_label='传奇时刻',
                  badge_text='IM', badge_shapes=changed, old_season15_shapes_and_all_ABC_unchanged=True,
                  unchanged_player_fields_except_team_league=True, all_non_moment_rows_unchanged=True,
                  old_localization_keys_preserved=True, language_teamnames=names, native_team_contracts=team_contracts,
                  data0_264_non_target_payloads_identical=True,
                  source_hashes=protected, native_verified=False, production_written=False,
                  files={str(p.relative_to(out)): codec.sha(p) for p in out.rglob('*') if p.is_file()})
    write(out / 'manifest.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'scope_cards', 'affiliation_teamid', 'badge_shapes')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    build(parser.parse_args().out)
