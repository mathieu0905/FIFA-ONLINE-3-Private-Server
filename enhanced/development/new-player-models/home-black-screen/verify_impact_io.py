import os,pathlib,tempfile
import install_bellingham_impact as m
import install_names_route as tx
import install_native_roster as n
import inspect
assert inspect.getsource(n.stage)==inspect.getsource(m.stage)
with tempfile.TemporaryDirectory() as folder:
    p=pathlib.Path(folder);a=p/'source';b=p/'target'
    a.write_bytes(bytes(range(256))*1000);b.write_bytes(b'old')
    q=m.stage(b,a);assert b.read_bytes()==b'old';os.replace(q,b)
    assert tx.sha(a)==tx.sha(b)
    print(tx.test_commit())
print('WinPS5 stream staging PASS')
