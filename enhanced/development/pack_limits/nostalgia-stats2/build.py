from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,sqlite3,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(S),str(S/'tools/re'),str(S/'player_editor')]
import bigdir,extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=S/'gamedata/fifadb.sqlite';original=C/'data/data_0.big';member='data/db2/fifadb.db.db2'
sources={str(p):sha(p) for p in [source,original,S/'http_config.py',S/'play-local.bat']}
decoded=bytes(extract_fifadb.decrypt(bigdir.read(original,member)))
assert b'SQLite format 3\0'+decoded[16:]==source.read_bytes()
tree=ast.parse((S/'http_config.py').read_text(encoding='utf8'))
weights=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='ROLE_WEIGHTS' for a in n.targets))
roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
stats='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
target=R/'fifadb.sqlite';assert not target.exists();shutil.copyfile(source,target);changes=[]
with sqlite3.connect(target) as db:
    db.row_factory=sqlite3.Row
    rows=list(db.execute('select * from players where spid/1000000=19'));assert len(rows)==88
    for row in rows:
        before=dict(row);w=weights[roles[row['preferredposition1']]];base=sum(row[k]*v for k,v in w.items())//100
        assert base==row['overallrating']
        new={k:min(99,row[k]+2) for k in stats};goal=base+2;corrections=[]
        # Retain the game's base-attribute cap and make the primary OVR exactly +2.
        while sum(new[k]*v for k,v in w.items())//100<goal:
            k=max((k for k in w if new[k]<99),key=lambda k:(w[k],-new[k],k));new[k]+=1;corrections.append(k)
        assert sum(new[k]*v for k,v in w.items())//100==goal
        new.update(overallrating=goal,potential=max(goal,min(99,row['potential']+2)))
        db.execute('update players set '+','.join(k+'=?' for k in new)+' where spid=?',list(new.values())+[row['spid']])
        changes.append(dict(spid=row['spid'],before=before,after={**before,**new},primary_ovr_before=base,primary_ovr_after=goal,cap_corrections=corrections))
    db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    db.execute('attach database ? as old',(str(source),))
    for (table,) in db.execute("select name from sqlite_master where type='table'").fetchall():
        where=' where spid/1000000!=19' if table=='players' else ''
        assert not db.execute('select * from main.'+table+where+' except select * from old.'+table+where+' limit 1').fetchone(),table
        assert not db.execute('select * from old.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
    for change in changes:
        actual=dict(db.execute('select * from players where spid=?',(change['spid'],)).fetchone());assert actual==change['after']
plain=target.read_bytes();enc=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor();encoded=extract_fifadb.swap32(enc.update(extract_fifadb.swap32(decoded[:16]+plain[16:]))+enc.finalize())
assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(encoded))[16:]==plain
print('Packing updated dual-end database',flush=True)
packed=refpack(encoded);out=R/'data_0.big';shutil.copyfile(original,out);replace_member(out,member,packed,len(encoded))
assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(out,member)))[16:]==plain
a=bigdir.entries(original);b=bigdir.entries(out);assert len(a)==len(b)==271
assert all(x[1]+x[2]<=y[1] for x,y in zip(b,b[1:]))
oldbytes=original.read_bytes();newbytes=out.read_bytes()
for x,y in zip(a,b):
    assert x[0]==y[0]
    if x[0]!=member:assert oldbytes[x[1]:x[1]+x[2]]==newbytes[y[1]:y[1]+y[2]]
assert all(sha(Path(p))==digest for p,digest in sources.items()),'Concurrent formal writer changed a source'
(R/'build-results.json').write_text(json.dumps(dict(status='PASS',source_hashes=sources,changes=changes,cards=88,old_primary_ovrs=[88,89],new_primary_ovrs=[90,91],display_level1_plus1=[95,96],non_target_members_exact=270,other_database_rows_exact=True,outputs={n:sha(R/n) for n in ['fifadb.sqlite','data_0.big']}),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',cards=88,primary_base_ovr=[90,91],display_plus1=[95,96],corrected_cards=sum(bool(c['cap_corrections']) for c in changes))))
