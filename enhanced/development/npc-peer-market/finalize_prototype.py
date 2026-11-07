from pathlib import Path
p=Path('D:/fifaol3/npc-peer-market/predict_value.py');s=p.read_text('utf-8-sig')
s=s.replace("self.model=json.loads(Path(path or ROOT/'value-model.json').read_text('utf8'))", "self.model=json.loads(Path(path or ROOT/'value-model.json').read_text('utf8'))\n  self.references=json.loads((ROOT/'historical-reference-prices.json').read_text('utf8'))")
s=s.replace("return dict(spid=row['spid'],ovr=row['ovr'],estimated_historical_plus1_ep=self.predict(row),known_season=row['season'] in self.model['seasons'],scope='historical regional estimate; not current live EP or measured hand feel')", "estimate=self.predict(row)\n  observed=self.references.get(str(row['spid']),0)\n  return dict(spid=row['spid'],ovr=row['ovr'],estimated_historical_plus1_ep=estimate,reference_anchor_plus1_ep=observed if observed>0 else estimate,anchor_source='historical exact card' if observed>0 else 'model fallback',known_season=row['season'] in self.model['seasons'],scope='historical regional estimate; not current live EP or measured hand feel')")
p.write_text(s,'utf8')
raw=Path('D:/FO3ID/server/gamedata/fa_prices.json').read_bytes();Path('D:/fifaol3/npc-peer-market/historical-reference-prices.json').write_bytes(raw)
p=Path('D:/fifaol3/npc-peer-market/plot_value_model.py');s=p.read_text('utf-8-sig').replace("'普通年度卡'","'其它赛季'");p.write_text(s,'utf8')
