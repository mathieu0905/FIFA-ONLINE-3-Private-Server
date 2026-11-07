"""Small temporary I/O tests; no second game/server environment is created."""
from pathlib import Path
import json,os,sys,tempfile
sys.dont_write_bytecode=True
import build,install

def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='club-history-io-') as td:
        root=Path(td)
        # A conflict on the second lock releases only the first lock acquired here.
        lockdir=root/'locks';lockdir.mkdir()
        other=lockdir/'.fo3-publish.lock';other.write_bytes(b'other owner')
        try:
            with install.locks(lockdir):raise AssertionError('Unexpected lock acquisition')
        except FileExistsError:pass
        assert other.read_bytes()==b'other owner' and not (lockdir/'.shop-release.lock').exists()
        checks.append('Conflicting lock preserved; own earlier lock released')

        def scenario(name,fail=False,later=False):
            s=root/name;s.mkdir();(s/'patches').mkdir()
            (s/'gamedata').mkdir();(s/'gamedata/fifadb.sqlite').write_bytes(b'synthetic-db')
            (root/'data').mkdir(exist_ok=True);(root/'data/data_0.big').write_bytes(b'synthetic-big')
            parent=s/'parent.py';parent.write_bytes(b'parent')
            first=s/'first.bin';first.write_bytes(b'old-first')
            second=s/'new.bin'
            gate=s/install.SELF;gate.parent.mkdir(exist_ok=True)
            # Verification intentionally fails after simulating another legal writer.
            helper=("from pathlib import Path\n"
                    "def preflight(server,client):\n"+
                    ("    (Path(server)/'first.bin').write_bytes(b'later-legal-writer')\n" if later else '')+
                    ("    raise RuntimeError('simulated verification failure')\n" if fail else "    return {'status':'PASS'}\n")).encode()
            entries=[]
            for rel,body in [('first.bin',b'new-first'),('new.bin',b'created'),(install.SELF,helper)]:
                target=s/rel
                entries.append(dict(root='server',relative=rel,target=target,source=body,
                    before=build.sha(target) if target.exists() else None,after=install.digest(body)))
            p=dict(server=s,client=root,entries=entries,revision='revision-'+name,parent='parent.py',parent_hash=build.sha(parent))
            # commit reports hashes for launch metadata as well; provide tiny files.
            for rel in [install.MANIFEST,install.RECEIPT,'play-local.bat']:(s/rel).write_bytes(b'metadata')
            return s,first,second,p

        s,a,b,p=scenario('success');r=install.commit(p)
        assert a.read_bytes()==b'new-first' and b.read_bytes()==b'created' and r['status']=='INSTALLED_CLUB_HISTORY'
        checks.append('Commit writes only declared files and creates backups')
        s,a,b,p=scenario('failure')
        try:install.commit(p,fail_after=2)
        except RuntimeError as exc:assert 'INJECTED' in str(exc)
        else:raise AssertionError('Injected failure was not raised')
        assert a.read_bytes()==b'old-first' and not b.exists()
        checks.append('Partial-write failure rolls back original and new files')
        s,a,b,p=scenario('later-change',fail=True,later=True)
        try:install.commit(p)
        except RuntimeError:pass
        else:raise AssertionError('Verification failure was not raised')
        assert a.read_bytes()==b'later-legal-writer' and not b.exists()
        checks.append('Rollback retains a later legal writer instead of overwriting it')
        s,a,b,p=scenario('before-drift');a.write_bytes(b'new-user-baseline')
        try:install.commit(p)
        except RuntimeError as exc:assert 'Concurrent' in str(exc)
        else:raise AssertionError('Baseline drift was not detected')
        assert a.read_bytes()==b'new-user-baseline' and not b.exists()
        checks.append('Baseline drift rejected before any payload write')

        # Execute the real new guard against a tiny synthetic manifest, then
        # corrupt one payload. This exercises hashes, receipt and parent policy.
        s=root/'guard';c=root/'client';(s/'patches').mkdir(parents=True);(s/'gamedata').mkdir();(c/'data').mkdir(parents=True)
        files={'gamedata/fifadb.sqlite':b'synthetic-db','play-local.bat':b'synthetic-launch',install.SELF:(build.HERE/'preflight.py').read_bytes()}
        for rel,body in files.items():(s/rel).write_bytes(body)
        (c/'data/data_0.big').write_bytes(b'synthetic-big')
        guards=[dict(root='server',relative=rel,sha256=build.sha(s/rel)) for rel in files]
        guards.append(dict(root='client',relative='data/data_0.big',sha256=build.sha(c/'data/data_0.big')))
        manifest=dict(schema=1,revision='synthetic-guard',client=str(c),state_shop_replaced=False,guards=guards,composition=dict(receipt_policies=[]))
        (s/install.MANIFEST).write_bytes(install.encoded(manifest))
        (s/install.RECEIPT).write_bytes(install.encoded(dict(status='INSTALLED_CLUB_HISTORY',revision='synthetic-guard',manifest_sha256=build.sha(s/install.MANIFEST))))
        gate=build.load(s/install.SELF,'history_real_guard_fixture')
        assert gate.preflight(s,c)['status']=='CLUB_HISTORY_PREFLIGHT_PASS'
        composed=gate.compose_manifest(s,c)
        assert len(composed['guards'])==len(guards)+2
        (s/'gamedata/fifadb.sqlite').write_bytes(b'tampered-db')
        try:gate.preflight(s,c)
        except RuntimeError as exc:assert 'Installed file differs' in str(exc)
        else:raise AssertionError('Tampered DB was not rejected')
        checks.append('Real new preflight accepts sealed files, composes ancestry and rejects changed DB')
    result=dict(status='PASS',checks=checks,formal_files_written=False)
    build.write(build.HERE/'install-test-results.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
