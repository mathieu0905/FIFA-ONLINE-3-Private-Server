"""Seal latest parent and verify/install under one exclusive publication window."""
from pathlib import Path
import subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));import deploy as d
assert d.read(R/'test-results.json')['status']=='PASS'
with d.locks(d.S):
    d.prepare()
    subprocess.run([str(d.S/'.venv/Scripts/python.exe'),'-B',str(R/'test_install.py')],check=True)
    # The imported cutover sees this process's lock ownership and retains both
    # locks from metadata sealing through stop/install/readiness.
    import cutover
