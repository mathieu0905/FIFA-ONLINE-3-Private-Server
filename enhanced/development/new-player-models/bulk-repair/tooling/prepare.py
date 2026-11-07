"""Finish a UI import artifact with native records, rig conversion and validation.

The input UI database/data0/registry must already contain the intended cards and
six-language names. This tool writes a new output folder, never the live game.
Publication uses the shared official release transaction after a full PASS.
"""
import argparse,hashlib,json,pathlib,shutil,sys
HERE=pathlib.Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['spec','server','client','database','data0','registry','imports','output']:p.add_argument('--'+n,required=True,type=pathlib.Path)
    p.add_argument('--portraits',type=pathlib.Path)
    a=p.parse_args();S,C=a.server.resolve(),a.client.resolve();out=a.output.resolve()
    if out.exists() or out.is_relative_to(S) or out.is_relative_to(C):raise ValueError('Output must be a new workspace folder outside the live server/client')
    sys.path[:0]=[str(HERE),str(S/'tools/re'),str(S)]
    import bigdir,eadb,native_db,ordered_big,refpack,rx3,check,sqlite3
    inputs=[a.spec,a.database,a.data0,a.registry,a.imports]+[C/f'data/data_{i}.big' for i in [3,4,6]]
    before={str(path):ordered_big.digest(path) for path in inputs}
    spec=json.loads(a.spec.read_text('utf8'));policy=json.loads(a.imports.read_text('utf8'));registry=json.loads(a.registry.read_text('utf8'))
    if spec.get('schema')!=1 or not spec.get('players'):raise ValueError('Invalid player package schema')
    rig=json.loads((HERE/'rig-map.json').read_text('utf8'));rawdb=bigdir.read(a.data0,'data/db/fifa_ng_db.db');meta=bigdir.read(a.data0,'data/db/fifa_ng_db-meta.xml').decode('utf8');_,_,_,index,t,fields=native_db.player_table(rawdb,meta)
    key=fields['playerid']['shortname'];indices={t.get(row,key):i for i,row in enumerate(t.rows)};template=t.find(key,231747);out.mkdir(parents=True)
    con=sqlite3.connect(a.database.resolve().as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
    replacements={3:{},4:{},6:{}};added=[];lua=bigdir.read(a.data0,'data/fifarna/lua/assets/player.lua').decode('latin1')
    marker='\tif (modernFaceAsset ~= nil) then'
    if marker not in lua:raise ValueError('Lua integration point not recognized; preserve the current script and review its routes')
    for player in spec['players']:
        pid,spid=player['playerid'],player['spid'];row=con.execute('SELECT * FROM players WHERE spid=?',(spid,)).fetchone()
        if row is None or row['playerid']!=pid or not any(c['base_playerid']==pid and c['fo3_spid']==spid for c in registry['cards']):raise ValueError('UI/registry identity missing or inconsistent')
        semantic=dict(row)
        if 'source_skill_stars' not in player and player.get('skill_input')!='fo3-code':raise ValueError('Declare source_skill_stars or skill_input=fo3-code; do not guess star units')
        if 'source_skill_stars' in player and semantic['skillmoves']!=native_db.stars_to_code(player['source_skill_stars']):raise ValueError('UI builder must convert source stars to FO3 code before native import')
        selector=semantic['headtypecode']
        if semantic['headclasscode']!=1 or not 30001<=selector<=65535:raise ValueError('Dedicated import requires an explicit reserved UI selector')
        if any(m['playerid']==pid for m in policy['models']) and not player.get('replace_existing'):raise ValueError('Existing imported model requires explicit replace_existing')
        same_selector=next((m for m in policy['models'] if m['reserved_selector']==selector and m['playerid']!=pid),None)
        if same_selector:raise ValueError('Reserved selector already belongs to another player')
        expected=[(3,'faces',f'face_{pid}_0_0_0_0_0_0_0_0_textures.rx3','texture'),(4,'heads',f'head_{pid}_0.rx3','mesh'),(4,'hair',f'hair_{pid}_0_0.rx3','mesh'),(4,'hair',f'hair_{pid}_0_textures.rx3','texture'),(6,'hairlod',f'hairlod_{pid}_0_0.rx3','mesh')]
        if set(player['files'])!={n for _,_,n,_ in expected}:raise ValueError('A dedicated face requires exactly head/hair/hairLOD/face texture/hair texture')
        files=[]
        for idx,folder,name,kind in expected:
            source=player['files'][name];raw=pathlib.Path(source['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Package source SHA mismatch: '+name)
            member=f'data/sceneassets/{folder}/{name}'
            if kind=='mesh':
                if player['source_rig']=='FIFA14_Switch':
                    native=bigdir.read(C/f'data/data_{idx}.big',member.replace(str(pid),'231747'));raw,proof=rx3.retarget(raw,native,rig)
                elif player['source_rig']=='ImpactEngine':rx3.validate(raw,252)
                else:raise ValueError('Unknown rig; do not infer compatibility from the RX3 extension or bone count')
            else:rx3.sections(rx3.unwrap(raw))
            replacements[idx][member]=(raw,0);files.append(dict(archive=idx,member=member,sha256=hashlib.sha256(raw).hexdigest(),kind=kind))
        semantic.update(player.get('native_overrides',{}));semantic.update(playerid=pid,spid=spid,headassetid=pid,headtypecode=1023,headclasscode=0)
        encoded=native_db.encode(t,fields,t.rows[indices[pid]] if pid in indices else template,semantic)
        if pid in indices:t.rows[indices[pid]]=encoded
        else:indices[pid]=len(t.rows);t.rows.append(encoded)
        if pid not in set(policy['native_base_ids']):
            policy['native_imports']=[r for r in policy['native_imports'] if r['playerid']!=pid]+[dict(playerid=pid,raw_sha256=hashlib.sha256(encoded).hexdigest())]
        clause=f'\tif (db.player[idx].headClass == 1 and db.player[idx].head == {selector}) then modernFaceAsset = {pid} end\n'
        lua=lua.replace(marker,clause+marker,1)
        model=dict(playerid=pid,spid=spid,name=player.get('name',str(pid)),reserved_selector=selector,rig='ImpactEngine',native_home_verified=False,native_match_verified=False,files=files)
        policy['models']=[m for m in policy['models'] if m['playerid']!=pid]+[model];added.append(pid)
    con.close()
    if len(t.rows)>65535:raise ValueError('Native row count exceeds UInt16; do not publish')
    native=native_db.rebuild(rawdb,index,t);packed=refpack.refpack(native);lua=lua.encode('latin1');plua=refpack.refpack(lua)
    ordered_big.rebuild(a.data0,out/'data_0.big',{'data/db/fifa_ng_db.db':(packed,len(native)),'data/fifarna/lua/assets/player.lua':(plua,len(lua))})
    for idx in [3,4,6]:ordered_big.rebuild(C/f'data/data_{idx}.big',out/f'data_{idx}.big',replacements[idx])
    shutil.copyfile(a.database,out/'fifadb.sqlite');shutil.copyfile(a.registry,out/'custom_rosters.json');(out/'player-imports.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding='utf8')
    result=check.validate(S,C,database=out/'fifadb.sqlite',data0=out/'data_0.big',data3=out/'data_3.big',data4=out/'data_4.big',data6=out/'data_6.big',imports=out/'player-imports.json',registry=out/'custom_rosters.json',portraits=a.portraits,full=True)
    if {str(path):ordered_big.digest(path) for path in inputs}!=before:raise ValueError('Import source changed during preparation')
    (out/'player-import-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'source-baseline.json').write_text(json.dumps(before,indent=2),encoding='utf8')
    print(json.dumps(dict(status='PREPARED_FULL_PASS_NOT_INSTALLED',players=added,output=str(out),native_verified=False)));return 0
if __name__=='__main__':raise SystemExit(main())
