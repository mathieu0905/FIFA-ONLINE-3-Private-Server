"""Adapt exact current business functions, without touching official files."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def replace(source,old,new):
 if source.count(old)!=1:raise ValueError('Runtime source changed; inspect adapter: '+old[:90])
 return source.replace(old,new)
def main():
 original={n:(S/n).read_bytes() for n in ['market_price_store.py','market_simulation.py','npc_exchange.py']}
 source=original['market_price_store.py'].decode('utf8').replace('\r\n','\n')
 marker="  if not all(math.isfinite(p) and 1<=p<=MAX_PRICE for p in self._prices.values()):raise ValueError('Invalid current market price')"
 source=replace(source,marker,marker+"\n  self.fair=None\n  if self.meta.get('fair_revision'):\n   from fair_value_store import FairLayer\n   self.fair=FairLayer(self)")
 source=replace(source,' def basis(self,spid):\n'," def basis(self,spid):\n  if self.fair is not None:return self.fair.reference(spid)\n")
 source=replace(source,' def flush(self,events):\n'," def flush(self,events):\n  if self.fair is not None:return self.fair.flush(events)\n")
 start=source.index(' def status(self):');end=source.index('\n def close(self)',start)
 status=source[start:end].replace('  return dict(','  result=dict(',1)
 status+="\n  if self.fair is not None:result.update(mode='bounded_same_player_curve',runtime_model_loaded=True,active_valuation_revision=self.meta['fair_revision'],active_valuation_model_sha256=self.meta['fair_model_sha256'],attribute_profile_sha256=self.meta['fair_profile_sha256'],market_factor_scope='same player across all seasons',market_factor_bounds=self.fair.model['market_factor_bounds'],profile_error=self.fair.last_profile_error)\n  return result"
 source=source[:start]+status+source[end:]
 (P/'market_price_store.py').write_text(source,'utf8')
 source=original['npc_exchange.py'].decode('utf8').replace('\r\n','\n')
 source=replace(source,'    def base_value(self,spid,st=None):\n',"    def base_value(self,spid,st=None):\n        if self.price_store.fair is not None:return self.price_store.fair.reference(spid,st)\n")
 source=replace(source,'    def reference_value(self,spid,grade,st=None):\n',"    def reference_value(self,spid,grade,st=None):\n        if self.price_store.fair is not None:return self.price_store.fair.reference(spid,st,int(grade),self.market.h.GRADE_BOOST)\n")
 source=replace(source,"model='one_time_neural_seed_then_trade_driven_database'","model='bounded_same_player_curve' if self.price_store.fair is not None else 'one_time_neural_seed_then_trade_driven_database'")
 source=replace(source,"('npc_attribute_value','expanded_value_model')","('npc_attribute_value','expanded_value_model','fair_value_model','fair_value_store')")
 source=replace(source,'    hc.market_reference_price=hc.player_value_price',"    hc.market_reference_price=hc.player_value_price\n    if engine.exchange.price_store.fair is not None and hasattr(hc,'PROGRESSION20'):\n        hc.PROGRESSION20['value_model']=dict(kind='fair_strength_curve',market_base='profile-bound fair value',enhancement='same bounded curve at actual grade ability boost',rounding='round economics then add integer ability floor',manufacturing_expected_cost='diagnostic only; not single-card market price')")
 (P/'npc_exchange.py').write_text(source,'utf8')
 source=original['market_simulation.py'].decode('utf8').replace('\r\n','\n')
 source=replace(source,"        m.setdefault('rare_books', {})", "        if self.exchange.price_store.fair is not None:self.exchange.price_store.fair.prepare_state(st)\n        m.setdefault('rare_books', {})")
 marker="        if not eligible:\n            return\n        quote = m['quotes'].setdefault(spid,"
 source=replace(source,marker,"        if not eligible:\n            return\n        if self.exchange.price_store.fair is not None:\n            self.exchange.price_store.fair.stage_trade(st,entry,stamp)\n            return\n        quote = m['quotes'].setdefault(spid,")
 (P/'market_simulation.py').write_text(source,'utf8')
 baseline={str(S/n):hashlib.sha256(body).hexdigest() for n,body in original.items()}
 (P/'runtime-baseline.json').write_text(json.dumps(baseline,indent=2)+'\n','utf8')
 for name in original:compile((P/name).read_text('utf8'),name,'exec')
 print('Runtime adapters compiled; no official files written')
if __name__=='__main__':main()
