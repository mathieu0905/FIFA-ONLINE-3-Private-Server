"""Read-only production HTTP checks and rejected mutations only."""
import json,urllib.request,urllib.error
BASE='http://127.0.0.1:8090'
def request(path,body=None,headers=None):
    r=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers or {})
    try:
        with urllib.request.urlopen(r,timeout=5) as reply:return reply.status,reply.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
assert request('/')[0]==200
status=json.loads(request('/api/status')[1]);assert status['count']==60678 and status['draft']['cards']=={}
rows=json.loads(request('/api/search?q=93192181')[1]);assert rows['total']==1 and rows['rows'][0]['spid']==93192181
detail=json.loads(request('/api/detail?spid=93192181')[1]);assert detail['row']['height']==188 and len(detail['fields'])==43
assert request('/api/stage',dict(spid=93192181))[0]==403
assert request('/api/stage')[0]==403
assert request('/api/status',headers={'Host':'evil.example'})[0]==403
assert request('/api/stage',dict(spid=93192181,row_hash=detail['row_hash'],revision=0,changes={'height':999}),{'X-FO3-Admin':'1'})[0]==400
assert json.loads(request('/api/status')[1])['draft']['cards']=={}
print(json.dumps(dict(status='PASS',checks=9,production_draft_unchanged=True,publish_readiness=status['publish_readiness']),ensure_ascii=True))
