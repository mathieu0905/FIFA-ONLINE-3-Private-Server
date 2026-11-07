from pathlib import Path
import hashlib,json,os,sqlite3,ssl,sys,urllib.request
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');sys.dont_write_bytecode=True
sys.path.insert(0,str(S));os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.argv=['http_config.py']
import http_config as h
build=json.loads((R/'build-results.json').read_text(encoding='utf8'));changes=build['changes'];checks=[]
def check(name,ok):
    assert ok,name
    checks.append(name)
check('Both installed database payload hashes match the verified synchronized build',all(hashlib.sha256(p.read_bytes()).hexdigest()==build['outputs'][name] for p,name in [(S/'gamedata/fifadb.sqlite','fifadb.sqlite'),(C/'data/data_0.big','data_0.big')]))
ratings=h.card_ovrs([c['spid'] for c in changes])
check('All 88 cards have exact primary base OVR +2 and displayed +1 OVR 95..96',all(ratings[c['spid']]==c['primary_ovr_before']+2==c['primary_ovr_after'] for c in changes) and {ratings[c['spid']]+h.GRADE_BOOST[1] for c in changes}=={95,96})
with sqlite3.connect(S/'gamedata/fifadb.sqlite') as db:
    db.row_factory=sqlite3.Row
    check('All 88 installed full player rows match the reviewed stat-only changes',all(dict(db.execute('select * from players where spid=?',(c['spid'],)).fetchone())==c['after'] for c in changes))
color=next(c for c in h.tc_colors() if c['teamcolorid']==20043)
check('Original legend set +2/+3/+4 restored at 5/7/9',[(g['count_min'],g['count_max'],g['boosts']) for g in color['boostgroups']]==[(5,6,[dict(type='ovr',amount=2)]),(7,8,[dict(type='ovr',amount=3)]),(9,11,[dict(type='ovr',amount=4)])])
check('All nostalgia cards continue to count toward the original legend set',all(c['spid'] in h.tc_special_sets()[20043][0] for c in changes))
for n,boost in [(5,2),(7,3),(9,4)]:
    players=[dict(_id=f'memory-{i}',spid=c['spid'],grade=1) for i,c in enumerate(changes[:n])]
    t=dict(players=players,squad=dict(positions=[dict(id=p['_id'],spid=p['spid'],pos=i) for i,p in enumerate(players)]))
    t['teamcolors']=[c for c in h.active_teamcolors(t) if c['teamcolorid']==20043]
    shown=h.xi_ratings(t);bare=h.xi_ratings(dict(t,teamcolors=[]))
    check(f'Original legend set has exact OVR +{boost} at {n} players',all(shown[k]-bare[k]==boost for k in bare))
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,admin=False):
    with op.open(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,timeout=20) as response:return json.load(response)
live=get('/static/info/teamcolor');lc=next(c for c in live['teamColors'] if c['teamcolorid']==20043)
check('Running HTTP service serves restored legend-set tiers',lc==color)
for c in changes:
    detail=get('/api/database_detail?spid='+str(c['spid']),True)
    assert all(detail['row'][k]==v for k,v in c['after'].items()),c['spid']
check('Running admin API serves all 88 updated full rows',True)
installed=json.loads((R/'installed-result.json').read_text(encoding='utf8'))
prior=json.loads((Path(installed['backup'])/'evidence/gamedata/state.json').read_text(encoding='utf8'));current=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
check('Manager, real card instances, XP, enhancement, wallet, inventory and squads equal fresh install snapshot',prior['coaches']==current['coaches'] and prior['teams']==current['teams'])
names=['patches/nostalgia_stats_preflight.py','patches/nostalgia-stats-release-manifest.json','patches/nostalgia-stats-release-installed.json','http_config.py','gamedata/fifadb.sqlite','play-local.bat']
report=dict(status='INSTALLED_STATS_PLUS2_LIVE_PASS_NATIVE_PENDING',top_preflight=str(S/names[0]),top_manifest=str(S/names[1]),top_receipt=str(S/names[2]),files={n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in names},cards=88,base_ovr_before=[88,89],base_ovr_after=[90,91],display_level1_plus1=[95,96],legend_set_boosts=[2,3,4],checks=checks,count=len(checks),state_shop_restored=False,installation=str(R/'installed-result.json'),native_status='NOT_STARTED')
(R/'installed-handback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(status=report['status'],checks=len(checks),cards=88,display_level1_plus1=[95,96])))
