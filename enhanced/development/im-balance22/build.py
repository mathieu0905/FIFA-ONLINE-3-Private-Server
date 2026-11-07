"""Role-ranked IM balance using a common ICON reference and rank-matched other seasons."""
from pathlib import Path
import ast, collections, datetime, hashlib, importlib.util, json, shutil, sqlite3, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(S/'tools/re'),str(S/'player_editor'),str(S)]
import bigdir,extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
FIELDS='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
MEMBER='data/db2/fifadb.db.db2';REVISION='im-role-hierarchy-plus22-v2'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def constants():
    n={};tree=ast.parse((S/'http_config.py').read_text('utf8'))
    for name in ('ROLE_WEIGHTS','POS_ROLE'):
        node=next(x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'current-role-weights','exec'),n)
    return n
def num(p,w):return sum(p[k]*v for k,v in w.items())
def design(rows,names):
    n=constants();refs={p['playerid']:p for p in rows if p['spid']//1000000==12};people=collections.defaultdict(list)
    for p in rows:people[p['playerid']].append(p)
    roles=collections.defaultdict(list)
    for p in rows:
        if p['spid']//1000000!=84:continue
        ref=refs[p['playerid']];role=n['POS_ROLE'][p['preferredposition1']];w=n['ROLE_WEIGHTS'][role]
        best=max((o for o in people[p['playerid']] if o['spid']//1000000!=84),key=lambda o:(num(o,w),o['spid']))
        roles[role].append(dict(current=p,ref=ref,own_best=best))
    result=[]
    for role,group in roles.items():
        w=n['ROLE_WEIGHTS'][role]
        # Common-source ordering first. Best-other values supply only the role's
        # power curve and are matched by rank, never by the same player's identity.
        group.sort(key=lambda x:(-x['ref']['overallrating'],-num(x['ref'],w),x['current']['spid']))
        peers=sorted((x['own_best'] for x in group),key=lambda p:(-num(p,w),p['spid']))
        top=max(x['ref']['overallrating'] for x in group)
        for rank,(x,peer) in enumerate(zip(group,peers),1):
            p,ref=x['current'],x['ref'];tier=int(ref['overallrating'])
            tier_bonus=1 if tier>=top-1 else 0 if tier>=top-3 else -1
            advantage=22+tier_bonus
            target=int(num(peer,w)//100)+advantage
            shift=target-int(num(ref,w)//100)
            after={**p,**{k:ref[k]+shift for k in FIELDS}}
            assert int(num(after,w)//100)==target
            assert all(1<=after[k]<=150 for k in FIELDS)
            assert all(after[k]==v for k,v in p.items() if k not in FIELDS)
            result.append(dict(spid=p['spid'],playerid=p['playerid'],name=names.get(p['playerid']),role=role,role_rank=rank,
                reference_spid=ref['spid'],reference_overall=tier,reference_row=ref,reference_row_sha256=digest(ref),
                rank_peer_spid=peer['spid'],rank_peer_primary=int(num(peer,w)//100),rank_peer_row=peer,
                own_best_spid=x['own_best']['spid'],own_best_primary=int(num(x['own_best'],w)//100),
                base_advantage_vs_rank_peer=advantage,source_profile_shift=shift,
                primary_before=int(num(p,w)//100),primary_after=target,
                full_im10_vs_peer18=advantage-19,full_im10_vs_peer20=advantage-25,
                before_row=p,after_row=after))
    return result
def build():
    out=R/('build-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
    paths=[S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',C/'data/data_0.big',S/'http_config.py']
    baseline={str(p):sha(p) for p in paths};registry=json.loads(paths[1].read_text('utf8'));oldregistry=json.loads(paths[1].read_text('utf8'))
    db=sqlite3.connect(paths[0].as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    rows=[dict(p) for p in db.execute('SELECT * FROM players WHERE spid>=1000000')];names=dict(db.execute('SELECT playerid,short_eng FROM nameschi'))
    result=design(rows,names);lookup={c['fo3_spid']:c for c in registry['cards']}
    assert {x['spid'] for x in result}=={sid for sid in lookup if sid//1000000==84}
    database=out/'fifadb.sqlite'
    with sqlite3.connect(database) as target:db.backup(target)
    db.close()
    with sqlite3.connect(database,uri=True) as target:
        for row in result:
            after=row['after_row'];sid=row['spid']
            target.execute('UPDATE players SET '+','.join(k+'=?' for k in FIELDS)+' WHERE spid=?',[after[k] for k in FIELDS]+[sid])
            old_balance=lookup[sid].get('im_balance')
            lookup[sid]['im_balance']=dict(revision=REVISION,prior_balance=old_balance,
                reference_spid=row['reference_spid'],reference_row_sha256=row['reference_row_sha256'],
                reference_overall=row['reference_overall'],role=row['role'],role_rank=row['role_rank'],
                rank_peer_spid=row['rank_peer_spid'],base_advantage_vs_rank_peer=row['base_advantage_vs_rank_peer'],
                before_row_sha256=digest(row['before_row']),after_row_sha256=digest(after),source_profile_shift=row['source_profile_shift'],
                policy='Common ICON profile and hierarchy; rank-matched same-role power curve +21..23; full-set IM10 beats peer18 by2..4 and loses peer20 by2..4; never claim each same-player pair; metadata/identity/models unchanged.')
        target.commit();target.execute('ATTACH DATABASE ? AS baseline',(paths[0].as_uri()+'?mode=ro',))
        for table, in target.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            q='"'+table.replace('"','""')+'"';where=' WHERE spid/1000000!=84' if table=='players' else ''
            assert target.execute('SELECT count(*) FROM main.'+q).fetchone()==target.execute('SELECT count(*) FROM baseline.'+q).fetchone()
            assert not target.execute('SELECT * FROM main.'+q+where+' EXCEPT SELECT * FROM baseline.'+q+where+' LIMIT 1').fetchone(),table
            assert not target.execute('SELECT * FROM baseline.'+q+where+' EXCEPT SELECT * FROM main.'+q+where+' LIMIT 1').fetchone(),table
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for old,new in zip(oldregistry['cards'],registry['cards']):
        assert {k:v for k,v in old.items() if k!='im_balance'}=={k:v for k,v in new.items() if k!='im_balance'}
        if old['fo3_spid']//1000000!=84:assert old==new
        else:assert new['im_balance']['prior_balance']==old.get('im_balance')
    save(out/'custom_rosters.json',registry);save(out/'changes.json',result)
    plain=database.read_bytes();decoded=bytes(extract_fifadb.decrypt(bigdir.read(paths[2],MEMBER)))
    assert b'SQLite format 3\0'+decoded[16:]==paths[0].read_bytes()
    enc=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor();encrypted=extract_fifadb.swap32(enc.update(extract_fifadb.swap32(decoded[:16]+plain[16:]))+enc.finalize())
    big=out/'data_0.big';shutil.copyfile(paths[2],big);packed=refpack(encrypted);assert len(packed)<len(encrypted)
    replace_member(big,MEMBER,packed,len(encrypted))
    assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(big,MEMBER)))[16:]==plain
    layout=load(S/'tools/check_data0_layout.py','hierarchy_layout').inspect(big,baseline=paths[2],changed_members={MEMBER},expected_count=len(bigdir.entries(paths[2])))
    assert layout['status']=='PASS';save(out/'layout.json',layout)
    certificate=load(S/'tools/player_import/check.py','hierarchy_full_check').validate(S,C,database=database,data0=big,registry=out/'custom_rosters.json',full=True)
    assert certificate['status']=='PLAYER_IMPORT_FULL_PASS';save(out/'player-import-validation.json',certificate)
    assert baseline=={str(p):sha(p) for p in paths},'Current official inputs changed; rebuild'
    summary=[{k:v for k,v in x.items() if k not in ('reference_row','rank_peer_row','before_row','after_row')} for x in result]
    save(out/'rankings.json',summary)
    report=dict(status='BUILD_FULL_PASS_NOT_INSTALLED',revision=REVISION,output=str(out),cards=len(result),
        base_range=[min(x['primary_after'] for x in result),max(x['primary_after'] for x in result)],
        comparison_scope='Same position and rank/tier, full grade sets and full IM feature; not same-person pairs. Same level and exclude original club/nation/special set differences.',
        im10_vs_peer18_range=[min(x['full_im10_vs_peer18'] for x in result),max(x['full_im10_vs_peer18'] for x in result)],
        im10_vs_peer20_range=[min(x['full_im10_vs_peer20'] for x in result),max(x['full_im10_vs_peer20'] for x in result)],
        non_target_rows_tables_and_big_members_exact=True,all_nonstat_metadata_exact=True,full_import=certificate['status'],layout=layout['status'],
        baseline=baseline,outputs={n:sha(out/n) for n in ('fifadb.sqlite','data_0.big','custom_rosters.json','player-import-validation.json','changes.json','rankings.json')},
        formal_files_written=False,services_restarted=False,native_verified=False,game_gui_used=False)
    save(out/'report.json',report);save(R/'latest-build.json',dict(path=str(out),status=report['status']));print(json.dumps(report),flush=True)
    return out
if __name__=='__main__':build()
