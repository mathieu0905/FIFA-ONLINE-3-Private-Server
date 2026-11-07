"""Allow registered season-84 NPC supply; keep explicitly retired cards excluded."""
from pathlib import Path
import json
import types


def install(hc):
    engine = hc.market_engine
    if getattr(engine, '_legend_moments_bulk_npc_exclusion', False):
        return engine
    registry = json.loads((Path(hc.HERE) / 'gamedata/custom_rosters.json').read_text('utf-8'))
    moments=frozenset(int(r['fo3_spid']) for r in registry['cards'] if int(r['fo3_spid'])//1000000==84)
    excluded=frozenset(int(r['fo3_spid']) for r in registry.get('retired_cards',[]) if r.get('npc_excluded'))
    if not moments or any(not engine.valid_card(spid,1) for spid in moments):
        raise ValueError('Registered moment card missing or unpriced in runtime database')
    if engine._quality_pools is not None or engine._supply_plan is not None:
        raise RuntimeError('Install the moments boundary before market caches populate')
    old_candidates, old_book, old_rare = engine.candidates, engine.book, engine.rare_stock

    def candidates(self):
        return tuple(s for s in old_candidates() if s not in excluded)

    def book(self, state, spid, stamp):
        if int(spid) in excluded:
            return {'epoch': int(stamp // 900), 'rows': []}
        return old_book(state, spid, stamp)

    def rare_stock(self, state, stamp):
        return [r for r in old_rare(state, stamp) if int(r['spid']) not in excluded]

    engine.candidates = types.MethodType(candidates, engine)
    engine.book = types.MethodType(book, engine)
    engine.rare_stock = types.MethodType(rare_stock, engine)
    engine._legend_moments_bulk_npc_exclusion = excluded
    return engine
