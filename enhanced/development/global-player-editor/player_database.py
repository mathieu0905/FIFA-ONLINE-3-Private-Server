"""Global player database editor. Drafts and builds never write installed databases."""
from pathlib import Path
from contextlib import closing
import argparse
import hashlib
import http.server
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
import urllib.parse
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MEMBER = 'data/db2/fifadb.db.db2'
STATS = 'strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
LABELS = '强壮 体力 加速度 速度 弹跳 灵活 平衡 铲断 盘带 控球 盯人 抢断 传中 短传 射术 长传 射门力量 头球 远射 凌空射门 弧线 任意球 点球 拦截 跑位 视野 反应 侵略性 门将开球 门将鱼跃 门将手型 门将站位 门将反应'.split()
FIELDS = {k: dict(label=v, min=1, max=150, group='能力') for k, v in zip(STATS, LABELS)}
FIELDS.update(height=dict(label='身高（cm）', min=100, max=250, group='身体'),
              weight=dict(label='体重（kg）', min=30, max=200, group='身体'),
              overallrating=dict(label='数据库原始 OVR', min=1, max=150, group='资料'),
              preferredfoot=dict(label='惯用脚（1右／2左）', min=1, max=2, group='资料'),
              skillmoves=dict(label='花式星级', min=1, max=5, group='资料'),
              weakfootabilitytypecode=dict(label='逆足星级', min=1, max=5, group='资料'))
