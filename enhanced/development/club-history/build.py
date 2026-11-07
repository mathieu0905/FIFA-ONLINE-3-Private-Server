"""Incremental playerhistory-only database/resource update from retained official evidence."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, importlib.util, json, re, shutil, sqlite3, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
MEMBER = 'data/db2/fifadb.db.db2'
# Reviewed licensing aliases. Every mapping must be supported by multiple exact
# player-ID + joining-year + loan matches in this installed historical database.
ALIASES = {131681:47, 131682:44, 115841:46, 115845:39}

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def load(p, name):
    sp = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(sp); sys.modules[name] = m; sp.loader.exec_module(m)
    return m

def write(p, d):
    Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def club_map():
    s = (HERE/'search.html').read_text('utf8')
    pairs = re.findall(r"DataCenter.SetAbilitySearch\('(\d+)', 'n4TeamId'\);[^<]*\"><span>([^<]+)</span>", s)
    table = defaultdict(set)
    from html import unescape
    for i, n in pairs: table[unescape(n).strip()].add(int(i))
    return {n:next(iter(v)) for n,v in table.items() if len(v)==1}

def merge(old, incoming):
    """Rows are (teamid, joinedyear, endyear, loan); retain all former club eligibility."""
    incoming = set(incoming)
    authoritative_keys = {(x[0], x[1]) for x in incoming}
    rows = incoming | {tuple(x) for x in old if (x[0],x[1]) not in authoritative_keys}
    result = sorted(rows, key=lambda x:(x[1], x[2] if x[2]!=-1 else 9999, x[0],x[3]))
    if not {x[0] for x in old} <= {x[0] for x in result}:
        raise RuntimeError('Former club eligibility was lost')
    return result

def prepare_history(db):
    supported = json.loads((SERVER/'server_display_zh.json').read_text('utf8'))['names_by_id']['TEAMNAMES_CHI.json']
    mapping = club_map()
    old = defaultdict(list)
    with sqlite3.connect('file:'+Path(db).as_posix()+'?mode=ro',uri=True) as c:
        valid_ids = {r[0] for r in c.execute('select distinct playerid from players')}
        for pid,_,t,j,e,l in c.execute('select * from playerhistory order by playerid,ordernum'):
            old[pid].append((t,j,e,l))
    records = []
    unavailable = 0
    for p in sorted((HERE/'records').glob('*.json')):
        r = json.loads(p.read_text('utf8'))
        if r['status']!='OK': unavailable += 1; continue
        if r['playerid'] not in valid_ids: raise RuntimeError('Foreign player ID')
        if int(r['source_spid'])%1000000 != r['playerid']: raise RuntimeError('Source player identity mismatch')
        import gzip
        raw = gzip.decompress(Path(r['raw_file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=r['raw_sha256']: raise RuntimeError('Official source hash mismatch')
        collector = sys.modules.get('club_history_collector') or load(HERE/'collect.py','club_history_collector')
        if collector.parse(raw.decode('utf-8-sig'))!=r['career']: raise RuntimeError('Parsed source changed')
        records.append(r)
    # Confirm the four reviewed licensing aliases against independent old careers.
    votes = defaultdict(list)
    for r in records:
        for h in r['career']:
            tid = mapping.get(h['club_ko'])
            if tid not in ALIASES: continue
            # A player can move through several clubs within the same year.
            # Such a year cannot identify an alias from years alone.
            if sum(x['joinedyear']==h['joinedyear'] for x in r['career'])!=1:
                continue
            matches = {x[0] for x in old.get(r['playerid'],[]) if x[1]==h['joinedyear'] and x[3]==h['loan']}
            if len(matches)==1:
                votes[tid].append(dict(playerid=r['playerid'],old_teamid=next(iter(matches)),joinedyear=h['joinedyear']))
    for tid,target in ALIASES.items():
        matches = [r for r in votes[tid] if r['old_teamid']==target]
        if len({r['playerid'] for r in matches})<3 or any(r['old_teamid']!=target for r in votes[tid]):
            raise RuntimeError('Licensing alias lacks consistent independent evidence: '+str(tid))
    unknown = Counter(); unsupported = Counter(); edits = {}; evidence = []
    for r in records:
        incoming = []
        for h in r['career']:
            tid = mapping.get(h['club_ko'])
            if tid is None: unknown[h['club_ko']] += 1; continue
            tid = ALIASES.get(tid,tid)
            if str(tid) not in supported:
                unsupported[(h['club_ko'],tid)] += 1; continue
            incoming.append((tid,h['joinedyear'],h['endyear'],h['loan']))
        if not incoming: continue
        pid = r['playerid'];before = old.get(pid,[]);after = merge(before,incoming)
        if before != after:
            edits[pid] = after
            evidence.append(dict(playerid=pid,name_ko=r['name_ko'],source_url=r['url'],
                  fetched_utc=r['fetched_utc'],raw_sha256=r['raw_sha256'],before=before,after=after,
                  added_club_ids=sorted({x[0] for x in after}-{x[0] for x in before})))
    updated = dict(old); updated.update(edits)
    report = dict(source='Nexon FC Online public datacenter',source_metadata_sha256=sha(HERE/'spid.json'),
        team_mapping_sha256=sha(HERE/'search.html'),source_careers=len(records),source_empty_or_unavailable=unavailable,
        players_before=len(old),history_rows_before=sum(map(len,old.values())),
        players_after=len(updated),history_rows_after=sum(map(len,updated.values())),changed_players=len(edits),
        new_player_club_eligibilities=sum(len(x['added_club_ids']) for x in evidence),
        corrected_or_added_history_rows=sum(len(set(x['after'])-set(x['before'])) for x in evidence),
        unmapped_club_names=[dict(name_ko=k,rows=v) for k,v in unknown.most_common()],
        unsupported_client_clubs=[dict(name_ko=k[0],teamid=k[1],rows=v) for k,v in unsupported.most_common()],
        licensing_aliases=[dict(source_teamid=k,installed_teamid=v,evidence=votes[k]) for k,v in ALIASES.items()],
        limitations=['Unavailable source careers and unmapped/unsupported clubs are retained in the report, not guessed.',
                    'Existing club eligibility is preserved. Same-club/same-joining-year dates and loan flags use official data.',
                    'This updates only playerhistory; existing card club, attributes, names and permissions do not change.'])
    return edits,report,evidence

def verify_tables(target, original):
    with sqlite3.connect('file:'+Path(target).as_posix()+'?mode=ro',uri=True) as c:
        if c.execute('pragma integrity_check').fetchone()[0]!='ok': raise RuntimeError('Database integrity')
        c.execute('attach database ? as original',('file:'+Path(original).as_posix()+'?mode=ro',))
        for (name,) in c.execute("select name from sqlite_master where type='table'").fetchall():
            if name=='playerhistory': continue
            q='"'+name.replace('"','""')+'"'
            for a,b in [('main','original'),('original','main')]:
                if c.execute(f'select * from {a}.{q} except select * from {b}.{q} limit 1').fetchone():
                    raise RuntimeError('Non-history table changed: '+name)
        if c.execute('select playerid,teamid from original.playerhistory except select playerid,teamid from main.playerhistory limit 1').fetchone():
            raise RuntimeError('Lost original historical club')
        if c.execute('select 1 from main.playerhistory h where not exists(select 1 from players p where p.playerid=h.playerid) limit 1').fetchone():
            raise RuntimeError('Unknown player in history')
    return dict(sqlite_integrity='PASS',all_non_history_tables_identical=True,old_club_eligibility_preserved=True)

def main():
    out = HERE/'build'
    if out.exists(): raise RuntimeError('Build directory already exists; inspect existing evidence before rebuilding')
    source_db=SERVER/'gamedata/fifadb.sqlite';source_big=CLIENT/'data/data_0.big'
    baseline={str(p):sha(p) for p in [source_db,source_big,SERVER/'server_display_zh.json',SERVER/'extract_fifadb.py',SERVER/'tools/re/refpack.py',SERVER/'tools/re/bigdir.py']}
    edits,report,evidence=prepare_history(source_db)
    if not edits: raise RuntimeError('No history changes')
    out.mkdir();target=out/'fifadb.sqlite';shutil.copyfile(source_db,target)
    with sqlite3.connect(target) as c:
        with c:
            for pid,rows in edits.items():
                c.execute('delete from playerhistory where playerid=?',(pid,))
                c.executemany('insert into playerhistory(playerid,ordernum,teamid,joinedyear,endyear,loan) values (?,?,?,?,?,?)',
                              [(pid,i,*row) for i,row in enumerate(rows)])
    report.update(verify_tables(target,source_db))
    print('History update validated:',report['changed_players'],'players;',report['history_rows_after'],'rows',flush=True)
    write(out/'coverage-report.json',report);write(out/'player-changes.json',evidence);write(out/'baseline.json',baseline)
    sys.path.insert(0,str(SERVER/'tools/re'))
    import bigdir,refpack
    codec=load(SERVER/'extract_fifadb.py','history_codec')
    decoded=bytes(codec.decrypt(bigdir.read(source_big,MEMBER)))
    if hashlib.sha256(b'SQLite format 3\0'+decoded[16:]).hexdigest()!=baseline[str(source_db)]:
        raise RuntimeError('Installed client/server database mismatch')
    plain=target.read_bytes()
    from cryptography.hazmat.primitives.ciphers import Cipher,modes
    from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
    e=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor()
    encrypted=codec.swap32(e.update(codec.swap32(decoded[:16]+plain[16:]))+e.finalize())
    print('Packing encrypted database',flush=True)
    packed=refpack.refpack(encrypted)
    target_big=out/'data_0.big';shutil.copyfile(source_big,target_big)
    ordered=load(HERE.parent/'global-player-editor/ordered_big.py','history_ordered')
    ordered.replace_member(target_big,MEMBER,packed,len(encrypted))
    if b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(target_big,MEMBER)))[16:]!=plain:
        raise RuntimeError('Database encrypted resource roundtrip mismatch')
    layout=load(SERVER/'tools/check_data0_layout.py','history_layout').inspect(target_big,source_big,{MEMBER},271)
    if layout['status']!='PASS': raise RuntimeError('Resource layout failed')
    write(out/'layout-report.json',layout)
    for p,h in baseline.items():
        if sha(p)!=h: raise RuntimeError('Formal build input changed: '+p)
    write(out/'build-result.json',dict(status='BUILT_FOR_DIRECT_INSTALL',database_sha256=sha(target),
         big_sha256=sha(target_big),state_shop_written=False,non_target_members_identical=270,
         source_record_files=len(list((HERE/'records').glob('*.json'))),report=report))
    print('BUILD_PASS',flush=True)

if __name__=='__main__':main()
