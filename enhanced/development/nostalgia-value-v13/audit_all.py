"""Re-run established full-value properties against the corrected working database."""
from pathlib import Path
import importlib.util,json,sys
P=Path(__file__).resolve().parent;V=Path('D:/fifaol3/value-redesign-v12')
sys.path.insert(0,str(P));sys.path.append(str(V))
def main():
 out=Path(json.loads((P/'latest-build.json').read_text('utf8'))['path'])
 source=(V/'audit_catalogue.py').read_text('utf8')
 source=source.replace("P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')","P=Path("+repr(str(out))+ ");S=Path('D:/FO3ID/server')")
 source=source.replace("database=S/'gamedata/fifadb.sqlite'","database=P/'fifadb.sqlite'")
 source=source.replace('cat=m.build_catalogue(database,config);','cat=m.build_catalogue(database,config);cat[\'expected_previous_revision\']=config[\'previous_revision\'];')
 scope={'__file__':str(P/'audit_all.py'),'__name__':'_v13_full_audit'};exec(compile(source,'v13_full_roster_properties','exec'),scope);scope['main']()
 source=(V/'audit_grades.py').read_text('utf8').replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(out))+')')
 scope={'__file__':str(P/'audit_all.py'),'__name__':'_v13_all_grades'};exec(compile(source,'v13_actual_grade_properties','exec'),scope);scope['main']()
 # Refresh artifact hashes after reproducibly regenerating the same catalogue.
 report=json.loads((out/'report.json').read_text('utf8'));import hashlib
 report['outputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='report.json'};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
if __name__=='__main__':main()