POSITIONS = 'GK SW RWB RB RCB CB LCB LB LWB RDM CDM LDM RM RCM CM LCM LM RAM CAM LAM RF CF LF RW RS ST LS LW'.split()
for i in range(1, 5):
    FIELDS['preferredposition' + str(i)] = dict(label='位置' + str(i), min=0 if i == 1 else -1, max=27, group='资料')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Database:
    def __init__(self, server, client, work):
        self.server, self.client, self.work = map(lambda p: Path(p).resolve(), (server, client, work))
        if self.work.is_relative_to(self.server) or self.work.is_relative_to(self.client):
            raise ValueError('Draft/build workspace must be outside installed server and client')
        self.db = self.server / 'gamedata/fifadb.sqlite'
        self.lock = threading.RLock()
        self.building = False
        self.weights = self._weights()
        self.publish_readiness = '尚未检查'
        try:
            module(HERE / 'publish_database.py', 'database_readiness').baseline(self.server, self.client)
            self.publish_readiness = '版本检查通过，应用时将再次校验'
        except Exception as e:
            self.publish_readiness = '当前版本禁止正式应用：' + str(e)

    def _weights(self):
        import ast
        tree = ast.parse((self.server / 'http_config.py').read_text('utf-8'))
        return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'ROLE_WEIGHTS' for t in n.targets))

    def connect(self):
        c = sqlite3.connect(self.db.as_uri() + '?mode=ro', uri=True)
        c.row_factory = sqlite3.Row
        return c

    def ovr(self, row):
        roles = 'GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
        return sum(row[k] * w for k, w in self.weights[roles[row['preferredposition1']]].items()) // 100

    def draft(self):
        path = self.work / 'draft.json'
        return read(path) if path.exists() else dict(revision=0, cards={})

    def search(self, p):
        q = str(p.get('q', '')).strip()[:100]
        season = str(p.get('season', '')).strip()
        offset = max(0, min(100000, int(p.get('offset', 0))))
        where, values = [], []
        if q:
            where.append('(CAST(p.spid AS TEXT)=? OR CAST(p.playerid AS TEXT)=? OR c.full LIKE ? OR e.full LIKE ? OR e.full_eng LIKE ?)')
            values += [q, q, '%' + q + '%', '%' + q + '%', '%' + q + '%']
        if season:
            where.append('CAST(p.spid/1000000 AS INT)=?')
            values.append(int(season))
        sql = ' FROM players p LEFT JOIN nameschi c ON c.playerid=p.playerid LEFT JOIN nameseng e ON e.playerid=p.playerid'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        with closing(self.connect()) as c:
            count = c.execute('SELECT COUNT(*)' + sql, values).fetchone()[0]
            rows = c.execute('SELECT p.*, COALESCE(c.full,e.full_eng,e.full) AS display_name' + sql + ' ORDER BY p.spid LIMIT 50 OFFSET ?', values + [offset]).fetchall()
        return dict(total=count, offset=offset, rows=[dict(spid=r['spid'], playerid=r['playerid'], name=r['display_name'], season=r['spid']//1000000,
                    height=r['height'], weight=r['weight'], ovr=self.ovr(r), position=POSITIONS[r['preferredposition1']]) for r in rows])

    def detail(self, p):
        with closing(self.connect()) as c:
            row = c.execute('SELECT * FROM players WHERE spid=?', (int(p['spid']),)).fetchone()
            if row is None:
                raise ValueError('球员卡不存在')
            row = dict(row)
            name = c.execute('SELECT full FROM nameschi WHERE playerid=?', (row['playerid'],)).fetchone()
            seasons = [r[0] for r in c.execute('SELECT spid FROM players WHERE playerid=? AND spid>=1000000 ORDER BY spid', (row['playerid'],))]
        d = self.draft()
        return dict(row=row, name=name[0] if name else str(row['playerid']), row_hash=digest(row), draft=d['cards'].get(str(row['spid'])),
                    revision=d['revision'], fields=FIELDS, positions=POSITIONS, ovr=self.ovr(row), seasons=seasons)

    def stage(self, p):
        with self.lock:
            d = self.draft()
            if p.get('revision') != d['revision']:
                raise ValueError('草稿已被另一页面修改，请刷新后重试')
            info = self.detail(p)
            if p.get('row_hash') != info['row_hash']:
                raise ValueError('正式数据库已有变化，请重新打开球员')
            changes = p.get('changes')
            if not isinstance(changes, dict) or not changes or set(changes) - FIELDS.keys():
                raise ValueError('请选择允许修改的球员字段')
            for k, v in changes.items():
                f = FIELDS[k]
                if type(v) is not int or not f['min'] <= v <= f['max']:
                    raise ValueError(f"{f['label']} 必须为 {f['min']}..{f['max']} 的整数")
            targets = info['seasons'] if p.get('all_seasons') is True else [info['row']['spid']]
            with closing(self.connect()) as c:
                for spid in targets:
                    row = dict(c.execute('SELECT * FROM players WHERE spid=?', (spid,)).fetchone())
                    old = d['cards'].get(str(spid))
                    if old and old['row_hash'] != digest(row):
                        raise ValueError('已暂存球员的正式数据发生变化，请移除旧草稿后重试')
                    merged = {**(old['changes'] if old else {}), **changes}
                    merged = {k: v for k, v in merged.items() if row[k] != v}
                    if merged:
                        d['cards'][str(spid)] = dict(spid=spid, name=info['name'], row_hash=digest(row), changes=merged,
                                                   before={k: row[k] for k in merged})
                    else:
                        d['cards'].pop(str(spid), None)
            d['revision'] += 1
            write(self.work / 'draft.json', d)
            return dict(affected=len(targets), draft=d)

    def remove(self, p):
        with self.lock:
            d = self.draft()
            if d['revision'] != p.get('revision'):
                raise ValueError('草稿已变化，请刷新')
            d['cards'].pop(str(int(p['spid'])), None)
            d['revision'] += 1
            write(self.work / 'draft.json', d)
            return d

    def status(self, p=None):
        jobs = [read(p) for p in sorted((self.work / 'jobs').glob('*.json'), reverse=True)][:15]
        with closing(self.connect()) as c:
            seasons = [r[0] for r in c.execute('SELECT DISTINCT CAST(spid/1000000 AS INT) FROM players ORDER BY 1')]
            count = c.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        return dict(draft=self.draft(), jobs=jobs, building=self.building, seasons=seasons, count=count,
                    database=str(self.db), client=str(self.client), fields=FIELDS, publish_readiness=self.publish_readiness)

    def queue(self, p):
        with self.lock:
            if self.building:
                raise ValueError('已有数据库构建任务在运行')
            d = self.draft()
            if p.get('revision') != d['revision'] or not d['cards']:
                raise ValueError('草稿为空或已变化，请刷新')
            job = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
            record = dict(id=job, status='building', cards=len(d['cards']), revision=d['revision'])
            write(self.work / 'jobs' / (job + '.json'), record)
            self.building = True
            def run():
                try:
                    out = self.work / 'builds' / job
                    m = self.build(d, out)
                    record.update(status='built', candidate=str(out), manifest_sha256=sha(out / 'manifest.json'), changed_cards=len(m['changes']))
                except Exception as e:
                    record.update(status='failed', error=str(e))
                finally:
                    write(self.work / 'jobs' / (job + '.json'), record)
                    with self.lock:
                        self.building = False
            threading.Thread(target=run, daemon=True).start()
            return record

    def publish(self, p):
        with self.lock:
            if self.building:
                raise ValueError('请等待当前构建或应用任务完成')
            job = str(p.get('id', ''))
            if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}', job):
                raise ValueError('非法构建编号')
            path = self.work / 'jobs' / (job + '.json')
            record = read(path)
            if record.get('status') not in ('built', 'apply_failed') or record.get('manifest_sha256') != p.get('manifest_sha256'):
                raise ValueError('构建状态或校验值不匹配')
            candidate = self.work / 'builds' / job
            if sha(candidate / 'manifest.json') != record['manifest_sha256']:
                raise ValueError('构建清单已变化')
            self.building = True
            record.update(status='applying')
            record.pop('error', None)
            write(path, record)
            def run():
                try:
                    publisher = module(HERE / 'publish_database.py', 'global_database_publisher')
                    record.update(publisher.apply(candidate, record['manifest_sha256'], manage_services=True))
                    with self.lock:
                        d = self.draft()
                        for entry in read(candidate / 'manifest.json')['changes']:
                            if d['cards'].get(str(entry['spid'])) == entry:
                                d['cards'].pop(str(entry['spid']))
                        d['revision'] += 1
                        write(self.work / 'draft.json', d)
                except Exception as e:
                    record.update(status='apply_failed', error=str(e))
                finally:
                    write(path, record)
                    with self.lock:
                        self.building = False
            threading.Thread(target=run, daemon=True).start()
            return record

    def build(self, draft, out):
        out = Path(out).resolve()
        if out.exists() or not out.is_relative_to(self.work):
            raise ValueError('构建目录必须为工作区内的新目录')
        source_big = self.client / 'data/data_0.big'
        hashes = dict(database=sha(self.db), client=sha(source_big))
        sys.path.insert(0, str(self.server / 'tools/re'))
        import bigdir
        import refpack
        codec = module(self.server / 'extract_fifadb.py', 'global_database_codec')
        ordered = module(HERE / 'ordered_big.py', 'global_database_ordered')
        from cryptography.hazmat.primitives.ciphers import Cipher, modes
        try:
            from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
        except ImportError:
            from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
        decoded = bytes(codec.decrypt(bigdir.read(source_big, MEMBER)))
        if hashlib.sha256(b'SQLite format 3\0' + decoded[16:]).hexdigest() != hashes['database']:
            raise ValueError('正式客户端与服务端数据库不一致，拒绝构建')
        out.mkdir(parents=True)
        target = out / 'fifadb.sqlite'
        shutil.copyfile(self.db, target)
        with closing(sqlite3.connect(target.as_uri(), uri=True)) as c:
            c.row_factory = sqlite3.Row
            with c:
                for entry in draft['cards'].values():
                    row = c.execute('SELECT * FROM players WHERE spid=?', (entry['spid'],)).fetchone()
                    if row is None or digest(dict(row)) != entry['row_hash']:
                        raise ValueError('草稿基线失效，请重新打开球员并暂存')
                    changes = entry['changes']
                    if not changes or set(changes) - FIELDS.keys():
                        raise ValueError('非法修改字段')
                    for k, v in changes.items():
                        if type(v) is not int or not FIELDS[k]['min'] <= v <= FIELDS[k]['max']:
                            raise ValueError('非法修改值')
                    c.execute('UPDATE players SET ' + ','.join(k + '=?' for k in changes) + ' WHERE spid=?', list(changes.values()) + [entry['spid']])
            if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('SQLite integrity check failed')
            c.execute('ATTACH DATABASE ? AS original', (self.db.as_uri() + '?mode=ro',))
            # Compare all tables and all columns, allowing only explicit changed cells.
            for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                quoted = '"' + table.replace('"', '""') + '"'
                if table != 'players':
                    if c.execute(f'SELECT * FROM main.{quoted} EXCEPT SELECT * FROM original.{quoted} LIMIT 1').fetchone() or c.execute(f'SELECT * FROM original.{quoted} EXCEPT SELECT * FROM main.{quoted} LIMIT 1').fetchone():
                        raise ValueError('非目标数据表变化：' + table)
                else:
                    changed = [dict(r) for r in c.execute('SELECT * FROM main.players EXCEPT SELECT * FROM original.players')]
                    removed = [dict(r) for r in c.execute('SELECT * FROM original.players EXCEPT SELECT * FROM main.players')]
                    expected = {int(k): e for k, e in draft['cards'].items()}
                    if {r['spid'] for r in changed} != set(expected) or {r['spid'] for r in removed} != set(expected):
                        raise ValueError('非目标球员变化')
                    old = {r['spid']: r for r in removed}
                    for row in changed:
                        if row != {**old[row['spid']], **expected[row['spid']]['changes']}:
                            raise ValueError('非目标字段变化')
        plain = target.read_bytes()
        encryptor = Cipher(Blowfish(codec.KEY), modes.ECB()).encryptor()
        encoded = codec.swap32(encryptor.update(codec.swap32(decoded[:16] + plain[16:])) + encryptor.finalize())
        target_big = out / 'data_0.big'
        shutil.copyfile(source_big, target_big)
        ordered.replace_member(target_big, MEMBER, refpack.refpack(encoded), len(encoded))
        if b'SQLite format 3\0' + bytes(codec.decrypt(bigdir.read(target_big, MEMBER)))[16:] != plain:
            raise ValueError('客户端资源回读不一致')
        gate = module(self.server / 'tools/check_data0_layout.py', 'global_database_layout')
        report = gate.inspect(target_big, source_big, {MEMBER}, 271)
        if report['status'] != 'PASS':
            raise ValueError('BIG 布局检查失败')
        write(out / 'layout-report.json', report)
        if sha(self.db) != hashes['database'] or sha(source_big) != hashes['client']:
            raise ValueError('构建期间正式数据变化，请重新生成')
        manifest = dict(schema=1, status='BUILT_RUNTIME_PENDING', server=str(self.server), client=str(self.client),
                        source_hashes=hashes, output_hashes={f: sha(out / f) for f in ('fifadb.sqlite', 'data_0.big')},
                        changes=list(draft['cards'].values()), non_target_members_identical=270,
                        state_shop_replaced=False, native_status='PENDING')
        write(out / 'manifest.json', manifest)
        return manifest


