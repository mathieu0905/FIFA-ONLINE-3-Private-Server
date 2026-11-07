"""Validate raised limits against the latest backend, only in an isolated snapshot."""
from pathlib import Path
import copy,datetime,hashlib,json,os,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parent;SOURCE=Path(r'D:\FO3ID\server')
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf8')
checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,condition):assert condition,name;checks.append(name)
with tempfile.TemporaryDirectory(prefix='pack-limits-') as td:
    private=Path(td)/'server';private.mkdir()
    for p in [*SOURCE.glob('*.py'),*SOURCE.glob('*.json')]:shutil.copyfile(p,private/p.name)
    for name in ('gamedata','responses','admin','tools'):
        shutil.copytree(SOURCE/name,private/name,ignore=shutil.ignore_patterns('migration-backups','__pycache__','*.bak*','*.log','replays'))
    before={}
    for name in ('pack_cadence.json','pack_catalogue.json'):
        before[name]=json.loads((private/'gamedata'/name).read_text(encoding='utf8'))
        shutil.copyfile(ROOT/name,private/'gamedata'/name)
    def audit(event,args):
        if event=='open':
            name,mode,flags=args
            if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_CREAT|os.O_WRONLY|os.O_RDWR|os.O_TRUNC))):
                p=Path(os.fsdecode(name)).resolve()
                if not p.is_relative_to(Path(td)) and not p.is_relative_to(ROOT):raise PermissionError('External write blocked: '+str(p))
    sys.addaudithook(audit)
    os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
    sys.path.insert(0,str(private));sys.argv=['http_config.py']
    import http_config as h
    for fn,old in before.items():
        new=json.loads((ROOT/fn).read_text(encoding='utf8'))
        check(fn+' signed',new['hash']==hashlib.sha256(json.dumps({k:v for k,v in new.items() if k!='hash'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())
        check(fn+' all caps increased',all(new['limits'][g]>n for g,n in old['limits'].items()))
        if fn=='pack_cadence.json':
            a,b=copy.deepcopy(old),copy.deepcopy(new)
            for x in (a,b):x.pop('hash');x.pop('limits')
            check('All issued old pools, weights, grades, prices, pity, item versions and chain entitlements identical',a==b)
        else:
            a,b=copy.deepcopy(old),copy.deepcopy(new)
            for x in (a,b):
                x.pop('hash');x.pop('limits')
                for item in x['items'].values():item.pop('description')
            check('All 54 new pools, prices, modes, grades, token key and edition identical',a==b)
    st=h._state();coach=h.my_coach(st);coach['cash']=10**9
    st['pack_catalogue_supply']={'season_day':{'period':h.today_wib(),'used':10},'legend_day':{'period':h.today_wib(),'used':2},'choice_week':{'period':h.pack_cadence.periods()['week'],'used':2}}
    st['pack_cadence_supply']={'legend_week':{'period':h.pack_cadence.periods()['week'],'used':2},'peak_week':{'period':h.pack_cadence.periods()['week'],'used':1},'classic_month':{'period':h.pack_cadence.periods()['month'],'used':1}}
    h._save(st);seed=copy.deepcopy(st)
    expected={97100022:90,97100900:18,97200911:18,97010004:18,97010005:9,97010007:9,97010110:9}
    raw=(private/'gamedata/state.json').read_bytes()
    for itemid,left in expected.items():
        check('Preserved used count -> correct remaining '+str(itemid),h.pack_cadence.remaining(h._state(),itemid)==left)
        row=h.shop_entry(itemid);check('Native displayed remaining '+str(itemid),row['remained']==left and row['remainedperaccount']==left and row['buy'])
    check('Quota/read-only display checks do not reset counters or write state',(private/'gamedata/state.json').read_bytes()==raw)
    for itemid in (97100022,97100900,97200911,97010004):
        previous=h._state();cash=h.my_coach(previous)['cash'];left=h.pack_cadence.remaining(previous,itemid)
        out=json.loads(h.ENDPOINTS['/shop/purchase']('',json.dumps({'productid':itemid,'bunch':0}).encode())[1])
        after=h._state()
        check('Purchase works after old exhausted quota '+str(itemid),out['result'] and h.my_coach(after)['cash']==cash-h.product_price(itemid,1) and h.pack_cadence.remaining(after,itemid)==left-1)
    st=h._state();st['pack_catalogue_supply']['season_day']['used']=100;h._save(st);raw=(private/'gamedata/state.json').read_bytes()
    out=json.loads(h.ENDPOINTS['/shop/purchase']('',json.dumps({'productid':97100022,'bunch':0}).encode())[1])
    check('New cap enforced without overcharging',not out['result'] and (private/'gamedata/state.json').read_bytes()==raw)
    for key,item in h.pack_catalogue['items'].items():
        cap=h.pack_catalogue['limits'][item['supply']]
        checktext=f'每周共享{cap}包' if item['supply']=='choice_week' else f'每日共享{cap}包'
        assert checktext in h.item_def(int(key))['description'],key
    check('All 54 native descriptions disclose the new shared caps',True)
    # Real endpoint list, not just configuration values.
    listing=json.loads(h.ENDPOINTS['/shop/list']('',b'')[1]);byid={e['product']['itemid']:e for e in listing}
    check('Native /shop/list reflects latest quota and max stock',byid[97100022]['remained']==0 and byid[97100022]['limittotalcount']==100 and byid[97200911]['limittotalcount']==20)
report=dict(status='PASS',checks=checks,count=len(checks),tested_files={n:sha(ROOT/n) for n in ('pack_cadence.json','pack_catalogue.json')},production_state_written=False)
(ROOT/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
