"""Native 8088 regression: reads and invalid mutations only, no user data writes."""
from pathlib import Path
import hashlib,json,re,urllib.request,urllib.error
BASE='http://127.0.0.1:8088'
def request(path,body=None,headers=None):
    r=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers or {})
    try:
        with urllib.request.urlopen(r,timeout=8) as response:return response.status,response.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
def data(path):return json.loads(request(path)[1])
def assets():
    s=json.loads(Path('D:/FO3ID/server/gamedata/state.json').read_text('utf-8'))
    return {k:s[k] for k in ('teams','coaches') if k in s}
before=assets()
code,page=request('/');assert code==200 and b'data-tab="database"' in page and b'src="/database"' in page
code,page=request('/database');assert code==200 and b'/api/database_' in page and b':8090' not in page
status=data('/api/database_status');assert status['count']>60000 and len(status['fields'])==43
assert '世界传奇' in status['season_labels']['93'] and status['season_labels']['93'].startswith('93 ')
assert status['season_labels']['13']=='13 · 现役精选'
assert '传奇时刻' in status['season_labels']['84']
assert all(str(code)+' · ' in label and re.search('[\u4e00-\u9fff]',label) for code,label in status['season_labels'].items())
search=data('/api/database_search?q=93192181');assert search['total']==1
detail=data('/api/database_detail?spid=93192181');assert detail['row']['height']==188
assert data('/api/summary')['coach']['name']=='ggmu'
assert 'players' in data('/api/players')
assert request('/api/database_stage',dict(spid=93192181))[0]==403
assert request('/api/database_publish')[0]==403
assert request('/api/database_status',headers={'Host':'evil.example'})[0]==403
code,result=request('/api/database_stage',dict(spid=93192181,row_hash=detail['row_hash'],revision=status['draft']['revision'],changes={'height':999}),{'X-FO3-Admin':'1'})
assert 'error' in json.loads(result)
assert data('/api/database_status')['draft']==status['draft']
assert assets()==before
report=dict(status='PASS',checks=17,port=8088,formal_assets_unchanged=True,valid_data_writes=0,publish_readiness=status['publish_readiness'],season_labels={k:status['season_labels'][k] for k in ('12','13','84','93')})
Path(__file__).with_name('8088-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=True))
