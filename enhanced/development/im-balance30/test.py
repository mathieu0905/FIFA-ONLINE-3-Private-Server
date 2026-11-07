"""Validate calibration independently against current official identities and all positions."""
import json,sqlite3,sys
from pathlib import Path
from build import R,S,FIELDS,weights,sha,save

def main():
    out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path'])
    report=json.loads((out/'report.json').read_text('utf8'));changes=json.loads((out/'changes.json').read_text('utf8'))
    for name,value in report['outputs'].items():assert sha(out/name)==value
    source=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);source.row_factory=sqlite3.Row
    ws=weights();cases=[]
    for change in changes:
        before,after=change['before_row'],change['after_row'];sid=change['spid'];shift=change['shift']
        if '--installed' in sys.argv:assert dict(source.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==after
        else:assert dict(source.execute('SELECT * FROM players WHERE spid=?',(sid,)).fetchone())==before
        assert sid//1000000==84
        assert set(after)==set(before) and all(v==after[k] for k,v in before.items() if k not in FIELDS)
        assert shift>=0 and all(after[k]-before[k]==shift for k in FIELDS)
        for w in ws:
            assert sum((after[k]-before[k])*v for k,v in w.items())==100*shift
        anchors=[dict(p) for p in source.execute('SELECT * FROM players WHERE playerid=? AND spid>=1000000 AND spid/1000000!=84',(before['playerid'],))]
        w=ws[before['preferredposition1']]
        best=max(sum(p[k]*v for k,v in w.items()) for p in anchors)
        actual=sum(after[k]*v for k,v in w.items())
        assert actual-best>=3000
        # Exact full-squad grade10 vs grade20 contribution: +24 vs +44;
        # grade sets +7 vs +17, feature full IM +5 vs no feature.
        assert actual-best+100*(24-44+7-17+5)>=500
        if shift:assert actual-best<3100
        cases.append(dict(spid=sid,positions=28,all33_differences_preserved=True,nonstats_exact=True,
                          base_margin=(actual-best)/100,full_im10_vs_other20_margin=(actual-best)/100-25))
    assert len(changes)==len(source.execute('SELECT spid FROM players WHERE spid/1000000=84').fetchall())
    result=dict(status='PASS',cards=len(cases),position_checks=28*len(cases),stat_checks=33*len(cases),
        min_base_margin=min(p['base_margin'] for p in cases),min_full_im10_vs_other20_margin=min(p['full_im10_vs_other20_margin'] for p in cases),
        installed_checked='--installed' in sys.argv,outputs=report['outputs'],cases=cases,native_verified=False,
        builder_sha256=sha(R/'build.py'))
    save(R/('installed-tests.json' if '--installed' in sys.argv else 'tests.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
if __name__=='__main__':main()
