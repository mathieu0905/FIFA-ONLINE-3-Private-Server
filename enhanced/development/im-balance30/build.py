"""Build an incremental IM stat calibration from current official inputs only."""
from pathlib import Path
import ast, collections, datetime, hashlib, importlib.util, json, math, shutil, sqlite3, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(S/'tools/re'),str(S/'player_editor'),str(S)]
import bigdir, extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
FIELDS='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
MEMBER='data/db2/fifadb.db.db2'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def weights():
    scope={};tree=ast.parse((S/'http_config.py').read_text('utf8'))
    for name in ('ROLE_WEIGHTS','POS_ROLE'):
        n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
        exec(compile(ast.Module(body=[n],type_ignores=[]),'official-role-weights','exec'),scope)
    return [scope['ROLE_WEIGHTS'][role] for role in scope['POS_ROLE']]
def num(p,w):return sum(p[k]*v for k,v in w.items())
def calibrate(current,others,w):
    candidates=[p for p in others if p['playerid']==current['playerid'] and p['spid']>=1000000 and p['spid']//1000000!=84]
    if not candidates:raise RuntimeError('No same-person non-IM baseline '+str(current['spid']))
    best=max(candidates,key=lambda p:(num(p,w),p['spid']))
    shift=max(0,math.ceil((num(best,w)+3000-num(current,w))/100))
    after={**current,**{k:current[k]+shift for k in FIELDS}}
    if any(not 1<=after[k]<=150 for k in FIELDS):raise RuntimeError('Stat outside established UI range 1..150; review '+str(current['spid']))
    assert num(after,w)-num(best,w)>=3000
    assert all(after[k]==v for k,v in current.items() if k not in FIELDS)
    return after,best,shift
def build():
    R.mkdir(exist_ok=True);out=R/('build-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
    paths=[S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',C/'data/data_0.big',S/'http_config.py']
    baseline={str(p):sha(p) for p in paths}
    registry=json.loads(paths[1].read_text('utf8'));old_registry=json.loads(paths[1].read_text('utf8'))
    lookup={r['fo3_spid']:r for r in registry['cards']};ws=weights()
    db=sqlite3.connect(paths[0].as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    rows=[dict(p) for p in db.execute('SELECT * FROM players WHERE spid>=1000000')]
    people=collections.defaultdict(list)
    for p in rows:people[p['playerid']].append(p)
    names={pid:name for pid,name in db.execute('SELECT playerid,short FROM nameschi')}
    im=[p for p in rows if p['spid']//1000000==84]
    assert {p['spid'] for p in im}=={sid for sid in lookup if sid//1000000==84}
    result=[];dbpath=out/'fifadb.sqlite'
    with sqlite3.connect(dbpath) as target:db.backup(target)
    db.close()
    with sqlite3.connect(dbpath,uri=True) as target:
        for p in im:
            w=ws[p['preferredposition1']];after,best,shift=calibrate(p,people[p['playerid']],w)
            target.execute('UPDATE players SET '+','.join(k+'=?' for k in FIELDS)+' WHERE spid=?',[after[k] for k in FIELDS]+[p['spid']])
            row=dict(spid=p['spid'],playerid=p['playerid'],name=names.get(p['playerid']),
                source_spid=best['spid'],source_row_sha256=digest(best),shift=shift,
                primary_before=num(p,w)//100,primary_after=num(after,w)//100,source_at_im_position=num(best,w)//100,
                exact_margin=(num(after,w)-num(best,w))/100,
                im10_vs_other20_without_sets=(num(after,w)-num(best,w))/100-20,
                full_im10_vs_full_other20_with_sets=(num(after,w)-num(best,w))/100-20+7-17+5,
                before_row=p,after_row=after)
            result.append(row)
            lookup[p['spid']]['im_balance']=dict(revision='im-best-other-plus30-v1',anchor_spid=best['spid'],anchor_row_sha256=digest(best),
                before_row_sha256=digest(p),after_row_sha256=digest(after),uniform_33stat_shift=shift,
                policy='At IM primary position, at least best same-person non-IM base +30; preserve existing IM stat differences, identity/body/model/traits/foot/skills/position; never lower')
        target.commit();target.execute('ATTACH DATABASE ? AS baseline',(paths[0].as_uri()+'?mode=ro',))
        for table, in target.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            q='"'+table.replace('"','""')+'"';where=' WHERE spid/1000000 != 84' if table=='players' else ''
            assert target.execute('SELECT count(*) FROM main.'+q).fetchone()==target.execute('SELECT count(*) FROM baseline.'+q).fetchone()
            assert not target.execute('SELECT * FROM main.'+q+where+' EXCEPT SELECT * FROM baseline.'+q+where+' LIMIT 1').fetchone(),table
            assert not target.execute('SELECT * FROM baseline.'+q+where+' EXCEPT SELECT * FROM main.'+q+where+' LIMIT 1').fetchone(),table
        target.row_factory=sqlite3.Row
        for row in result:assert dict(target.execute('SELECT * FROM players WHERE spid=?',(row['spid'],)).fetchone())==row['after_row']
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for old,new in zip(old_registry['cards'],registry['cards']):
        assert {k:v for k,v in new.items() if k!='im_balance'}=={k:v for k,v in old.items() if k!='im_balance'}
    save(out/'custom_rosters.json',registry);save(out/'changes.json',result)
    decoded=bytes(extract_fifadb.decrypt(bigdir.read(paths[2],MEMBER)))
    assert b'SQLite format 3\0'+decoded[16:]==paths[0].read_bytes()
    plain=dbpath.read_bytes();enc=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor()
    encrypted=extract_fifadb.swap32(enc.update(extract_fifadb.swap32(decoded[:16]+plain[16:]))+enc.finalize())
    big=out/'data_0.big';shutil.copyfile(paths[2],big)
    packed=refpack(encrypted);assert len(packed)<len(encrypted)
    replace_member(big,MEMBER,packed,len(encrypted))
    assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(big,MEMBER)))[16:]==plain
    layout=load(S/'tools/check_data0_layout.py','im_layout').inspect(big,baseline=paths[2],changed_members={MEMBER},expected_count=len(bigdir.entries(paths[2])))
    assert layout['status']=='PASS';save(out/'layout.json',layout)
    cert=load(S/'tools/player_import/check.py','im_import').validate(S,C,database=dbpath,data0=big,registry=out/'custom_rosters.json',full=True)
    assert cert['status']=='PLAYER_IMPORT_FULL_PASS';save(out/'player-import-validation.json',cert)
    assert baseline=={str(p):sha(p) for p in paths},'Official inputs changed; rebuild'
    report=dict(status='BUILD_FULL_CHECK_PASS_NOT_INSTALLED',output=str(out),cards=len(result),changed=sum(r['shift']>0 for r in result),
        base_min=min(r['primary_after'] for r in result),base_max=max(r['primary_after'] for r in result),
        margin_min=min(r['exact_margin'] for r in result),im10_vs_other20_min=min(r['im10_vs_other20_without_sets'] for r in result),
        full_im10_vs_other20_with_sets_min=min(r['full_im10_vs_full_other20_with_sets'] for r in result),
        all_other_rows_tables_and_nonstat_fields_exact=True,layout_status=layout['status'],full_import=cert['status'],
        baseline=baseline,outputs={n:sha(out/n) for n in ('fifadb.sqlite','custom_rosters.json','data_0.big','player-import-validation.json','changes.json')},
        game_gui_used=False,native_verified=False,state_shop_written=False,
        highlights=[{k:v for k,v in row.items() if k not in ('before_row','after_row')} for row in result if row['playerid'] in (250,37576,192181,5467,238380)])
    save(out/'report.json',report);save(R/'latest-build.json',dict(path=str(out),status=report['status']));print(json.dumps(report,ensure_ascii=True),flush=True)
    return out
if __name__=='__main__':build()
