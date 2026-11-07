"""Tiny byte fixtures for release ordering/CAS; no duplicate game environment."""
from contextlib import contextmanager
from pathlib import Path
import json
import sys
import tempfile
import types
sys.dont_write_bytecode=True
import install as d


def main():
    cases=[]
    original={name:getattr(d,name) for name in ('S','C','closed','game_running','check_inputs','locks','fresh_parent','payloads','transact')}
    original_cas=d.base.atomic_cas
    old_stop,old_start,old_hot=d.base.stop,d.base.start,d.base.hot_status
    with tempfile.TemporaryDirectory(dir=d.R,prefix='release-io-') as temp:
        root=Path(temp)
        try:
            d.game_running=lambda:True
            d.check_inputs=lambda:(_ for _ in ()).throw(AssertionError('Inputs accessed after game deferral'))
            d.main()
            assert not list(root.iterdir())
            cases.append('game_running_defers_before_locks_and_any_formal_write')
            d.game_running=original['game_running'];d.closed=lambda:None
            # Fault beginning, middle and end of the real 42-payload loop.
            for position in (1,21,42):
                fixture=root/('fault-'+str(position));(fixture/'server').mkdir(parents=True);(fixture/'client').mkdir()
                d.S,d.C=fixture/'server',fixture/'client'
                files={('server','byte-'+str(i)+'.txt'):('new'+str(i)).encode() for i in range(42)}
                first=('server','byte-0.txt');d.target(first).write_bytes(b'original')
                parent=dict(validator=types.SimpleNamespace(table=lambda rows:{first:{}}),composition={'guards':[]})
                counter=[0]
                def inject(path,before,after):
                    counter[0]+=1
                    if counter[0]==position:raise OSError('Injected output failure')
                    return original_cas(path,before,after)
                d.base.atomic_cas=inject
                try:d.transact(parent,files,'io-regression')
                except OSError:pass
                else:raise AssertionError('Injected release failure accepted')
                assert d.target(first).read_bytes()==b'original'
                assert all(not d.target(key).exists() for key in files if key!=first)
                cases.append('42_payload_rollback_at_'+str(position))
            d.base.atomic_cas=original_cas
            # Rollback may restore only its own after-image.
            p=d.S/'later.txt';p.write_bytes(b'later legal progress')
            try:d.restore_files([(('server','later.txt'),b'old',b'our version')])
            except RuntimeError:pass
            else:raise AssertionError('Later write overwritten')
            assert p.read_bytes()==b'later legal progress'
            cases.append('rollback_preserves_later_writer')
            # A failed/deferred protected stop must not lead to transact/start.
            fixture=root/'stop-failure';(fixture/'server/docs').mkdir(parents=True);(fixture/'client').mkdir()
            d.S,d.C=fixture/'server',fixture/'client';(d.S/d.DOC).write_bytes(b'ledger')
            d.check_inputs=lambda:None
            @contextmanager
            def fake_lock():yield
            d.locks=fake_lock
            d.fresh_parent=lambda:{};d.payloads=lambda:{}
            d.base.hot_status=lambda:{'revision':'unchanged'}
            d.base.stop=lambda:(_ for _ in ()).throw(RuntimeError('Protected stop refused'))
            d.base.start=lambda:(_ for _ in ()).throw(AssertionError('Duplicate start after refused stop'))
            d.transact=lambda *a:(_ for _ in ()).throw(AssertionError('Write after refused stop'))
            try:d.main()
            except RuntimeError as error:assert str(error)=='Protected stop refused'
            else:raise AssertionError('Stop failure ignored')
            cases.append('protected_stop_failure_aborts_without_write_or_duplicate_start')
        finally:
            for name,value in original.items():setattr(d,name,value)
            d.base.atomic_cas=original_cas;d.base.stop=old_stop;d.base.start=old_start;d.base.hot_status=old_hot
    result=dict(status='PASS',case_count=len(cases),cases=cases,formal_files_written=False,services_touched=False)
    (d.R/'transaction-tests.json').write_bytes(d.encoded(result));print(json.dumps(result))


if __name__=='__main__':main()
