"""Prepare generation-aware helpers from the actual installed implementation."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def main():
 source=(S/'fair_value_store.py').read_text('utf8');start=source.index('def install_catalogue(');end=source.index('\nclass FairLayer:',start);source=source[:start]+(P/'generation_functions.py').read_text('utf8')+'\n'+source[end:]
 compile(source,'fair_value_store.py','exec');(P/'fair_value_store.py').write_text(source,'utf8')
 source=(S/'fair_value_model.py').read_text('utf8');old="effective_score=score,weakfoot=p['weakfootabilitytypecode']";new="effective_score=score,valuation_score_kind='attribute_proxy_not_measured_playability',historical_preference_factor=name,weakfoot=p['weakfootabilitytypecode']";assert source.count(old)==1;source=source.replace(old,new);compile(source,'fair_value_model.py','exec');(P/'fair_value_model.py').write_text(source,'utf8')
 (P/'runtime-baseline.json').write_text(json.dumps({str(S/n):hashlib.sha256((S/n).read_bytes()).hexdigest() for n in ['fair_value_model.py','fair_value_store.py']},indent=2)+'\n','utf8')
 print('Generation runtime adapters ready; no official files written')
if __name__=='__main__':main()
