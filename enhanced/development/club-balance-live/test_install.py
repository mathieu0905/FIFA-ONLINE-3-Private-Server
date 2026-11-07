"""Exercise refusal, shared-lock ownership and CAS rollback without formal writes."""
from pathlib import Path
import json
import ast
import tempfile
import sys
sys.dont_write_bytecode=True
import install
import prepare


def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='transaction-',dir=prepare.ROOT) as temporary:
        root=Path(temporary).resolve()
        assert root.is_relative_to(prepare.ROOT.resolve())
        target=root/'file';target.write_bytes(b'before');backup=root/'backup';backup.write_bytes(b'before')
        e=dict(target=target,source=b'ours',before=install.digest(b'before'),after=install.digest(b'ours'),backup=backup)
        install.cas(e);assert target.read_bytes()==b'ours'
        assert install.rollback([e])==[] and target.read_bytes()==b'before'
        checks.append('Own committed file rolls back to the exact fresh backup')
        target.write_bytes(b'concurrent')
        try:install.cas(e)
        except RuntimeError:pass
        else:raise AssertionError('CAS accepted target drift')
        assert target.read_bytes()==b'concurrent'
        checks.append('CAS rejects concurrent target changes without overwriting them')
        target.write_bytes(b'later-legal-change')
        assert install.rollback([e])==[str(target)] and target.read_bytes()==b'later-legal-change'
        checks.append('Rollback preserves a later legitimate change')
        new=root/'new'
        created=dict(target=new,source=b'new',before=None,after=install.digest(b'new'),backup=root/'unused')
        install.cas(created);assert new.exists()
        assert install.rollback([created])==[] and not new.exists()
        checks.append('Own newly created immutable file is removed on rollback')
        other=root/'.fo3-publish.lock';other.write_bytes(b'other-owner')
        try:
            with install.locks(root):raise AssertionError('Lock conflict accepted')
        except FileExistsError:pass
        assert other.read_bytes()==b'other-owner' and not (root/'.shop-release.lock').exists()
        other.unlink()
        with install.locks(root):
            assert (root/'.shop-release.lock').exists() and (root/'.fo3-publish.lock').exists()
        assert not (root/'.shop-release.lock').exists() and not (root/'.fo3-publish.lock').exists()
        checks.append('Locks acquire in shop/publish order, preserve another owner and release only own locks')
    old_idle,old_write=install.idle,prepare.write
    captured=[]
    try:
        install.idle=lambda:False
        prepare.write=lambda path,obj:captured.append((path,obj))
        install.main()
    finally:install.idle,prepare.write=old_idle,old_write
    assert len(captured)==1 and captured[0][1]['status']=='DEFERRED_GAME_RUNNING' and captured[0][1]['formal_files_written'] is False
    checks.append('A running game exits before locking, planning, stopping services or any formal write')
    tree=ast.parse((prepare.ROOT/'install.py').read_text('utf8'))
    main_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    for locked in (n for n in ast.walk(main_node) if isinstance(n,ast.With)):
        assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='finish' for n in ast.walk(locked))
    checks.append('Startup business watcher verification runs after releasing publication locks')
    result=dict(status='PASS',case_count=len(checks),checks=checks,installer_sha256=prepare.sha(prepare.ROOT/'install.py'),formal_files_written=False,services_action=False)
    prepare.write(prepare.ROOT/'transaction-tests.json',result)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
