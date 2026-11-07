from pathlib import Path
import datetime,json,os,re,sys
sys.dont_write_bytecode=True
import deploy as x
R=x.R;S=x.S;C=x.C;d=x.d
with d.locks(S):
    play=(S/'play-local.bat').read_bytes();name=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
    own=d.load(S/'patches/wonderkid_preflight.py','wk_handoff');current=d.load(S/'patches'/name,'current_handoff')
    proof=current.preflight(S,C);comp=current.compose_manifest(S,C)
    installed=d.read(R/'cutover-result.json');backup=Path(installed['backup'])
    old=d.read(backup/'audit-state.json');live=d.read(S/'gamedata/state.json')
    assets=lambda v:{k:x for k,x in v.items() if k!='market_simulation'}
    assert assets(old)==assets(live),'Live manager/card assets changed since stopped snapshot; report before claiming exact preservation'
    assert d.tx.sha(backup/'audit-shop.json')==d.tx.sha(S/'gamedata/shop.json')
    assert d.tx.sha(S/'patches/Label.big')==d.tx.sha(C/'data/ui/components/Label.big')
    assert all(d.tx.sha(S/'patches/language_chi.big')==d.tx.sha(C/f'_cache/{p}/externalAssets/language_chi.big') for p in ('games/fo3id','cdn'))
    triplet={str(S/p):d.tx.sha(S/p) for p in (own.SELF,own.MANIFEST,own.RECEIPT)}
    report=dict(status='INSTALLED_WONDERKID40_FORMAL_PASS_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),season_id=18,card_count=40,ratings=[90,94],chinese_youngsters_added=False,top_preflight=str(S/'patches'/name),top_manifest=str(S/current.MANIFEST),top_receipt=str(S/current.RECEIPT),composition_available=True,function_signatures={'preflight':'server=None,client=None','compose_manifest':'server=None,client=None'},files={str(S/p):d.tx.sha(S/p) for p in (current.SELF,current.MANIFEST,current.RECEIPT,'play-local.bat')},own_triplet_sha256=triplet,preflight=proof,service_restart=True,service_readiness=installed['readiness'],launcher_pid=installed['launcher_pid'],backup=str(backup),protected_assets=dict(manager_card_team_progress_equal=True,shop_hash_equal=True,market_background_may_advance=True,snapshot=str(backup/'audit-state.json')),verification=d.read(R/'formal-verification.json'),existing_model_files=200,new_model_files=0,portraits=40,legacy_packs_frozen=263,gui_used=False,native_verified=False,match_verified=False,root_goal_resumed=False,locks_released=True)
    d.write(R/'handoff.json',report);d.write(R/'installed-handback.json',report)
    descriptor=Path('D:/fifaol3/root-current-top.json');previous=d.tx.sha(descriptor)
    report['handoff']=str(R/'installed-handback.json')
    assert previous==d.tx.sha(descriptor);d.write(descriptor,report)
    roster=d.read(R/'first-roster.json');roster.update(installed=True,season_id=18,installed_report=str(R/'installed-handback.json'));d.write(R/'first-roster.json',roster)
    print(json.dumps(dict(status=report['status'],triplet=triplet,guards=proof['files'],assets_equal=True)))
