"""Reparse retained evidence; retain explicitly reviewed legacy DOB discrepancies."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,os
import wiki_careers as w
APPROVED={165239:('Samir Nasri','1987-06-26'),169588:('Jonny Evans','1988-01-03'),173608:('Joselu','1990-03-27'),210930:('Carles Gil','1992-11-22'),227174:('Matty Cash','1997-08-07'),230977:('Miguel Almirón','1994-02-10'),231447:('Donyell Malen','1999-01-19'),233419:('Raphinha','1996-12-14'),233866:('Odsonne Édouard','1998-01-16'),241159:('Marc Guéhi','2000-07-13'),39943:('Park Ji-sung','1981-03-30')}
def main():
 counts=Counter();reviewed=[];issues=[]
 for path in w.ROOT.glob('*.json'):
  if not path.stem.isdigit():continue
  before=path.read_bytes();r=json.loads(before)
  if not r.get('raw_file'):counts[r['status']]+=1;continue
  raw=gzip.decompress(Path(r['raw_file']).read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
  dob,career,name=w.parse(raw);r.update(source_dob=dob,career=career,source_name=w.clean(name),parser_sha256=hashlib.sha256(Path(w.__file__).read_bytes()).hexdigest())
  r['status']='OK' if dob==r['expected_dob'] and career else 'DOB_MISMATCH' if dob and dob!=r['expected_dob'] else 'NO_VERIFIED_INFOBOX'
  pid=r['playerid']
  if r['status']=='DOB_MISMATCH' and pid in APPROVED and APPROVED[pid][1]==dob and career:
   r['status']='OK';r['identity_review']=dict(player=APPROVED[pid][0],basis='Reviewed exact existing EA identity and named football subject; source/game DOB disagreement documented without selecting a preferred birthdate',installed_dob=r['expected_dob'],source_dob=dob,attributes_changed=False);reviewed.append(dict(playerid=pid,**r['identity_review']))
  if path.read_bytes()!=before:issues.append(dict(playerid=pid,status='CONCURRENT_SOURCE_RETAINED'));continue
  temporary=path.with_suffix('.review.tmp');w.base.write(temporary,r);os.replace(temporary,path);counts[r['status']]+=1
 report=dict(status='EVIDENCE_REPARSED',outcomes=dict(counts),reviewed_dob_discrepancies=reviewed,concurrent_sources_retained=issues,formal_files_written=False)
 w.base.write(w.P/'source-review.json',report);print(json.dumps({k:report[k] for k in ('status','outcomes','formal_files_written')}))
if __name__=='__main__':main()
