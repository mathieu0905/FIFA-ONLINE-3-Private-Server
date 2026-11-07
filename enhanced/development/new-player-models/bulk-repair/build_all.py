"""Build bounded deltas against the current official release; never writes it."""
import collections,hashlib,json,pathlib,re,shutil,sqlite3,struct,sys
R=pathlib.Path(__file__).resolve().parent;O=R/'built';O.mkdir(exist_ok=True);T=R/'tooling'
S=pathlib.Path('D:/FO3ID/server');C=pathlib.Path('D:/FO3ID/32795');W=R.parent/'home-black-screen'
sys.path[:0]=[str(T),str(S/'tools/re'),str(S)]
import bigdir,eadb,extract_fifadb as codec,refpack,rx3,native_db,ordered_big
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
def sha(b):return hashlib.sha256(b).hexdigest()
def filehash(p):return ordered_big.digest(p)
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def skeleton(name):
    p=W/'converter-research/data/FIFA Converter/Skeletons'/name
    return {int(r.split(',')[0]):r.split(',')[1] for r in p.read_text('utf-8-sig').splitlines() if r.strip()}
def main():
    sources={str(p):filehash(p) for p in [S/'gamedata/fifadb.sqlite']+[C/f'data/data_{i}.big' for i in [0,4,6]]}
    catalog=json.loads(pathlib.Path('D:/FO3QA/modern_player_integration_v2/model19-v4/model_catalog24.json').read_text('utf8'))['players'];visual={p['playerid']:p for p in catalog if p.get('reserved_head_selector')}
    src=skeleton('Skeleton_FIFA14_Switch.txt');dest=skeleton('Skeleton_ImpactEngine.txt');byname={v:k for k,v in dest.items()};aliases=json.loads((W/'converter-research/impact-bone-name-map.json').read_text('utf8'))
    mapping={i:byname.get(name,aliases['mapping'].get(name)) for i,name in src.items()};mapping={i:v for i,v in mapping.items() if v is not None}
    rig=dict(schema=1,source_rig='FIFA14_Switch',target_rig='ImpactEngine',source_bone_count=len(src),target_bone_count=len(dest),index_mapping=mapping,source_names=src,target_names=dest,alias_provenance=aliases['artifact'],alias_method=aliases['method'])
    write(T/'rig-map.json',rig)
    replacements={4:{},6:{}};model_reports=[];models=[]
    for pid,p in visual.items():
        files=[];proofs=[]
        for folder,filename,idx in [('heads',f'head_{pid}_0.rx3',4),('hair',f'hair_{pid}_0_0.rx3',4),('hairlod',f'hairlod_{pid}_0_0.rx3',6)]:
            member=f'data/sceneassets/{folder}/{filename}';archive=C/f'data/data_{idx}.big';raw=bigdir.read(archive,member);data=rx3.unwrap(raw);sections=rx3.sections(data);counts=[struct.unpack_from('<I',data,off+4)[0] for _,off,_ in sections[rx3.SKIN]]
            if set(counts)=={252}:
                check=rx3.validate(raw);changed=False;converted=raw;proof=dict(unchanged=True,validation=check)
            elif set(counts)=={255}:
                template=bigdir.read(archive,member.replace(str(pid),'231747'));converted,proof=rx3.retarget(raw,template,rig);replacements[idx][member]=(converted,0);changed=True
            else:raise ValueError('Unsupported source rig '+str((pid,counts)))
            files.append(dict(member=member,archive=idx,sha256=sha(converted),kind='mesh',target_bones=252))
            proofs.append(dict(member=member,changed=changed,**proof))
        for folder,filename,idx in [('faces',f'face_{pid}_0_0_0_0_0_0_0_0_textures.rx3',3),('hair',f'hair_{pid}_0_textures.rx3',4)]:
            member=f'data/sceneassets/{folder}/{filename}';raw=bigdir.read(C/f'data/data_{idx}.big',member);rx3.sections(rx3.unwrap(raw));files.append(dict(member=member,archive=idx,sha256=sha(raw),kind='texture'))
        models.append(dict(playerid=pid,spid=p['local_spid'],name=p['name_zh'],reserved_selector=p['reserved_head_selector'],rig='ImpactEngine',native_home_verified=(pid==252371),native_match_verified=False,files=files));model_reports.append(dict(playerid=pid,files=proofs))
    write(O/'mesh-conversions.json',model_reports)
    print('Models validated/converted',len(models),flush=True)
    dbpath=O/'fifadb.sqlite';shutil.copyfile(S/'gamedata/fifadb.sqlite',dbpath);con=sqlite3.connect(dbpath.as_uri(),uri=True);con.row_factory=sqlite3.Row
    sourcepath=pathlib.Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/modern_roster_completion/official24.json');official=json.loads(sourcepath.read_text('utf8'));skills=[];changes={}
    for p in official:
        html=pathlib.Path(p['raw_response_file']).read_bytes();require_hash=p['raw_response_sha256'];assert sha(html)==require_hash
        text=html.decode('utf8');m=re.search(r'<span class="etc skill">(.*?)</span>\s*</span>',text,re.S) or re.search(r'<span class="etc skill">(.*?)</span>',text,re.S);assert m
        stars=m[1].count('★');code=native_db.stars_to_code(stars);spid=p['local_spid'];current=con.execute('SELECT skillmoves FROM players WHERE spid=?',(spid,)).fetchone()[0]
        if current==stars:changes.setdefault(spid,{})['skillmoves']=code;con.execute('UPDATE players SET skillmoves=? WHERE spid=?',(code,spid))
        elif current!=code:raise ValueError('Later player skill edit needs semantic review: '+str(spid))
        skills.append(dict(playerid=p['playerid'],spid=spid,stars=stars,code=code,source_sha256=require_hash))
    registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));registered={p['fo3_spid']:p for p in registry['cards']};done={p['spid'] for p in skills}
    bulk=json.loads(pathlib.Path('D:/fifaol3/bulk-sources/sources.json').read_text('utf8'))
    for p in bulk:
        spid=13000000+p['playerid']
        if p.get('group')!='modern' or spid not in registered or spid in done:continue
        card=registered[spid];raw=pathlib.Path(p['raw_file']).read_bytes();assert sha(raw)==p['raw_sha256']==card['source_sha256']
        m=re.search(r'<span class="etc skill">(.*?)</span>',raw.decode('utf8'),re.S);assert m
        stars=m[1].count('★');code=native_db.stars_to_code(stars);current=con.execute('SELECT skillmoves FROM players WHERE spid=?',(spid,)).fetchone()[0]
        if current==stars:changes.setdefault(spid,{})['skillmoves']=code;con.execute('UPDATE players SET skillmoves=? WHERE spid=?',(code,spid))
        elif current!=code:raise ValueError('Later FC skill edit needs semantic review '+str(spid))
        skills.append(dict(playerid=p['playerid'],spid=spid,stars=stars,code=code,source_sha256=p['raw_sha256']));done.add(spid)
    # This identity's configured native preset only exists in class 1. Preserve
    # the configured preset 1505; do not substitute a different person's face.
    beck=[]
    for row in con.execute('SELECT * FROM players WHERE playerid=250').fetchall():
        assert row['headtypecode']==1505
        if row['headclasscode']==0:
            changes.setdefault(row['spid'],{})['headclasscode']=1;con.execute('UPDATE players SET headclasscode=1 WHERE spid=?',(row['spid'],));beck.append(row['spid'])
        else:assert row['headclasscode']==1
    con.commit();assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';con.execute('ATTACH DATABASE ? AS old',((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',))
    for table, in con.execute("SELECT name FROM main.sqlite_master WHERE type='table'").fetchall():
        name='"'+table.replace('"','""')+'"'
        added=[dict(r) for r in con.execute('SELECT * FROM main.'+name+' EXCEPT SELECT * FROM old.'+name)]
        removed=[dict(r) for r in con.execute('SELECT * FROM old.'+name+' EXCEPT SELECT * FROM main.'+name)]
        if table!='players':assert not added and not removed,table
        else:
            assert {r['spid'] for r in added}==set(changes)=={r['spid'] for r in removed}
            before={r['spid']:r for r in removed}
            for row in added:assert row=={**before[row['spid']],**changes[row['spid']]}
    native_before=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8');base,names,raws,index,table,fields=native_db.player_table(native_before,meta);original=list(table.rows)
    pidkey=fields['playerid']['shortname'];existing={table.get(row,pidkey):i for i,row in enumerate(original)}
    registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));ids=sorted({p['base_playerid'] for p in registry['cards']});missing=[pid for pid in ids if pid not in existing]
    template=table.find(pidkey,231747);native_changes=[]
    for pid in missing:
        source=dict(con.execute('SELECT * FROM main.players WHERE playerid=? ORDER BY overallrating,spid LIMIT 1',(pid,)).fetchone());semantic={**source,'headassetid':pid};notes=[]
        if pid in visual:semantic.update(headassetid=pid,headclasscode=0,headtypecode=1023)
        if semantic['potential']>99:notes.append(dict(field='potential',source=semantic['potential'],native_base=99,reason='Native base schema maximum; live card/source SQLite value retained'));semantic['potential']=99
        row=native_db.encode(table,fields,template,semantic);table.rows.append(row);native_changes.append(dict(playerid=pid,operation='append',source_spid=source['spid'],raw_sha256=sha(row),notes=notes))
    for pid,p in visual.items():
        if pid not in existing:continue
        i=existing[pid];old=table.rows[i];row=old;delta=dict(headassetid=pid,headclasscode=0,headtypecode=1023)
        if pid==252371:delta['skillmoves']=con.execute('SELECT skillmoves FROM main.players WHERE spid=?',(p['local_spid'],)).fetchone()[0]
        for field,value in delta.items():row=table.set(row,fields[field]['shortname'],value-int(fields[field]['rangelow']))
        if row!=old:table.rows[i]=row;native_changes.append(dict(playerid=pid,operation='binding-update',fields=delta,before_sha256=sha(old),after_sha256=sha(row)))
    assert len(table.rows)<65536
    modified={r['playerid'] for r in native_changes if r['operation']=='binding-update'}
    for pid,i in existing.items():
        if pid not in modified:assert table.rows[i]==original[i]
    native_after=native_db.rebuild(native_before,index,table);_,_,outtables=eadb.db_tables(native_after)
    assert all(a==b for i,(a,b) in enumerate(zip(raws,outtables)) if i!=index)
    write(O/'native-changes.json',dict(missing_before=missing,old_count=len(original),new_count=len(table.rows),changes=native_changes,non_target_rows_preserved=True,other_tables_preserved=True))
    raw=bytes(codec.decrypt(bigdir.read(C/'data/data_0.big','data/db2/fifadb.db.db2')));assert sha(b'SQLite format 3\0'+raw[16:])==sources[str(S/'gamedata/fifadb.sqlite')]
    plain=dbpath.read_bytes();e=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor();encrypted=codec.swap32(e.update(codec.swap32(raw[:16]+plain[16:]))+e.finalize())
    p_native=refpack.refpack(native_after);p_sql=refpack.refpack(encrypted);assert refpack.unrefpack(p_native)==native_after and refpack.unrefpack(p_sql)==encrypted
    archives=[];archives.append(ordered_big.rebuild(C/'data/data_0.big',O/'data_0.big',{'data/db/fifa_ng_db.db':(p_native,len(native_after)),'data/db2/fifadb.db.db2':(p_sql,len(encrypted))}))
    for idx in [4,6]:archives.append(ordered_big.rebuild(C/f'data/data_{idx}.big',O/f'data_{idx}.big',replacements[idx]))
    assert b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(O/'data_0.big','data/db2/fifadb.db.db2')))[16:]==plain
    for p,digest in sources.items():assert filehash(p)==digest,'Source advanced during build'
    imported_native=[dict(playerid=pid,raw_sha256=sha(table.find(pidkey,pid))) for pid in missing]
    imports=dict(schema=1,native_base_ids=sorted(existing),native_imports=imported_native,models=models,source_skill_semantics=skills,legacy_skill_codes=[dict(spid=48195864,playerid=195864,value=5,source_template=91195864,reason='Preserve pre-existing FO3 template value; native base record is present and unchanged. Not treated as FC star input.')],known_missing_portraits=[48000249,48000245],legacy_preset_fixes=[dict(playerid=250,headtypecode=1505,headclasscode=1,spids=beck)],native_template_playerid=231747,scope=dict(custom_cards=len(registry['cards']),custom_identities=len(ids)),human_home_verified=[252371],all_models_match_verified=False)
    write(O/'player-imports.json',imports)
    report=dict(status='BUILT_CURRENT_OFFICIAL_DELTAS_NOT_INSTALLED',archives=archives,database=dict(target=str(S/'gamedata/fifadb.sqlite'),payload=str(dbpath),before_sha256=sources[str(S/'gamedata/fifadb.sqlite')],after_sha256=filehash(dbpath)),sqlite_changes=changes,skills=skills,missing_native_ids=missing,models=len(models),retargeted_models=len(models)-1,state_shop_written=False,native_verified_playerids=[252371],other_players_native_verified=False)
    write(O/'build.json',report);print('PASS missing',missing,'retargeted',len(models)-1,'SQLite changed rows',len(changes),flush=True)
if __name__=='__main__':main()
