"""Real HTTP, replay, quota, rollback and display-contract checks in the sandbox."""
import concurrent.futures
import copy
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import shutil
import sys
import threading

ROOT = Path(__file__).resolve().parent
SERVER = ROOT/'sandbox/server'
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
shutil.copyfile(ROOT/'pack_catalogue.py',SERVER/'pack_catalogue.py')
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(SERVER))
sys.argv=['http_config.py']
outside_writes=[]
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_CREAT|os.O_WRONLY|os.O_RDWR|os.O_TRUNC))):
            path=Path(os.fsdecode(name)).resolve()
            if not path.is_relative_to(ROOT):
                outside_writes.append(str(path));raise PermissionError('External write: '+str(path))
sys.addaudithook(audit)
import http_config as h

checks=[]
def check(label,condition):
    assert condition,label
    checks.append(label)

c=h.pack_catalogue
legacy=json.loads((SERVER/'gamedata/pack_cadence.json').read_text(encoding='utf-8'))
for key,data in legacy['legacy'].items():
    assert h.pack_pool(int(key))==[tuple(r) for r in data['pool']]
    assert h.pack_grades(int(key))==[tuple(r) for r in data['grades']]
check('All frozen legacy pools and grade weights unchanged',True)
check('Existing cadence config is unmodified',h.pack_cadence.config==legacy)
entries=c['items']
for key,d in entries.items():
    itemid=int(key);definition=h.item_def(itemid)
    assert {s//1000000 for s in d['pool']}==set(d['seasons'])
    assert h.pack_pool(itemid)==[(s,1.0) for s in d['pool']]
    assert h.pack_grades(itemid)==[(1,1)]
    assert '（' in definition['description'] and '）' in definition['description']
    assert definition['bunches']==[dict(bunch=1,price=d['price'])]
    assert ('任选1名' in definition['description'])==(d['mode']=='choice')
check('54 new definitions: exact nonempty frozen pools, Chinese season labels, correct random/choice and +1',True)
seed=h._state()
seed_coach=h.my_coach(seed)
seed_coach['cash']=10**9
seed_coach['items']=[x for x in seed_coach.get('items',[]) if x['itemid'] not in map(int,entries)]
seed_coach.pop('pack_catalogue_receipts',None)
seed.pop('pack_catalogue_supply',None)
h._save(seed)

srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),h.H)
thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
def call(path,body=None,method=None):
    connection=http.client.HTTPConnection('127.0.0.1',srv.server_port,timeout=45)
    connection.request(method or ('POST' if body is not None else 'GET'),path,
                       json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json'})
    response=connection.getresponse();data=response.read();connection.close()
    assert response.status==200,(path,response.status,data[:200])
    return json.loads(data)
def reset():h._save(copy.deepcopy(seed))
def snapshots():return (SERVER/'gamedata/state.json').read_bytes()
def grant(itemid,count=1):
    st=h._state();h.inventory_add(h.my_coach(st),itemid,count);h._save(st)
    return next(x for x in h.coach_items(st,h._default_slot(st)) if x['itemid']==itemid)['_id']
def asset_count():return len(h._state()['teams'][str(h._default_slot(h._state()))]['players'])

try:
    before=snapshots();listing=call('/shop/list')
    listed={r['product']['itemid']:r for r in listing}
    check('Native /shop/list contains all 54 new packs',set(map(int,entries))<=set(listed))
    definitions=call('/static/cache/item',{'itemids':list(map(int,entries))+list(map(int,legacy['items']))})
    check('Native static cache resolves every new and current pack',len(definitions)==len(entries)+len(legacy['items']))
    check('Read-only listing/static requests preserve state bytes',snapshots()==before)
    check('All current 14 names and Chinese season descriptions reach native fields',all('赛季范围' in definitions[k]['description'] and '多赛季' not in definitions[k]['name'] for k in legacy['items']))

    random_id=97100022;choice_id=97200911
    d=entries[str(choice_id)]
    before_cash=h.my_coach(h._state())['cash']
    bought=call('/shop/purchase',{'productid':choice_id,'bunch':0})
    check('Purchase debits exact point price and grants one native DRAFTPACK',bought['result'] and h.my_coach(h._state())['cash']==before_cash-d['price'])
    st=h._state();token=next(x for x in h.coach_items(st,h._default_slot(st)) if x['itemid']==choice_id)['_id']
    check('Choice inventory carries an opaque one-opening id', '_pc_' in token)
    before=snapshots()
    check('Native choice initialization never preselects a player',call(f'/item/draftpack/{choice_id}/players/1')==[])
    options=call(f'/packchoice/{choice_id}/search?q=&league=255&team=255')
    check('TOP10 choice returns precisely the 10 frozen candidates',len(options)==10 and {x['spid'] for x in options}==set(d['pool']))
    alloptions=call(f'/item/draftpack/{choice_id}/players/1000')
    check('Native draft candidates are restricted to the issued pool',len(alloptions)==10)
    check('Opening/cancelling the selection UI does not consume or write assets',snapshots()==before)
    foreign=next(s for s in h.market_spids() if s not in d['pool'])
    for req in ({}, {'spids':[foreign]}, {'spids':d['pool'][:2]}, {'spids':[True]}, {'spids':[str(d['pool'][0])]}):
        result=call('/item/'+token+'/use',req)
        assert not result['result'] and snapshots()==before
    check('Missing, foreign, multiple, bool and string choices reject without consumption',True)
    spid=d['pool'][0];n=asset_count()
    result=call('/item/'+token+'/use',{'spids':[spid]})
    check('User-selected exact SPID is awarded at +1',result['result'] and result['player']['spid']==spid and result['player']['grade']==1 and asset_count()==n+1)
    before=snapshots();again=call('/item/'+token+'/use',{'spids':[spid]})
    check('Retry returns persisted receipt without duplicated card/consumption',again.get('replayed') and snapshots()==before and again['player']==result['player'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(lambda _:call('/item/'+token+'/use',{'spids':[spid]}),range(4)))
    check('Four concurrent retries reuse one committed receipt',all(x.get('replayed') for x in results) and snapshots()==before)
    changed=call('/item/'+token+'/use',{'spids':[d['pool'][1]]})
    check('A committed token cannot choose a second player',not changed['result'] and snapshots()==before)
    reset();token=grant(choice_id,2);n=asset_count()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(lambda _:call('/item/'+token+'/use',{'spids':[spid]}),range(4)))
    st=h._state();raw=next(i for i in h.my_coach(st)['items'] if i['itemid']==choice_id)
    check('Concurrent first opens consume exactly one from a stack of two',asset_count()==n+1 and raw['remains']==1 and sum(not x.get('replayed',False) for x in results)==1)
    nexttoken=next(x for x in h.coach_items(st,h._default_slot(st)) if x['itemid']==choice_id)['_id']
    check('Next deliberate opening has a fresh id',nexttoken!=token)
    result=call('/item/'+nexttoken+'/use',{'spids':[spid]})
    check('A second intentional choice can award the same player',result['result'] and asset_count()==n+2)

    reset();token=grant(random_id,2);n=asset_count()
    result=call('/item/'+token+'/use',{})
    again=call('/item/'+token+'/use',{})
    check('Random season pack only awards its own season and replays safely',result['player']['spid']//1000000==22 and again.get('replayed') and asset_count()==n+1)
    reset();token=grant(choice_id)
    st=h._state();t=st['teams'][str(h._default_slot(st))]
    t['players']+= [copy.deepcopy(t['players'][0]) for _ in range(h.MAX_PLAYERS-len(t['players']))]
    h._save(st);before=snapshots()
    result=call('/item/'+token+'/use',{'spids':[spid]})
    check('Full roster rejects without consuming',not result['result'] and snapshots()==before)

    reset();token=grant(choice_id);before=snapshots();save=h._save
    def failed_save(st):raise OSError('injected pre-commit failure')
    h._save=failed_save
    try:
        try:h.ep_item_use(token,'',json.dumps({'spids':[spid]}).encode())
        except OSError:pass
        else:raise AssertionError('Save failure hidden')
    finally:h._save=save
    check('Pre-commit failure leaves persisted cards/inventory unchanged',snapshots()==before)
    reset()
    for i in range(2):assert call('/shop/purchase',{'productid':choice_id,'bunch':0})['result']
    before=snapshots();result=call('/shop/purchase',{'productid':97200910,'bunch':0})
    check('All choice SKUs share account weekly quota, rejection does not charge',not result['result'] and snapshots()==before)
    # Re-imported definitions, saves and new packs never change immutable old configurations.
    check('Frozen existing cadence remains equal after transactions',h.pack_cadence.config==legacy)
    check('No write outside the isolated release directory',not outside_writes)
finally:
    srv.shutdown();srv.server_close();thread.join(timeout=3)
report={'status':'PASS','checks':checks,'count':len(checks),'production_writes':outside_writes,'native_runtime_verified':False,
        'tested_files':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('http_config.py','shop_season_names.py','pack_catalogue.py','pack_catalogue.json')}}
(ROOT/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
