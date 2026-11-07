from pathlib import Path
import copy,hashlib,json,shutil,datetime

ROOT=Path(__file__).resolve().parent;SERVER=Path(r'D:\FO3ID\server')
LIMITS={'pack_cadence.json':{'legend_week':20,'peak_week':10,'direct_week':10,'high_grade_week':20,'star_day':30,'classic_month':10},
        'pack_catalogue.json':{'season_day':100,'legend_day':20,'choice_week':20}}
def signature(c):return hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records={}
for filename,limits in LIMITS.items():
    path=SERVER/'gamedata'/filename;raw=path.read_bytes();old=json.loads(raw);new=copy.deepcopy(old)
    new['limits']=limits
    if filename=='pack_catalogue.json':
        for item in new['items'].values():
            group=item['supply'];cap=limits[group]
            if group=='choice_week':item['description']=item['description'].replace('每周共享2包',f'每周共享{cap}包')
            elif group=='legend_day':item['description']=item['description'].replace('每日共享2包',f'每日共享{cap}包')
            else:item['description']=item['description'].replace('每日共享10包',f'每日共享{cap}包')
    new['hash']=signature({k:v for k,v in new.items() if k!='hash'})
    (ROOT/filename).write_text(json.dumps(new,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    (ROOT/('before-'+filename)).write_bytes(raw)
    records[filename]=dict(before_sha256=sha(path),after_sha256=sha(ROOT/filename),before_limits=old['limits'],after_limits=limits)
launcher=(SERVER/'play-local.bat').read_bytes()
assert launcher.count(b'patches\\xp30_batch_preflight.py')==1
(ROOT/'play-local.bat').write_bytes(launcher.replace(b'patches\\xp30_batch_preflight.py',b'patches\\pack_limits_preflight.py'))
records['play-local.bat']=dict(before_sha256=sha(SERVER/'play-local.bat'),after_sha256=sha(ROOT/'play-local.bat'))
(ROOT/'changes.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(records))