def serve(database, port):
    class Handler(http.server.BaseHTTPRequestHandler):
        def route(self):
            host = self.headers.get('Host', '').rsplit(':', 1)[0]
            if self.client_address[0] != '127.0.0.1' or host not in ('127.0.0.1', 'localhost'):
                return self.send(403, b'Forbidden', 'text/plain')
            url = urllib.parse.urlparse(self.path)
            if url.path == '/' and self.command == 'GET':
                return self.send(200, (HERE / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            name = url.path.removeprefix('/api/')
            methods = dict(search=database.search, detail=database.detail, status=database.status,
                           stage=database.stage, remove=database.remove, build=database.queue, publish=database.publish)
            if name not in methods or not url.path.startswith('/api/'):
                return self.send(404, b'{}')
            if name not in ('search', 'detail', 'status') and (self.command != 'POST' or self.headers.get('X-FO3-Admin') != '1'):
                return self.send(403, b'{}')
            try:
                p = dict(urllib.parse.parse_qsl(url.query))
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 <= size <= 65536:
                    raise ValueError('Request too large')
                if size:
                    p.update(json.loads(self.rfile.read(size)))
                with database.lock:
                    result = methods[name](p)
                self.send(200, json.dumps(result, ensure_ascii=False).encode())
            except Exception as e:
                self.send(400, json.dumps(dict(error=str(e)), ensure_ascii=False).encode())

        def send(self, code, body, content='application/json; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type', content)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        do_GET = route
        do_POST = route

        def log_message(self, *args):
            pass

    http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='D:/FO3ID/server')
    parser.add_argument('--client', default='D:/FO3ID/32795')
    parser.add_argument('--work', default=str(HERE / 'workspace'))
    parser.add_argument('--port', type=int, default=8090)
    args = parser.parse_args()
    serve(Database(args.server, args.client, args.work), args.port)
