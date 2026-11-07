"""Replay existing price/market business contracts with the new model/helpers."""
from pathlib import Path
import importlib.util,json,sys
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');V=Path('D:/fifaol3/value-redesign-v12')
sys.path[:0]=[str(P),str(S),str(V)]
def main():
 out=Path(json.loads((P/'latest-build.json').read_text('utf8'))['path']);source=(V/'test_engine.py').read_text('utf8')
 source=source.replace("config=json.loads((P/'model.json').read_text('utf8'))","config=json.loads(Path("+repr(str(out/'model.json'))+").read_text('utf8'))")
 source=source.replace("(P/'market_simulation.py').read_text('utf8')","Path("+repr(str(S/'market_simulation.py'))+").read_text('utf8')")
 source=source.replace("assert fs.install_catalogue(price,catpath,mp,source)['applied'];", "assert bootstrap.install_catalogue(price,catpath,mp,source)['applied'];",1)
 spec=importlib.util.spec_from_file_location('v13_bootstrap_fixture_only',S/'fair_value_store.py');bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)
 scope={'__name__':'_v13_runtime_contract','__file__':str(P/'test_runtime.py'),'bootstrap':bootstrap};exec(compile(source,'v13_real_business_contracts','exec'),scope);scope['main']()
if __name__=='__main__':main()
