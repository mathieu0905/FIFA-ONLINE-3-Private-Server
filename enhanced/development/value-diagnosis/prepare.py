"""Build source deltas only. Never writes to the official installation."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')


def prepare():
    expected = json.loads((HERE / 'source-baseline.json').read_text('utf8'))
    for rel, sha in expected.items():
        if hashlib.sha256((SERVER / rel).read_bytes()).hexdigest() != sha:
            raise RuntimeError('Source changed; rebase this delta: ' + rel)
    code = (SERVER / 'npc_exchange.py').read_text('utf8')
    code = code.replace('from market_price_store import MarketPriceStore, MAX_PRICE',
                        'from market_price_store import MarketPriceStore, MAX_PRICE\nfrom ability_value import AbilityPriceBook')
    code = code.replace('        self._profiles={}', '        self._profiles={}\n        self.ability_prices=AbilityPriceBook(market.h)')
    start = code.index('    def base_value(')
    end = code.index('    def world(', start)
    code = code[:start] + '''    def base_value(self,spid,st=None):
        initial=self.price_store.initial(spid)
        if initial<=0:return 0
        basis=self.price_store.basis(spid)
        if st is not None:
            basis=st.get('market_simulation',{}).get('quotes',{}).get(str(int(spid)),{}).get('basis_price',basis)
        return self.ability_prices.current(spid,basis,initial)

    def reference_value(self,spid,grade,st=None):
        base=self.base_value(spid,st)
        if base<=0:return 0
        return self.ability_prices.graded(base,grade)

''' + code[end:]
    code = code.replace("model='one_time_neural_seed_then_trade_driven_database'",
                        "model='role_ability_value_v1_with_bounded_trade_movement'")
    needle = "            out.update(spid=spid,grade=grade,initial_price=store.initial(spid),current_price=store.current(spid),value=hc.player_value_price(spid,grade))"
    assert code.count(needle) == 1
    code = code.replace(needle, '''            out.update(spid=spid,grade=grade,initial_price=store.initial(spid),
                legacy_current_basis=store.current(spid),current_price=engine.exchange.base_value(spid),
                value=hc.player_value_price(spid,grade),ability=engine.exchange.ability_prices.explain(spid),
                market_factor=engine.exchange.ability_prices.policy.market_factor(store.basis(spid),store.initial(spid)))''')
    code = code.replace("        out['runtime_model_loaded']=bool(out['runtime_model_modules'])",
                        "        out['runtime_model_loaded']=bool(out['runtime_model_modules'])\n        out['active_valuation_policy']='ability-value-v1'\n        out['historical_basis_unit']='immutable old seed EP; not the active displayed price'")
    compile(code, 'npc_exchange.py', 'exec')
    output = HERE / 'payload'
    (output / 'gamedata').mkdir(parents=True, exist_ok=True)
    payload = {'npc_exchange.py': code.encode('utf8'),
               'ability_value.py': (HERE / 'ability_value.py').read_bytes(),
               'gamedata/ability_value_policy.json': (HERE / 'ability_value_policy.json').read_bytes()}
    market = (SERVER / 'market_simulation.py').read_text('utf8')
    old = 'one-time model seed; persistent trade-only current prices; inherited grade multiplier'
    assert market.count(old) == 1
    market = market.replace(old, 'positive role-ability fair price; bounded historical demand; existing enhancement investment curve')
    payload['market_simulation.py'] = market.encode('utf8')
    for rel, data in payload.items():
        (output / rel).write_bytes(data)
    digest = {rel: hashlib.sha256(data).hexdigest() for rel, data in payload.items()}
    (HERE / 'payload-hashes.json').write_text(json.dumps(digest, indent=2), 'utf8')
    print(json.dumps(dict(status='BUILT_NOT_ACTIVATED', payload=digest)))
    return payload


if __name__ == '__main__':
    prepare()
