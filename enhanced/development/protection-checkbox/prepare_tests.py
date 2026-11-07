from pathlib import Path
W=Path(__file__).parent
s=Path(r'D:\fifaol3\protection-preview-fix\test_server.py').read_text('utf8')
s=s.replace("W=Path(r'D:\\fifaol3\\protection-preview-fix')", "W=Path(r'D:\\fifaol3\\protection-checkbox')")
s=s.replace("assert sum(i['itemid']==p.ITEM for i in items)==1", "assert sum(i['itemid']==p.ITEM for i in items)==0")
s=s.replace("c['ep']=10**18;c['es']=1000000", "c['ep']=10**18;c['es']=1000000;c['items']=[row for row in c.get('items',[]) if row.get('itemid') not in (1000052,1000053,1000054)]")
at=s.index("result={'status':'PASS'")
extra='''
def boosted_fresh(grade=12,mat=1,count=2):
 a,b=fresh(grade,mat);st=h._state();h.inventory_add(h.my_coach(st),1000052,count);h._save(st);return a,b
def stacked_preview(a,b,point=0,item=1000052,event=-1):
 return call(f'/player/{a}/enhance2.5/{b}/preview/{point}/{item}/{event}?protection=1')
def stacked_execute(a,b,q,point=0,item=1000052,event=-1):
 return call(f'/player/{a}/enhance2.5/{b}/{point}/{item}/{event}?'+urlencode({'protection_ack':q['protection']['version'],'protection_token':q['protection']['token']}))
for success in (True,False):
 for point in (0,1):
  a,b=boosted_fresh();before=h._state();pa=copy.deepcopy(getcard(before,a));booster=h.boost_stack(before,'1000052');before_count=booster['remains'];q=stacked_preview(a,b,point)
  raw=Path(h.STATE).read_bytes();normal=call(f'/player/{a}/enhance2.5/{b}/preview/{point}/1000052/-1');plain=call(f'/player/{a}/enhance2.5/{b}/preview/{point}/-1/-1')
  assert Path(h.STATE).read_bytes()==raw and q['result'] and q['probability']==normal['probability']>plain['probability']
  assert '黄金强化加成' in q['protection']['label'] and '均消耗1个' in q['protection']['label']
  cost=(h.player_value_price(pa['spid'],12)*2+4)//5;n=len(commits)
  with patch.object(h.random,'random',return_value=0 if success else .999999):r=stacked_execute(a,b,q,point)
  after=h._state();assert r['result'] and r['success']==success and len(commits)==n+1
  assert h.my_coach(after)['ep']==h.my_coach(before)['ep']-cost and h.boost_stack(after,'1000052')['remains']==before_count-1
  assert getcard(after,a)['grade']==12+success and getcard(after,a)['levelinfo']==pa['levelinfo']
  assert all(h.iid(card)!=b for card in after['teams'][str(slot)]['players']) and 'enhance_restore' not in after
  raw=Path(h.STATE).read_bytes();assert not stacked_execute(a,b,q,point)['result'] and Path(h.STATE).read_bytes()==raw
checks.append('Gold + independent protection: real routed chance equals native gold preview, above no-gold; point off/on, success/failure one booster/material/40%-fee/atomic save; replay zero charge')
a,b=boosted_fresh(count=1);q=stacked_preview(a,b)
with patch.object(h.random,'random',return_value=.999999):assert stacked_execute(a,b,q)['result']
assert h.boost_stack(h._state(),'1000052') is None
a,b=boosted_fresh();q=stacked_preview(a,b);st=h._state();h.boost_stack(st,'1000052')['remains']+=1;h._save(st);raw=Path(h.STATE).read_bytes()
assert not stacked_execute(a,b,q)['result'] and Path(h.STATE).read_bytes()==raw
a,b=boosted_fresh();st=h._state();h.inventory_add(h.my_coach(st),1000053,1);h._save(st);q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes()
assert not stacked_execute(a,b,q,item=1000053)['result'] and Path(h.STATE).read_bytes()==raw
a,b=fresh(12,1);raw=Path(h.STATE).read_bytes();q=stacked_preview(a,b)
assert q['result'] and q['reason']=='BOOST_ITEM_UNAVAILABLE' and q['protection']['blocked'] and 'token' not in q['protection'] and Path(h.STATE).read_bytes()==raw
checks.append('Last booster removes stack; inventory quantity/path changes invalidate quote; absent booster is nonfatal blocked read with zero spend')
a,b=boosted_fresh();q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes()
with patch.object(h,'_save',side_effect=OSError('Injected stacked atomic-save failure')):
 try:stacked_execute(a,b,q)
 except OSError:pass
 else:raise AssertionError('save failure expected')
assert Path(h.STATE).read_bytes()==raw
with patch.object(h.random,'random',return_value=.999999):assert stacked_execute(a,b,q)['result']
a,b=boosted_fresh();q=stacked_preview(a,b);n=len(commits)
with patch.object(h.random,'random',return_value=.999999),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda _:stacked_execute(a,b,q),range(2)))
assert sum(row['result'] for row in rows)==1 and len(commits)==n+1
checks.append('Stacked save failure preserves persisted assets; retry works; concurrent same quote commits once')
a,b=boosted_fresh(6,6);raw=Path(h.STATE).read_bytes();q=stacked_preview(a,b)
assert q['result'] and q['protection']['blocked'] and q['probability']==100 and Path(h.STATE).read_bytes()==raw
a,b=boosted_fresh();q=stacked_preview(a,b);raw=Path(h.STATE).read_bytes();st=h._state();pa=getcard(st,a);before_ep=h.my_coach(st)['ep'];before_count=h.boost_stack(st,'1000052')['remains']
with patch.object(h.random,'random',return_value=.999999):r=call(f'/player/{a}/enhance2.5/{b}/0/1000052/-1')
assert r['result'] and h.my_coach(h._state())['ep']==before_ep-h.enhance_cost(pa) and h.boost_stack(h._state(),'1000052')['remains']==before_count-1
assert h.grade_of(getcard(h._state(),a))==h.enhancement_failure_grade(pa)
rules=call('/info/enhancement/protection/rules');assert rules['independent_checkbox'] and not rules['boost_item_exclusive']
checks.append('Capped 100% gold combo needs no paid protection; unchecked gold retains original fee/drop/stock behavior; pseudo service removed from dropdown inventory')
'''
s=s[:at]+extra+s[at:]
(W/'test_server.py').write_text(s,encoding='utf8')
