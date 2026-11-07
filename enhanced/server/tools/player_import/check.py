"""Read-only player import gate: UI DB, native DB, language names and mesh routes.

Run --full before publication. Startup can reuse a certificate only when every
input and checker module has the exact validated SHA-256. No live state is read.
"""
import argparse,hashlib,json,pathlib,sqlite3,struct,sys
HERE=pathlib.Path(__file__).resolve().parent
def filehash(p):
    with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate(server,client,*,database=None,data0=None,data3=None,data4=None,data6=None,imports=None,registry=None,portraits=None,full=False,certificate=None):
    server,client=pathlib.Path(server),pathlib.Path(client)
    sys.path[:0]=[str(HERE),str(server/'tools/re'),str(server)]
    import bigdir,eadb,extract_fifadb as codec,rx3,native_db
    database=pathlib.Path(database or server/'gamedata/fifadb.sqlite');imports=pathlib.Path(imports or server/'gamedata/player-imports.json')
    archives={i:pathlib.Path(v or client/f'data/data_{i}.big') for i,v in [(0,data0),(3,data3),(4,data4),(6,data6)]}
    registry_path=pathlib.Path(registry or server/'gamedata/custom_rosters.json');certificate=pathlib.Path(certificate or server/'gamedata/player-import-validation.json')
    portrait_root=pathlib.Path(portraits) if portraits else None
    source_files={'database':database,'registry':registry_path,'imports':imports,**{'archive'+str(i):p for i,p in archives.items()},**{'checker:'+p.name:p for p in HERE.glob('*.py')},'rig-map':HERE/'rig-map.json'}
    hashes={key:filehash(p) for key,p in source_files.items()}
    if not full and portrait_root is None and certificate.exists():
        saved=json.loads(certificate.read_text('utf8'))
        if saved.get('status')=='PLAYER_IMPORT_FULL_PASS' and saved.get('input_hashes')==hashes:
            if all(pathlib.Path(p).is_file() and filehash(p)==digest for p,digest in saved.get('portrait_hashes',{}).items()):
                return dict(status='PLAYER_IMPORT_CERTIFICATE_PASS',custom_cards=saved['custom_cards'],custom_identities=saved['custom_identities'],models=saved['models'],warnings=saved.get('warnings',[]),native_runtime_proven=False)
    registry=json.loads(registry_path.read_text('utf8'));policy=json.loads(imports.read_text('utf8'))
    if policy.get('schema')!=1:raise ValueError('Invalid player import policy schema')
    errors=[];warnings=[];portrait_hashes={};con=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
    if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':errors.append('UI SQLite integrity check failed')
    unpacked=bytes(codec.decrypt(bigdir.read(archives[0],'data/db2/fifadb.db.db2')))
    if hashlib.sha256(b'SQLite format 3\0'+unpacked[16:]).hexdigest()!=hashes['database']:errors.append('Server and client UI databases differ')
    raw_native=bigdir.read(archives[0],'data/db/fifa_ng_db.db');meta=bigdir.read(archives[0],'data/db/fifa_ng_db-meta.xml').decode('utf8');native_db.verify_crc(raw_native)
    _,_,_,_,table,fields=native_db.player_table(raw_native,meta);key=fields['playerid']['shortname'];ids=[table.get(r,key) for r in table.rows]
    if len(ids)!=len(set(ids)):errors.append('Duplicate native player IDs')
    native={pid:r for pid,r in zip(ids,table.rows)};cards=registry.get('cards',[]);seen={};pids=set();sqlrows={}
    base_ids=set(policy['native_base_ids']);native_receipts={p['playerid']:p for p in policy['native_imports']};model_by_spid={m['spid']:m for m in policy.get('models',[])}
    for card in cards:
        pid,spid=card['base_playerid'],card['fo3_spid'];pids.add(pid)
        if spid in seen and seen[spid]!=pid:errors.append('Conflicting custom SPID '+str(spid))
        seen[spid]=pid;source=con.execute('SELECT * FROM players WHERE spid=?',(spid,)).fetchone()
        if source is None or source['playerid']!=pid:errors.append('Missing/mismatched UI identity '+str((spid,pid)));continue
        sqlrows[spid]=dict(source)
        legacy=next((p for p in policy.get('legacy_skill_codes',[]) if p['spid']==spid and p['playerid']==pid and p['value']==source['skillmoves']),None)
        if not 0<=source['skillmoves']<=4 and legacy is None:errors.append('Undeclared skill code outside 0..4 for SPID '+str(spid))
        if pid not in native:errors.append('Missing native player record '+str(pid))
        elif pid not in base_ids:
            receipt=native_receipts.get(pid)
            if receipt is None or receipt['raw_sha256']!=hashlib.sha256(native[pid]).hexdigest():errors.append('Missing/mismatched native import receipt '+str(pid))
        if source['headclasscode']==1 and source['headtypecode']>=30001 and not any(m['playerid']==pid and m.get('reserved_selector')==source['headtypecode'] for m in policy.get('models',[])):errors.append('Reserved face selector has no complete model receipt '+str(spid))
        candidates=[client/'_cache/cdn/externalAssets/players'/f'p{spid}.png',client/'_cache/games/fo3id/externalAssets/players'/f'p{spid}.png',server/'assets/players'/f'p{spid}.png']
        if portrait_root:candidates.insert(0,portrait_root/f'p{spid}.png')
        existing=[p for p in candidates if p.is_file()]
        if not existing:
            if spid in policy.get('known_missing_portraits',[]):warnings.append('Pre-existing missing portrait; client default image: '+str(spid))
            else:errors.append('Missing custom card portrait '+str(spid))
        for p in existing:portrait_hashes[str(p)]=filehash(p)
    for route in policy.get('generic_models',[]):
        pid,spid=route['playerid'],route['spid'];source=sqlrows.get(spid)
        if route.get('appearance_route')!='fo3_builtin_generic' or not route.get('source_sha256'):
            errors.append('Undocumented generic appearance '+str(pid));continue
        template=native.get(route.get('template_playerid'));current=native.get(pid)
        if source is None or template is None or current is None:
            errors.append('Generic identity/template missing '+str(pid));continue
        for name in ('headclasscode','headtypecode','headassetid','skintonecode'):
            f=fields[name];actual=table.get(current,f['shortname'])+int(f['rangelow'])
            expected=table.get(template,f['shortname'])+int(f['rangelow'])
            if actual!=expected or (name!='headassetid' and source[name]!=expected):errors.append('Generic template route mismatch '+str((pid,name)))
        if source['headclasscode']!=1 or source['headtypecode']>=30001:errors.append('Generic route is not a built-in generic face '+str(pid))
    language_rows={}
    for language in ['eng','chi','ind','kor','tha','vie']:
        raw=bytes(codec.decrypt(bigdir.read(archives[0],f'data/db2/{language}.db.db2')));lc=sqlite3.connect(':memory:');lc.deserialize(b'SQLite format 3\0'+raw[16:]);present={r[0] for r in lc.execute('SELECT playerid FROM names')};language_rows[language]=len(present)
        for pid in sorted(pids-present):errors.append('Missing '+language+' name for player '+str(pid))
        lc.close()
    lua=bigdir.read(archives[0],'data/fifarna/lua/assets/player.lua').decode('latin1')
    import re
    routes={int(k):int(v) for k,v in re.findall(r'\.head\s*==\s*(\d+)\)\s*then\s+modernFaceAsset\s*=\s*(\d+)',lua)}
    directory={i:{n for n,*_ in bigdir.entries(p)} for i,p in archives.items() if i in [3,4,6]}
    models=policy.get('models',[])
    for model in models:
        pid=model['playerid'];row=native.get(pid);spid=model['spid'];source=sqlrows.get(spid)
        if row is not None:
            actual={n:table.get(row,fields[n]['shortname'])+int(fields[n]['rangelow']) for n in ['headassetid','headclasscode','headtypecode']}
            if actual!={'headassetid':pid,'headclasscode':0,'headtypecode':1023}:errors.append('Native dedicated face route mismatch '+str(pid))
        selector=model.get('reserved_selector')
        if source is None or (source['headtypecode'],source['headclasscode'])!=(selector,1):errors.append('UI face selector mismatch '+str(pid))
        if routes.get(selector)!=pid:errors.append('Missing/wrong Lua selector route '+str(pid))
        for f in model['files']:
            idx,name=f['archive'],f['member']
            if name not in directory[idx]:errors.append('Missing model member '+name);continue
            raw=bigdir.read(archives[idx],name)
            if hashlib.sha256(raw).hexdigest()!=f['sha256']:errors.append('Model receipt SHA differs '+name)
            try:
                if f['kind']=='mesh':rx3.validate(raw,252)
                else:rx3.sections(rx3.unwrap(raw))
            except (ValueError,struct.error,AssertionError) as e:errors.append('Invalid RX3 '+name+': '+str(e))
    for fix in policy.get('legacy_preset_fixes',[]):
        member=f"data/sceneassets/heads/head_{fix['headtypecode']}_{fix['headclasscode']}.rx3"
        if member not in directory[4]:errors.append('Missing configured legacy head preset '+member)
        for spid in fix['spids']:
            row=con.execute('SELECT headtypecode,headclasscode FROM players WHERE spid=?',(spid,)).fetchone()
            if tuple(row)!=(fix['headtypecode'],fix['headclasscode']):errors.append('Legacy preset class mismatch '+str(spid))
    if {key:filehash(p) for key,p in source_files.items()}!=hashes:errors.append('Inputs changed during semantic validation')
    con.close()
    if errors:raise ValueError('Player import validation failed:\n'+'\n'.join(errors[:100]))
    return dict(status='PLAYER_IMPORT_FULL_PASS',input_hashes=hashes,portrait_hashes=portrait_hashes,custom_cards=len(cards),custom_identities=len(pids),native_player_rows=len(ids),models=len(models),language_rows=language_rows,warnings=warnings,native_runtime_proven=False,match_proven=False)
def re_search(pattern,value):
    import re
    return re.search(pattern,value,re.S) is not None
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--server',type=pathlib.Path,default=HERE.parents[1]);p.add_argument('--client',type=pathlib.Path,default=pathlib.Path('D:/FO3ID/32795'))
    for name in ['database','data0','data3','data4','data6','imports','registry','portraits','certificate','write-certificate']:p.add_argument('--'+name,type=pathlib.Path)
    p.add_argument('--full',action='store_true');a=p.parse_args();args=vars(a);output=args.pop('write_certificate')
    if output and not a.full:p.error('--write-certificate requires --full')
    try:
        result=validate(**args)
        if output:output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({k:v for k,v in result.items() if k not in ['input_hashes','portrait_hashes']},ensure_ascii=True));return 0
    except (ValueError,KeyError,OSError,sqlite3.Error,struct.error) as e:print(str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
