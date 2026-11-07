"""Fulfil the user's explicit +20 roster grant through the live local admin API.

Preserves existing cards and XI. Reuses owned +20 copies and journals each step;
an ambiguous POST is reconciled by owned instance IDs before any retry.
"""
import datetime,json,pathlib,urllib.request
R=pathlib.Path(__file__).resolve().parent;O=R/'grant20';O.mkdir(exist_ok=True);S=pathlib.Path('D:/FO3ID/server')
def write(p,v):
    temp=p.with_suffix(p.suffix+'.next');temp.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(p)
def api(name,body=None):
    headers={'X-FO3-Lang':'zh'}
    if body is not None:headers.update({'Content-Type':'application/json','X-FO3-Admin':'1'})
    req=urllib.request.Request('http://127.0.0.1:8088/api/'+name,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=20) as r:result=json.load(r)
    if 'error' in result:raise RuntimeError(result['error'])
    return result
def main():
    models=json.loads((S/'gamedata/player-imports.json').read_text('utf8'))['models'];assert len(models)==19
    summary=api('summary');assert summary['coach']['name']=='ggmu' and summary['admin_target']['slot']==0
    target=summary['admin_target'];ledger_path=O/'journal.json'
    if ledger_path.exists():
        ledger=json.loads(ledger_path.read_text('utf8'));assert ledger['target']==target
    else:
        current=(S/'gamedata/state.json').read_bytes();(O/'operation-before-state.json').write_bytes(current)
        ledger=dict(operation='user-models-grade20-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),authorization='User explicitly requested these newly adapted players at +20 in their roster',target=target,coach='ggmu',requested_spids=[m['spid'] for m in models],selected={},actions=[])
        write(ledger_path,ledger)
    def bound():
        current=api('summary')
        if current['admin_target']!=target or current['coach']['name']!='ggmu':raise RuntimeError('Manager changed; remaining grants stopped')
    for model in models:
        spid=model['spid'];bound();owned=api('players')['players'];matches=[p for p in owned if p['spid']==spid and p['grade']==20]
        selected=ledger['selected'].get(str(spid));choice=next((p for p in matches if selected and p['id']==selected['id']),None)
        if choice is None and matches:choice=next((p for p in matches if not p['team2']),matches[0])
        if choice is None:
            before_ids={p['id'] for p in owned};bound();write(ledger_path,ledger)
            try:
                result=api('player_add',dict(spid=spid,grade=20));newid=result['id']
            except Exception:
                # Never blindly retry an API that has no native idempotency key.
                bound();now=api('players')['players'];new=[p for p in now if p['id'] not in before_ids and p['spid']==spid and p['grade']==20]
                if len(new)!=1:raise
                newid=new[0]['id']
            ledger['actions'].append(dict(action='created',spid=spid,id=newid,grade=20));write(ledger_path,ledger)
            choice=next(p for p in api('players')['players'] if p['id']==newid)
        if choice['team2']:
            bound();api('player_team',dict(id=choice['id'],team='first'));ledger['actions'].append(dict(action='moved_to_first_team',spid=spid,id=choice['id']));write(ledger_path,ledger)
        ledger['selected'][str(spid)]=dict(id=choice['id'],spid=spid,playerid=model['playerid'],name=model['name'],grade=20);write(ledger_path,ledger)
    bound();after=(S/'gamedata/state.json').read_bytes();(O/'operation-after-state.json').write_bytes(after);before=json.loads((O/'operation-before-state.json').read_bytes());after=json.loads(after)
    oldteam=before['teams']['0'];newteam=after['teams']['0'];iid=lambda p:str(p.get('_id') or p['spid']);oldcards={iid(p):p for p in oldteam['players']};newcards={iid(p):p for p in newteam['players']};created={a['id'] for a in ledger['actions'] if a['action']=='created'}
    assert created==set(newcards)-set(oldcards) and all(newcards[k]==v for k,v in oldcards.items()),'Existing card mutation or unexpected concurrent inventory change; retained for audit'
    assert newteam['squad']==oldteam['squad'],'Formation changed during grant; retained for audit'
    for p in ledger['selected'].values():assert newcards[p['id']]['spid']==p['spid'] and newcards[p['id']]['grade']==20 and not newcards[p['id']].get('team2')
    coach_before=next(c for c in before['coaches'] if c['slot']==0);coach_after=next(c for c in after['coaches'] if c['slot']==0)
    assert coach_before==coach_after,'Concurrent manager progress changed; not restored'
    result=dict(status='USER_REQUESTED_MODEL20_GRANT_PASS',coach='ggmu',target=target,models=len(models),new_instances=len(created),reused_plus20=len(models)-len(created),before_count=len(oldcards),after_count=len(newcards),existing_cards_unchanged=True,coaches_equal=True,formation_unchanged=True,all_selected_in_first_team=True,starting_XI_changed=False,state_written_by_authorized_admin_api=True,source_files_changed=False,selected=list(ledger['selected'].values()),actions=ledger['actions'])
    write(O/'result.json',result)
    lines=['# ggmu 新球员 +20 发放记录','','使用正式本地管理接口发放；保留所有旧卡、经验、强化、余额及当前首发。','',f'新增 {len(created)} 张，复用已有 +20 {len(models)-len(created)} 张，共 {len(models)} 位，均在一线队名单。','','| 球员 | SPID | 强化 | 处理 |','|---|---:|---:|---|']
    for p in result['selected']:lines.append(f"| {p['name']} | {p['spid']} | +20 | {'新增' if p['id'] in created else '复用已有卡'} |")
    (O/'发放记录.md').write_text('\n'.join(lines)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k not in ['selected','actions']},ensure_ascii=True))
if __name__=='__main__':main()
