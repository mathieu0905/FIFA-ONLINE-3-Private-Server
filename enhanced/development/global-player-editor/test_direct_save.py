"""Synthetic orchestration checks; no production DB, server, or client writes."""
from pathlib import Path
import importlib.util,json,tempfile,threading,time,types
ROOT=Path(__file__).resolve().parent/'pending-direct-save'
spec=importlib.util.spec_from_file_location('direct_save_test',ROOT/'player_database.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
passed=[]
with tempfile.TemporaryDirectory(prefix='fo3-save-') as temp:
    work=Path(temp);d=p.Database.__new__(p.Database);d.lock=threading.RLock();d.work=work;d.db=work/'db';d.client=work/'client';(d.client/'data').mkdir(parents=True);d.db.write_bytes(b'database');(d.client/'data/data_0.big').write_bytes(b'client')
    state=dict(revision=2,cards={'123':dict(spid=123,changes={'height':190})});d.draft=lambda:state
    d.building=False;calls=[];p.module=lambda *a:types.SimpleNamespace(game_closed=lambda:calls.append('game_closed'))
    d.queue=lambda request:calls.append(('queue',request)) or request
    d.publish=lambda request:calls.append(('publish',request)) or request
    d.save(dict(revision=2));assert calls[-1]==('queue',dict(revision=2,auto_apply=True));passed.append('one-click auto queue')
    try:d.save(dict(revision=1))
    except ValueError:passed.append('stale revision rejected')
    else:raise AssertionError()
    d.building=True
    try:d.save(dict(revision=2))
    except ValueError:passed.append('duplicate busy save rejected')
    else:raise AssertionError()
    d.building=False
    candidate=work/'candidate';candidate.mkdir();m=dict(changes=list(state['cards'].values()),source_hashes=dict(database=p.sha(d.db),client=p.sha(d.client/'data/data_0.big')))
    p.write(candidate/'manifest.json',m);p.write(work/'jobs/reuse.json',dict(status='built',candidate=str(candidate),id='reuse',manifest_sha256='exact'))
    d.save(dict(revision=2));assert calls[-1]==('publish',dict(id='reuse',manifest_sha256='exact'));passed.append('reuse exact existing build without recompression')
    d.db.write_bytes(b'changed');d.save(dict(revision=2));assert calls[-1][0]=='queue';passed.append('changed source rebuilds')
    (work/'jobs/reuse.json').unlink()
    def stage(request):
        state['revision']+=1;calls.append('stage');return dict(draft=state)
    d.stage=stage;d.save(dict(revision=2,changes={'height':191}));assert calls[-1]==('queue',dict(revision=3,auto_apply=True));passed.append('edit stages and auto-applies in one request')
print(json.dumps(dict(status='PASS',checks=passed),ensure_ascii=True))
