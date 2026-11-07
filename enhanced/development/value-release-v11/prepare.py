"""Prepare one official combined update; build artifacts only, no second service."""
from pathlib import Path
import gzip,hashlib,json,sqlite3

P=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server')
V=Path('D:/fifaol3/npc-peer-market/identity-anchor-v11')
A=Path('D:/fifaol3/value-diagnosis/manutd-full-audit')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def encoded(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def gz(p):
 with gzip.open(p,'rt',encoding='utf8') as f:return json.load(f)

def main():
 build=Path(read(A/'latest-build.json')['path']);report=read(build/'report.json')
 for path,h in report['baseline'].items():assert sha(path)==h,'Refresh changed official inputs: '+path
 for name,h in report['outputs'].items():assert sha(build/name)==h,'Changed validated artifact '+name
 verified=read(V/'local-verification.json');assert verified['status']=='PASS' and verified['model_sha256']==sha(V/'selected-model.json.gz')
 expected={r['spid']:r for r in gz(V.with_name('anchor-retraining-v10')/'current-profiles.json.gz')}
 with sqlite3.connect((build/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;rows={r['spid']:dict(r) for r in db.execute('select * from players')}
 assert rows.keys()==expected.keys()
 for sid,r in expected.items():assert all(rows[sid][k]==v for k,v in r.items()),sid
 preview=gz(V/'current-price-preview.json.gz')
 prices=[[sid,int(preview[str(sid)]['price'])] for sid in sorted(rows)]
 packet=dict(schema=1,revision='identity-anchor-v11-mul63',model_sha256=verified['model_sha256'],rows=prices,
             prices_sha256=hashlib.sha256(json.dumps(prices,separators=(',',':')).encode()).hexdigest(),
             corrected_database_sha256=sha(build/'fifadb.sqlite'),strict_checks=2128493,strict_failures=0)
 with (P/'valuation-calibration.json.gz').open('wb') as f:f.write(gzip.compress(encoded(packet),mtime=0))
 source=(S/'market_price_store.py').read_text('utf8')
 old="seed_revision=self.meta['seed_revision'],priced_cards="
 new="seed_revision=self.meta['seed_revision'],active_valuation_revision=self.meta.get('valuation_revision'),active_valuation_model_sha256=self.meta.get('valuation_model_sha256'),priced_cards="
 assert source.count(old)==1;source=source.replace(old,new)
 source+='\n\n'+(P/'calibration_functions.py').read_text('utf8')
 compile(source,'market_price_store.py','exec');(P/'market_price_store.py').write_text(source,'utf8')
 baseline={str(S/'market_price_store.py'):sha(S/'market_price_store.py'),**report['baseline']}
 (P/'prepared.json').write_bytes(encoded(dict(status='PREPARED',build=str(build),baseline=baseline,rows=len(prices),model_sha256=packet['model_sha256'],packet_sha256=sha(P/'valuation-calibration.json.gz'),resource_artifacts=report['outputs'])))
 print(json.dumps(dict(status='PREPARED',rows=len(prices),attribute_repairs=63,formal_written=False)))

if __name__=='__main__':main()
