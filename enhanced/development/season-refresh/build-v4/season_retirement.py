"""Retire duplicate ICON season12 from new acquisition; preserve issued pack rights."""
import functools,types

RETIRED_SEASON=12
LEGACY_ISSUED_POOLS=frozenset((97300012,98100020))

def install(h):
    if getattr(h,'_season12_retirement_installed',False):return
    old_market=h.market_spids
    @functools.lru_cache(maxsize=None)
    def market_spids():return frozenset(s for s in old_market() if s//1000000!=RETIRED_SEASON)
    h.market_spids=market_spids
    old_pool=h.pack_pool
    def pool(i):
        rows=old_pool(i)
        # The 47 already-owned retired adventure packs retain their signed odds.
        return rows if i in LEGACY_ISSUED_POOLS else [(s,w) for s,w in rows if s//1000000!=RETIRED_SEASON]
    h.pack_pool=pool
    for name in ('pack_price','trade_pool','trade3_pool'):
        fn=getattr(h,name,None)
        if hasattr(fn,'cache_clear'):fn.cache_clear()
    engine=h.market_engine
    old_candidates,old_book,old_rare=engine.candidates,engine.book,engine.rare_stock
    def candidates(self):return tuple(s for s in old_candidates() if s//1000000!=RETIRED_SEASON)
    def book(self,state,spid,stamp):
        if int(spid)//1000000==RETIRED_SEASON:return {'epoch':int(stamp//900),'rows':[]}
        return old_book(state,spid,stamp)
    def rare(self,state,stamp):return [r for r in old_rare(state,stamp) if int(r['spid'])//1000000!=RETIRED_SEASON]
    engine.candidates=types.MethodType(candidates,engine);engine.book=types.MethodType(book,engine);engine.rare_stock=types.MethodType(rare,engine)
    import admin
    old_search,old_shop=admin.API['search'],admin.API['shop']
    def search(p):
        out=old_search(p);return {**out,'rows':[r for r in out.get('rows',[]) if int(r['spid'])//1000000!=RETIRED_SEASON]}
    def shop(p):
        out=old_shop(p);return {**out,'seasons':[r for r in out.get('seasons',[]) if r['code']!=RETIRED_SEASON]}
    admin.API['search']=search;admin.search=search;admin.API['shop']=shop
    for lang,table in admin.I18N.items():table['e_retired_season']='该赛季已退场，请选择其它赛季。' if lang=='zh' else 'This season has been retired.'
    for name in ('player_add','bag_send'):
        previous=admin.API[name]
        def guarded(p,_old=previous):
            try:blocked=bool(p.get('spid') and int(p['spid'])//1000000==RETIRED_SEASON) or bool(p.get('itemid') and int(p['itemid']) in LEGACY_ISSUED_POOLS)
            except (ValueError,TypeError):blocked=False
            if blocked:raise admin.AdminError('e_retired_season')
            return _old(p)
        admin.API[name]=functools.wraps(previous)(guarded)
    h._season12_retirement_installed=True
