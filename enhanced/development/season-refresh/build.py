"""Build only per-SPID balance deltas and a compatibility-preserving retirement."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,math,shutil,sqlite3,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
WORK=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path.insert(0,str(WORK/'work/season_expansion'));import roster_import as codec
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def main():
    out=R/'build-v7';assert not out.exists();out.mkdir()
    inputs=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json',S/'http_config.py',S/'product_packs.py',S/'gamedata/all_item_icon_manifest.json',S/'npc_exchange.py']
    sources={str(p):sha(p) for p in inputs}
    module=ast.parse((S/'http_config.py').read_text('utf-8'));ns={}
    for node in module.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ROLE_WEIGHTS','POS_ROLE','POSOVR') for t in node.targets):exec(compile(ast.Module(body=[node],type_ignores=[]),'<current native rating>','exec'),ns)
    registry=read(S/'gamedata/custom_rosters.json');modern={int(x['fo3_spid']) for x in registry['cards'] if x['fo3_spid']//1000000==13};assert len(modern)==257
    retired=[x for x in registry['cards'] if x['fo3_spid']//1000000==12];assert len(retired)==123
    columns='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
    database=out/'fifadb.sqlite';shutil.copyfile(S/'gamedata/fifadb.sqlite',database)
    report=[]
    with sqlite3.connect(database.as_uri(),uri=True) as db:
        db.row_factory=sqlite3.Row
        for spid in sorted(modern):
            before=dict(db.execute('select * from players where spid=?',(spid,)).fetchone())
            weights=ns['ROLE_WEIGHTS'][ns['POS_ROLE'][before['preferredposition1']]]
            rating=lambda row:sum(row[k]*v for k,v in weights.items())//100+5
            old=rating(before)
            target=min(92,max(old,round(84+(old-73)*8/18)))
            for delta in range(0,35):
                after={k:min(99,before[k]+delta) for k in columns}
                if rating(after)>=target:break
            assert target==rating(after) and rating(after)<=92
            db.execute('update players set '+','.join('"'+k+'"=?' for k in columns)+',overallrating=? where spid=?',
                       [after[k] for k in columns]+[min(99,before['overallrating']+delta),spid])
            report.append(dict(spid=spid,before_plus1=old,after_plus1=rating(after),raw_attribute_delta=delta))
        db.execute('update permid set transferable=0 where spid/1000000=12')
        assert db.execute('select count(*) from permid where spid/1000000=12 and transferable!=0').fetchone()[0]==0
        db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        db.execute('attach database ? as old',((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',))
        ids=','.join(map(str,sorted(modern)))
        assert db.execute(f'select count(*) from (select * from players where spid not in ({ids}) except select * from old.players where spid not in ({ids}))').fetchone()[0]==0
        for (table,) in db.execute("select name from old.sqlite_master where type='table'").fetchall():
            if table=='permid':assert not db.execute('select * from permid where spid/1000000!=12 except select * from old.permid where spid/1000000!=12').fetchone()
            elif table!='players':assert not db.execute(f'select * from "{table}" except select * from old."{table}"').fetchone(),table
    for card in registry['cards']:
        if card['fo3_spid'] in modern:card['fo3_balance_adjustment']=next(x for x in report if x['spid']==card['fo3_spid'])|{'policy':'Native untrained +1 position OVR compressed to84..92; preserve original strengths and all instance progress'}
    registry['cards']=[x for x in registry['cards'] if x['fo3_spid']//1000000!=12]
    registry['seasons']=[x for x in registry['seasons'] if x['id']!=12]
    for card in retired:card.update(retired=True,npc_exclusion_policy='season_retirement runtime plus native transferable=0',retirement_reason='Duplicate legend season removed from new acquisition; legacy issued packs remain compatible')
    registry.setdefault('retired_cards',[]).extend(retired)
    registry.setdefault('retired_seasons',[]).append(dict(id=12,label='传奇精选',reason='重复原生传奇卡种，停止新发行；保留旧库存兼容数据'))
    write(out/'custom_rosters.json',registry)
    roster=read(S/'responses/static_roster.json');roster['seasons']=[x for x in roster['seasons'] if 12 not in x.get('value',[])];write(out/'static_roster.json',roster)
    source=(S/'http_config.py').read_bytes();anchor=b'if __name__ == "__main__":';assert source.count(anchor)==1
    (out/'http_config.py').write_bytes(source.replace(anchor,b'import season_retirement\nseason_retirement.install(sys.modules[__name__])\n\n'+anchor))
    packs=(S/'product_packs.py').read_text('utf-8')
    old="    market=set(h.market_spids())\n";assert packs.count(old)==1
    packs=packs.replace(old,old+"    legacy_compat={int(c['fo3_spid']) for c in json.loads((Path(h.HERE)/'gamedata/custom_rosters.json').read_text('utf-8')).get('retired_cards',[]) if int(c['fo3_spid'])//1000000==12}\n")
    old="not set(t['pool'])<=market";assert packs.count(old)==1
    packs=packs.replace(old,"not set(t['pool']) <= (market | legacy_compat)")
    old="'reward_upgrade_products.json')";assert packs.count(old)==1
    packs=packs.replace(old,"'reward_upgrade_products.json','season_refresh_products.json')")
    (out/'product_packs.py').write_text(packs,'utf-8')
    npc=(S/'npc_exchange.py').read_text('utf-8')
    for old in ["        for key,asset in w['assets'].items():\n", "            asset=w['assets'][key];row=asset.get('listing')\n"]:
        assert npc.count(old)==1
        indent='            ' if old.startswith('        for ') else '            '
        npc=npc.replace(old,old+indent+"if not self.market.valid_card(asset['spid'],asset['grade']):continue\n")
    (out/'npc_exchange.py').write_text(npc,'utf-8')
    # New issuance uses an existing native-legend TOP10 pool; original signed
    # products and partially paid rounds remain available only for legacy rights.
    base=read(S/'gamedata/chain_rebalance_products.json')
    newpack=copy.deepcopy(base['strength_packs']['98100006'])
    newpack.update(name='原生传奇TOP10·自选+13',grades=[0]*12+[100])
    newpack['tiers'][0]['name']='原生经典传奇TOP10'
    newpack['description']='原生经典传奇TOP10候选中自选1人，固定+13；不含已退场的传奇精选赛季。'
    newpack['price']=round(newpack['price']*1.2/100)*100
    newroot=71360501;oldtrack=base['chains']['71250501'];newtrack=copy.deepcopy(oldtrack)
    newtrack.update(name='五档全自选连锁·原生传奇版',steps=list(range(newroot,newroot+5)),round_steps=[list(range(newroot+r*5,newroot+r*5+5)) for r in range(oldtrack['rounds'])],packages={},prices={})
    for oldsteps,newsteps in zip(oldtrack['round_steps'],newtrack['round_steps']):
        for oldid,newid in zip(oldsteps,newsteps):
            d=copy.deepcopy(oldtrack['packages'][str(oldid)]);d['name']=d['name'].replace(oldtrack['name'],newtrack['name'])
            d['contents']=[[98500020 if i==98100020 else i,n] for i,n in d['contents']]
            newtrack['packages'][str(newid)]=d
            newtrack['prices'][str(newid)]=round(newpack['price']*.65/100)*100 if any(i==98500020 for i,n in d['contents']) else oldtrack['prices'][str(oldid)]
    addon=dict(schema=1,edition='20261107-season-refresh-v1',limits={'98500020':dict(count=0,period='once')},risk_packs={},strength_packs={'98500020':newpack},bundles={},chains={str(newroot):newtrack},chain_only_items=[98500020],retired_sale_items=[97300012,98100020],retired_chains=[71250501])
    # This price follows the already-reviewed +12 native TOP10 pack's grade
    # scaling; all later ordinary offers still use the shared value function.
    addon['hash']=hashlib.sha256(json.dumps(addon,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write(out/'season_refresh_products.json',addon)
    icons=read(S/'gamedata/all_item_icon_manifest.json')
    icons['items']['98500020']={**icons['items']['98100008'],'itemid':98500020}
    for oldsteps,newsteps in zip(oldtrack['round_steps'],newtrack['round_steps']):
        for k,(oldid,newid) in enumerate(zip(oldsteps,newsteps)):
            art='98100008' if k==1 else str(oldid)
            icons['items'][str(newid)]={**icons['items'][art],'itemid':newid}
    write(out/'all_item_icon_manifest.json',icons)
    shutil.copyfile(R/'season_retirement.py',out/'season_retirement.py')
    big,decrypt,replace,refpack,encrypt=codec.load_codecs(S)
    archive=out/'data_0.big';shutil.copyfile(C/'data/data_0.big',archive)
    member='data/db2/fifadb.db.db2';old=bytes(decrypt.decrypt(big.read(archive,member)))
    assert b'SQLite format 3\0'+old[16:]==(S/'gamedata/fifadb.sqlite').read_bytes(),'Client/server DB baseline mismatch'
    raw=encrypt(old[:16]+database.read_bytes()[16:]);replace(archive,member,refpack(raw),len(raw))
    assert b'SQLite format 3\0'+bytes(decrypt.decrypt(big.read(archive,member)))[16:]==database.read_bytes()
    spec=importlib.util.spec_from_file_location('layout',WORK/'tools/check_data0_layout.py');layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
    check=layout.inspect(archive,C/'data/data_0.big',changed_members={member},expected_count=271);assert check['status']=='PASS',check
    write(out/'layout.json',check)
    assert sources=={str(p):sha(p) for p in inputs},'Input changed during build; rebase before install'
    before=[r['before_plus1'] for r in report];after=[r['after_plus1'] for r in report]
    summary=dict(status='BUILD_AND_RESOURCE_READBACK_PASS',sources=sources,files={p.name:sha(p) for p in out.iterdir() if p.is_file()},active_modern_cards=257,retired_legend_cards=123,
      before_plus1=dict(min=min(before),max=max(before),mean=sum(before)/len(before)),after_plus1=dict(min=min(after),max=max(after),mean=sum(after)/len(after)),
      non_target_rows_and_tables_exact=True,permid_exception='Only season12 transferable set0',client_server_sqlite_exact=True,all_other_270_big_members_exact=True,native_verified=False)
    write(out/'balance-rows.json',report);write(out/'build.json',summary);print(json.dumps(summary,ensure_ascii=True))
if __name__=='__main__':main()
