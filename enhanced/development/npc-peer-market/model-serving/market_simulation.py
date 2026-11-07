"""Offline market with independent NPC inventory. Install last, after the stable pricing and state guards.

Only existing native client URIs are used. card_price remains the immutable pack anchor.
The clock is deliberately injectable for isolated tests; production uses real elapsed time.
"""
import copy
import hashlib
import json
import math
import re
import secrets
import time
import random
import types
import threading
import logging
from npc_exchange import NpcExchange

REFRESH_SECONDS = 900
BACKGROUND_SECONDS = 15
DISCOVERY_SECONDS = 300
RARE_DISCOVERY_LIMIT = 16
EXPIRE_SECONDS = 86400
MAX_OFFERS = 30
NPC_HOLD_SECONDS = 3600
SALE_PROBABILITIES = ((.5, .995), (.8, .92), (1., .55), (1.1, .18),
                      (1.3, .03), (1.6, .003), (2.5, .00005))
SALE_WAIT_RANGES = ((.5,300,900),(.8,900,3600),(1.,3600,14400),
                    (1.1,14400,43200),(1.3,28800,86340),
                    (1.6,43200,86340),(2.5,64800,86340))
# Whole-world ceilings, not a separate lottery for every queried SPID.
# Each opportunity has a preassigned card, grade and release time. Skipped or
# expired opportunities never accumulate into an offline catch-up jackpot.
LEGACY_RARE_TIERS = (
    {'key': 'silver', 'grades': (7, 8, 9), 'period': 86400, 'slots': 12,
     'chance': .8, 'pool': 2000},
    {'key': 'gold', 'grades': (10,), 'period': 86400, 'slots': 3,
     'chance': .75, 'pool': 1000},
    {'key': 'breakthrough', 'grades': (11, 12, 13), 'period': 7*86400, 'slots': 2,
     'chance': .5, 'pool': 500},
    {'key': 'prestige', 'grades': (14, 15, 16), 'period': 14*86400, 'slots': 1,
     'chance': .35, 'pool': 200},
    {'key': 'ultimate', 'grades': (17, 18, 19), 'period': 28*86400, 'slots': 1,
     'chance': .25, 'pool': 100},
    {'key': 'apex', 'grades': (20,), 'period': 84*86400, 'slots': 1,
     'chance': .25, 'pool': 100},
)
QUALITY_BANDS = (
    {'key':'low','min':0,'max':80,'factor':1.,'regular':(.85,.65,.45)},
    {'key':'mid','min':81,'max':86,'factor':.9,'regular':(.65,.45,.25)},
    {'key':'high','min':87,'max':90,'factor':.8,'regular':(.4,.25,.12)},
    {'key':'elite','min':91,'max':999,'factor':.7,'regular':(.2,.1,.04)},
)
# Low-quality anchors. All other quality pools receive the SAME per-SPID rate,
# discounted by their factor. No rare per-SPID query lottery exists.
LOW_SUPPLY = (
    ((11,),1,768,1.), ((12,),1,576,1.), ((13,),1,384,1.),
    ((14,),1,192,1.), ((15,),1,144,1.), ((16,),1,96,1.),
    ((17,),1,48,1.), ((18,),1,36,1.), ((19,),1,24,1.), ((20,),1,12,1.),
)
REGULAR_HIGH_CHANCES = {7: .95, 8: .85, 9: .70, 10: .55}
SUPPLY_VERSION = 3

now = time.time


def integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('integer required')
    return int(value)


def iso(stamp):
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(stamp))


class Market:
    def __init__(self, hc):
        self.h = hc
        self.reference = hc.player_value_price
        self._candidates = None
        self._known_cards = {}
        self._quality_pools = None
        self._supply_plan = None
        self._worker_lock = threading.Lock()
        self._worker_stop = threading.Event()
        self._worker = None
        self._worker_status = {'ticks': 0, 'last_tick': None, 'last_error': None, 'errors': 0}
        self.exchange = NpcExchange(self, getattr(hc, 'NPC_VALUE_MODEL_PATH', None))

    def tick(self):
        """Advance the shared world without a client request; never auto-claim EP."""
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):
                return False
            before = copy.deepcopy(st)
            self.prepare(st)
            stamp = now()
            self.settle(st, stamp)
            self.rare_stock(st, stamp)
            epoch = int(stamp // REFRESH_SECONDS)
            # Refresh recently used books. Old, abandoned books expire normally;
            # do not turn every card ever searched into permanent saved inventory.
            recent = [int(key) for key, book in st['market_simulation']['books'].items()
                      if epoch - 1 <= book['epoch'] <= epoch]
            for spid in recent:
                self.book(st, spid, stamp)
            self.featured_rows(st, stamp, limit=50)
            self.exchange.advance(st, stamp)
            changed = st != before
            if changed:
                self.h._save(st)
            return changed

    def start_background(self):
        """Start once, only after the HTTP listener and all roster hooks are ready."""
        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return False
            self._worker_stop.clear()
            self._worker = threading.Thread(target=self._run_background, name='market-world', daemon=True)
            self._worker.start()
            return True

    def stop_background(self):
        with self._worker_lock:
            self._worker_stop.set()
            worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=5)

    def _run_background(self):
        while not self._worker_stop.is_set():
            try:
                self.tick()
                self._worker_status.update(ticks=self._worker_status['ticks'] + 1,
                                           last_tick=now(), last_error=None)
            except Exception as exc:
                self._worker_status.update(errors=self._worker_status['errors'] + 1,
                                           last_error=f'{type(exc).__name__}: {exc}')
                logging.getLogger(__name__).exception('Market background tick failed; retrying next interval')
            self._worker_stop.wait(BACKGROUND_SECONDS)

    def quality(self,spid):
        rating=self.h.card_ovr(int(spid))+self.h.GRADE_BOOST[1]
        return next(b['key'] for b in QUALITY_BANDS if b['min']<=rating<=b['max'])

    def quality_pools(self):
        if self._quality_pools is None:
            pools={b['key']:[] for b in QUALITY_BANDS}
            for spid in self.candidates():pools[self.quality(spid)].append(spid)
            self._quality_pools=pools
        return self._quality_pools

    def supply_plan(self):
        if self._supply_plan is None:
            pools=self.quality_pools();base=max(1,len(pools['low']));plan=[]
            for band in QUALITY_BANDS:
                size=len(pools[band['key']])
                for grades,days,slots,chance in LOW_SUPPLY:
                    per_day=slots*chance/days*size/base*band['factor']
                    if band['key']!='low':
                        if per_day>=1:days=1
                        else:days=next((d for d in (7,14,28,84,365) if per_day*d>=.25),365)
                        slots=max(1,math.ceil(per_day*days));chance=per_day*days/slots
                    plan.append({'key':band['key']+'_'+str(grades[0]),'quality':band['key'],
                                 'grades':grades,'period':days*86400,'slots':slots,
                                 'chance':chance,'pool_size':size,'expected_per_day':per_day})
            self._supply_plan=tuple(plan)
        return self._supply_plan

    def fail(self, reason='INVALID_PARAM'):
        return self.h._json({'result': False, 'reason': reason})

    def active(self, st):
        slot = self.h._default_slot(st)
        coach = next(c for c in st['coaches'] if c['slot'] == slot)
        return coach, st['teams'][str(slot)], slot

    def has_active(self, st):
        slot=self.h._default_slot(st)
        return any(c.get('slot')==slot for c in st.get('coaches',[])) and str(slot) in st.get('teams',{})

    def valid_card(self, spid, grade=1):
        try:
            spid, grade = integer(spid), integer(grade)
            if not 1 <= grade <= self.h.MAX_GRADE or not self.h.on_market(spid):return False
            if spid not in self._known_cards:
                with self.h.closing(self.h._db()) as db:
                    self._known_cards[spid]=db.execute('SELECT 1 FROM players WHERE spid=?',(spid,)).fetchone() is not None
            return self._known_cards[spid] and self.exchange.price_store.current(spid)>0
        except (TypeError, ValueError, OverflowError):
            return False

    def quote(self, spid, grade=1, st=None):
        if not self.valid_card(spid, grade):
            raise ValueError('unknown market card or invalid grade')
        if st is None:
            st = self.h._state()
        # Current database/state price only. No valuation model or seed anchor.
        return min((2**53-1)//3, max(1, self.exchange.reference_value(int(spid),int(grade),st)))

    def prepare(self, st):
        """Lazy, one-time migration, saved with the successful operation/read transaction.

        Old offers had no owner information. Preserve them for the active manager at first
        migration only, recording that decision; never expose them to every manager.
        New managers get a random lifetime owner token, even when an old slot/id is reused.
        """
        m = st.setdefault('market_simulation', {})
        if not m:
            m.update(version=2, seed=secrets.token_hex(16), books={}, quotes={}, sales=[],
                     rare_books={}, buyers={}, created_at=now())
        m.setdefault('rare_books', {})
        m.setdefault('buyers', {})
        m.setdefault('created_at', now())
        pending_events=m.setdefault('price_events',[])
        # Only remove already committed events; never write an uncommitted
        # state transaction to the price DB from prepare()/read operations.
        m['price_events']=[e for e in pending_events if not self.exchange.price_store.applied(e['event_id'])]
        if m.get('price_store_version')!=1:
            for spid,q in m.get('quotes',{}).items():
                before=self.exchange.price_store.basis(spid)
                if before<=0:continue
                factor=min(1.6,max(.6,q.get('factor',1.)))
                basis=min(5_600_000_000_000_000,max(1.,before*factor))
                if basis!=before:
                    m['price_events'].append(dict(event_id='seed-migration:'+self.exchange.price_store.meta['seed_revision']+':'+spid,spid=int(spid),before=before,after=basis,at=now(),reason='legacy_market_movement',evidence={'legacy_factor':factor}))
                q['basis_price']=basis
                q['prior_model_pending']=q.get('pending',[]);q['pending']=[]
                q['movement']=min(math.log(1.02),q.get('movement',0.))
            m['price_store_version']=1

        if m.get('attribute_value_model_version') != 1:
            for quote in m.get('quotes', {}).values():
                quote['pending'] = []  # Old-valuation trials cannot mix with the new base.
            m['attribute_value_model_version'] = 1
        if m.get('player_price_divisor', 1) == 1:
            # Convert existing NPC quotes in place without refilling any stock.
            # Player listings and completed sale entitlements are contracts;
            # their original agreed amounts and historical cost bases survive.
            for table in ('books', 'rare_books'):
                for book in m.get(table, {}).values():
                    for row in book.get('rows', []):
                        if row.get('price') is not None:
                            row['price'] = max(1, int(row['price']) // 1000)
            for row in m.get('legacy_supply', []):
                if row.get('price') is not None:
                    row['price'] = max(1, int(row['price']) // 1000)
            m['player_price_divisor'] = 1000
        if m.get('supply_version',1)<SUPPLY_VERSION:
            # A shown quote is a contract: keep its stock/price to old expiry.
            # Hidden future slots have no quoted price and are not player commitments.
            stamp=now()
            m['legacy_supply']=[copy.deepcopy(row) for row in
                (m.get('legacy_supply',[])+[r for batch in m['rare_books'].values() for r in batch.get('rows',[])]) if row.get('price') is not None
                and row.get('count',0)>0 and stamp<row.get('_market_expires',0)]
            m['rare_books']={};m['supply_version']=SUPPLY_VERSION;m['supply_started_at']=stamp
        m.setdefault('supply_started_at',m['created_at'])
        if m.get('version', 1) < 2:
            for book in m.get('books', {}).values():
                book['rows'] = [r for r in book['rows'] if r['grade'] <= 6]
            m['version'] = 2
        coach, team, slot = self.active(st)
        owner = coach.setdefault('_market_owner', secrets.token_hex(16))
        if not m.get('legacy_migrated'):
            for offer in st.get('offers', []):
                if '_market_owner' not in offer:
                    offer.update(_market_owner=owner, _market_slot=slot, _market_legacy=True)
            m['legacy_migrated'] = True
        return m, owner, team, slot

    @staticmethod
    def unit(seed):
        return (int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], 'big') + 1) / (2**64 + 1)

    def book(self, st, spid, stamp):
        m = st['market_simulation']; key = str(int(spid)); epoch = int(stamp // REFRESH_SECONDS)
        books = m['books']; book = books.get(key)
        # Do not roll an earlier clock backwards into extra inventory.
        if book and (book['epoch'] > epoch or (book['epoch']==epoch and book.get('supply_version')==SUPPLY_VERSION)):
            return book
        upgrading=bool(book and book['epoch']==epoch)
        rows = copy.deepcopy(book['rows']) if upgrading else []
        for g in range(7 if upgrading else 1, min(10, self.h.MAX_GRADE) + 1):
            quality=self.quality(spid)
            regular=next(b['regular'] for b in QUALITY_BANDS if b['key']==quality)
            chance = dict(zip((4,5,6),regular)).get(g,0)
            if g in REGULAR_HIGH_CHANCES:
                chance=REGULAR_HIGH_CHANCES[g]*next(b['factor'] for b in QUALITY_BANDS if b['key']==quality)
            # Preserve already displayed pre-upgrade offers at their exact price.
            if any(r['spid']==int(spid) and r['grade']==g and r['count']>0
                   and r['_market_release']<=stamp<r['_market_expires']
                   for r in m.get('legacy_supply',[])):
                continue
            count = {1: 12, 2: 6, 3: 3}.get(g, 1 if self.unit(f'{m["seed"]}:{key}:{epoch}:{g}') < chance else 0)
            if count:
                rows.append({'spid': int(spid), 'expandme': 'player', 'grade': g,
                             'price': self.quote(spid, g, st), 'count': count})
        book = {'epoch': epoch, 'rows': rows, 'supply_version':SUPPLY_VERSION}; books[key] = book
        # Bound persisted per-card books without evicting any live batch (no refill exploit).
        for old in [k for k, b in books.items() if b['epoch'] < epoch - 1]:
            del books[old]
        return book

    def candidates(self):
        if self._candidates is None:
            with self.h.closing(self.h._db()) as db:
                present={s for(s,) in db.execute('SELECT spid FROM players')}
            cards = [s for s in self.h.market_spids() & present if self.exchange.price_store.current(s)>0]
            ratings = self.h.card_ovrs(cards)
            self._candidates = tuple(sorted(cards, key=lambda s: (-ratings[s], s)))
        return self._candidates

    def rare_stock(self, st, stamp):
        m = st['market_simulation']; result = []
        pools=self.quality_pools()
        for tier in self.supply_plan():
            grades = [g for g in tier['grades'] if g <= self.h.MAX_GRADE]
            if not grades:
                continue
            period = tier['period']
            key = tier['key']; batch = m['rare_books'].get(key)
            if batch is None or stamp>=batch['start']+batch['period']:
                if batch is None:
                    epoch=max(0,int((stamp-m['supply_started_at'])//period))
                    start=m['supply_started_at']+epoch*period
                else:
                    # Existing period/rows remain signed across roster updates. A
                    # changed pool/config takes effect only AFTER that period ends.
                    prior_end=batch['start']+batch['period']
                    skipped=max(0,int((stamp-prior_end)//period))
                    epoch=batch['epoch']+1+skipped;start=prior_end+skipped*period
                rows = []
                cards = pools[tier['quality']]
                if not cards:
                    continue
                for i in range(tier['slots']):
                    seed = f'{m["seed"]}:rare:{key}:{epoch}:{i}'
                    if self.unit(seed+':exists') >= tier['chance']:
                        continue
                    s = cards[min(len(cards)-1, int(self.unit(seed+':card')*len(cards)))]
                    g = grades[min(len(grades)-1, int(self.unit(seed+':grade')*len(grades)))]
                    # Nonoverlapping release slots make the total period stock explicit.
                    duration=period/tier['slots']
                    release = start + i*duration
                    expires = start + (i+1)*period/tier['slots']
                    rows.append({'spid':s, 'expandme':'player', 'grade':g,
                                 'price':None, 'count':1,
                                 '_market_quality':tier['quality'],'_market_supply_key':key,
                                 '_market_release':release, '_market_expires':expires})
                batch = {'epoch':epoch,'start':start,'period':period,
                         'slots':tier['slots'],'chance':tier['chance'],
                         'pool_size':tier['pool_size'],'rows':rows};m['rare_books'][key] = batch
            # A backwards clock never reopens a previously consumed historical batch.
            for row in batch['rows']:
                if row['count']>0 and row['_market_release']<=stamp<row['_market_expires']:
                    # A hidden future opportunity has no quoted price yet. Freeze
                    # current value only when it first becomes a visible offer.
                    if row['price'] is None:row['price']=self.quote(row['spid'],row['grade'],st)
                    result.append(row)
        for row in m.get('legacy_supply',[]):
            if row['count']>0 and row['_market_release']<=stamp<row['_market_expires']:
                result.append(row)
        return result

    @staticmethod
    def public_row(row):
        return {k:copy.deepcopy(v) for k,v in row.items() if not k.startswith('_market_')}

    def rows(self, st, spid, stamp):
        regular = [r for r in self.book(st,spid,stamp)['rows'] if r['count']>0]
        return sorted(regular + [r for r in self.rare_stock(st,stamp) if r['spid']==int(spid)] + self.exchange.listings(st,stamp,spid), key=lambda r:(r['grade'],r['price']))

    @staticmethod
    def sale_probability(ratio):
        if ratio <= SALE_PROBABILITIES[0][0]:
            return SALE_PROBABILITIES[0][1]
        for (x0,p0),(x1,p1) in zip(SALE_PROBABILITIES,SALE_PROBABILITIES[1:]):
            if ratio <= x1:
                f=(ratio-x0)/(x1-x0)
                lo=math.log(p0/(1-p0));hi=math.log(p1/(1-p1))
                return 1/(1+math.exp(-(lo+(hi-lo)*f)))
        return SALE_PROBABILITIES[-1][1]

    @staticmethod
    def wait_range(ratio):
        if ratio<=SALE_WAIT_RANGES[0][0]:return SALE_WAIT_RANGES[0][1:]
        for (x0,lo0,hi0),(x1,lo1,hi1) in zip(SALE_WAIT_RANGES,SALE_WAIT_RANGES[1:]):
            if ratio<=x1:
                f=(ratio-x0)/(x1-x0)
                return lo0+(lo1-lo0)*f,hi0+(hi1-hi0)*f
        return SALE_WAIT_RANGES[-1][1:]

    def band(self, spid, grade, st):
        q = self.quote(spid, grade, st)
        return {'lower': max(1, q // 2), 'upper': max(1, q * 5 // 2),
                'default': q, 'lowest': q, 'registrationFee': 0}

    def schedule(self, st, offer, price, stamp):
        q = self.quote(offer['spid'], offer['grade'], st)
        p = offer['_market_player']
        seed = p.setdefault('_market_sale_seed', secrets.token_hex(16))
        # A cancelled listing keeps the same 24h trial; only real expiry permits
        # another deterministic draw. Neither page refresh nor relisting resets it.
        expires=p.get('_market_trial_expires')
        if expires is None or stamp >= expires:
            p['_market_trial_round']=int(p.get('_market_trial_round',-1))+1
            p['_market_trial_expires']=stamp+EXPIRE_SECONDS
            p.pop('_market_trial_plan',None)
        u = self.unit(f'{seed}:attempt:{p["_market_trial_round"]}')
        probability=self.sale_probability(price/q)
        # Two independent, stable quantiles: whether this whole trial can sell,
        # then how quickly an interested buyer arrives. A cheap card that hits
        # the 92% trial chance clears in minutes; polling cannot redraw a miss.
        hit=u>=1-probability
        plan=p.get('_market_trial_plan')
        if plan and plan['price']==price and plan['quote']==q:
            due=plan['due']
        elif hit:
            lo,hi=self.wait_range(price/q)
            v=self.unit(f'{seed}:attempt:{p["_market_trial_round"]}:time')
            wait=lo+(hi-lo)*v
            remaining=p['_market_trial_expires']-stamp
            due=stamp+min(wait,max(0,remaining-1)) if remaining>60 else p['_market_trial_expires']
        else:due=p['_market_trial_expires']
        if hit and due<p['_market_trial_expires']:due=max(due,stamp+60)
        if p.get('_market_origin'):
            due=max(due,float(p['_market_origin'].get('at',stamp))+NPC_HOLD_SECONDS)
        p['_market_trial_plan']={'price':price,'quote':q,'due':due}
        offer.update(status='selling', price=price, issuedat=iso(p['_market_trial_expires']-EXPIRE_SECONDS),
                     completefee={'base': int(price * self.h.SALE_FEE)},
                     _market_listed=stamp, _market_due=due,
                     _market_expires=p['_market_trial_expires'], _market_quote=q,
                     _market_probability24=probability)
        offer.pop('soldat', None)

    def record(self, st, offer, stamp):
        m = st['market_simulation']; spid = str(offer['spid']); p = offer.get('_market_player', {})
        eligible = not p.get('_market_origin') and not offer.get('_market_legacy')
        entry = {'id': offer['_id'], 'spid': offer['spid'], 'grade': offer['grade'],
                 'price': offer['price'], 'at': stamp, 'eligible': eligible,
                 'ratio': offer['price'] / max(1, self.exchange.reference_value(offer['spid'], offer['grade'],st)),
                 'kind':offer.get('_market_kind','player_sale'),
                 'buyer':offer.get('_market_buyer'), 'seller':offer.get('_market_seller'),
                 'owner': offer['_market_owner']}
        m['sales'].append(entry); m['sales'] = m['sales'][-500:]
        if not eligible:
            return
        quote = m['quotes'].setdefault(spid, {'factor': 1.0, 'day': int((stamp+7*3600) // 86400), 'movement': 0.0, 'pending': []})
        day = int((stamp+7*3600) // 86400)
        if day > quote['day']:
            quote.update(day=day, movement=0.0)
        pending = quote.setdefault('pending', [])
        pending.append({'ratio': entry['ratio'], 'at': stamp, 'id':entry['id'], 'kind':entry['kind'], 'price':entry['price'], 'grade':entry['grade']})
        quote['pending'] = pending = pending[-20:]
        # A single lucky overpriced sale cannot move a quote. Require three sales whose
        # actual simulated成交 times span >=30 minutes, then consume the entire sample.
        if len(pending) < 3 or max(x['at'] for x in pending) - min(x['at'] for x in pending) < 1800:
            return
        target = sorted(x['ratio'] for x in pending)[len(pending)//2]
        before=quote.get('basis_price',self.exchange.price_store.basis(spid))
        if before<=0:return
        delta=max(-math.log(1.005),min(math.log(1.005),math.log(max(1e-12,target))*.1))
        budget=max(0.,math.log(1.02)-quote['movement']);delta=max(-budget,min(budget,delta))
        value=min(5_600_000_000_000_000,max(1.,before*math.exp(delta)))
        if value!=before:
            st['market_simulation'].setdefault('price_events',[]).append(dict(
                event_id='trade-price:'+str(entry['id']),spid=int(spid),before=before,after=value,at=stamp,
                reason='funded_trade_volume',evidence={'sales':list(pending),'median_ratio':target}))
        quote.update(basis_price=value,movement=quote['movement']+abs(math.log(value/before)),pending=[])

    def settle(self, st, stamp):
        for offer in sorted(st.get('offers', []), key=lambda o:o.get('_market_due',float('inf'))):
            if offer.get('status') != 'selling' or '_market_due' not in offer:
                continue
            if stamp >= offer['_market_due'] and offer['_market_due'] < offer['_market_expires']:
                m=st['market_simulation']; day=int((offer['_market_due']+7*3600)//86400)
                band='high' if offer['grade']>=11 else 'silver' if offer['grade']>=7 else 'regular'
                key=f'{offer["spid"]}:{band}'; demand=m['buyers'].get(key)
                if demand is None or demand['day']<day:
                    demand={'day':day,'count':0};m['buyers'][key]=demand
                limit=2 if offer['grade']>=11 else 8 if offer['grade']>=7 else 32
                if demand['count']>=limit or demand['day']>day:
                    # This trial missed the finite buyer pool; polling cannot retry it.
                    offer['_market_due']=offer['_market_expires']
                    if stamp>=offer['_market_expires']:offer['status']='expired'
                    continue
                demand['count']+=1
                offer.update(status='sold', soldat=iso(offer['_market_due']))
                self.record(st, offer, offer['_market_due'])
            elif stamp >= offer['_market_expires']:
                offer['status'] = 'expired'

    def listing(self, st):
        if not self.has_active(st):
            return {'offerexpireoffset':EXPIRE_SECONDS*1000,'boost':self.h.NO_BOOST,'offers':[]}
        coach, _, _ = self.active(st); owner = coach.get('_market_owner')
        # Private escrow/provenance must not leak into native player expansion payloads.
        offers = [{k: copy.deepcopy(v) for k, v in o.items() if not k.startswith('_market_')}
                  for o in st.get('offers', []) if o.get('_market_owner') == owner and owner]
        return {'offerexpireoffset': EXPIRE_SECONDS*1000, 'boost': self.h.NO_BOOST, 'offers': offers}

    def resources(self, st):
        return [{'uri': '/transfer/my/offer/list', 'body': self.listing(st)}] + self.h.coach_me_resources(st, self.h._default_slot(st))

    def persist(self, st, before):
        if st != before:
            self.h._save(st)

    def featured_rows(self, st, stamp, position=None, limit=34):
        """Rotate a balanced selection, independently of stock refresh/expiry."""
        pools = self.quality_pools()
        epoch = int(stamp // DISCOVERY_SECONDS)
        seed = st['market_simulation']['seed']
        limits = self.h.LINES.get(str(position).upper()) if position else None
        if limits is not None:
            with self.h.closing(self.h._db()) as db:
                positions = dict(db.execute('SELECT spid, preferredposition1 FROM players'))
        groups = []
        for band in reversed(QUALITY_BANDS):
            cards = pools[band['key']]
            if limits is not None:
                cards = [s for s in cards if positions.get(s) in limits]
            size = len(cards)
            if not size:
                continue
            offset = int(self.unit(f'{seed}:discovery:{epoch}:{band["key"]}') * size)
            step = 7919
            while math.gcd(step, size) != 1:
                step += 1
            groups.append((cards, offset, step))
        result = []
        seen = set()
        # Equal exposure across quality bands; stock availability still follows
        # the existing 1/.9/.8/.7 probabilities. No additional inventory is drawn.
        def available(group, values):
            cards, offset, step = values
            for index in range(len(cards)):
                sid = cards[(offset + index * step) % len(cards)]
                if sid in seen:
                    continue
                rows = sorted(self.book(st, sid, stamp)['rows'] + self.exchange.listings(st,stamp,sid), key=lambda r:r['price'])
                grade = (10, 9, 8, 7)[(index + group) % 4]
                row = next((r for r in rows if r['grade'] == grade and r['count'] > 0), None)
                if row:
                    seen.add(sid)
                    yield self.public_row(row)
        streams = [available(group, values) for group, values in enumerate(groups)]
        while streams:
            remaining = []
            for stream in streams:
                row = next(stream, None)
                if row is not None:
                    result.append(row)
                    remaining.append(stream)
                    if len(result) >= limit:
                        return result
            streams = remaining

        return result

    def search(self, spid, query, body):
        if not self.valid_card(spid):
            return self.h._json([])
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.h._json([])
            before = copy.deepcopy(st); self.prepare(st); stamp = now(); self.settle(st, stamp)
            result = [self.public_row(r) for r in self.rows(st,int(spid),stamp)]
            self.persist(st, before)
            return self.h._json(result)

    def top(self, position, query, body):
        if position and str(position).upper() not in self.h.LINES:
            return self.fail()
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.h._json([])
            before = copy.deepcopy(st); self.prepare(st); stamp = now(); self.settle(st, stamp)
            rare = []
            limits=self.h.LINES.get(str(position).upper()) if position else None
            for row in self.rare_stock(st,stamp):
                if limits is not None:
                    with self.h.closing(self.h._db()) as db:
                        p=db.execute('SELECT preferredposition1 FROM players WHERE spid=?',(row['spid'],)).fetchone()
                    if not p or p[0] not in limits:continue
                rare.append(self.public_row(row))
            epoch = int(stamp // DISCOVERY_SECONDS)
            seed = st['market_simulation']['seed']
            rare.sort(key=lambda r:self.unit(f'{seed}:rare-display:{epoch}:{r["spid"]}:{r["grade"]}'))
            # Long-lived rare offers remain searchable but cannot monopolize
            # the recommendation page for days. Keep every available grade represented.
            result = []
            grades = set()
            for row in rare:
                if row['grade'] not in grades:
                    result.append(row)
                    grades.add(row['grade'])
            for row in rare:
                if len(result) >= RARE_DISCOVERY_LIMIT:
                    break
                if row not in result:
                    result.append(row)
            result = result[:RARE_DISCOVERY_LIMIT]
            result.extend(self.featured_rows(st, stamp, position, limit=50-len(result)))
            self.persist(st, before)
            return self.h._json(result)

    def price(self, spid, grade, query, body):
        if not self.valid_card(spid, grade):
            return self.fail()
        with self.h.STATE_LOCK:
            return self.h._json(self.band(int(spid), int(grade), self.h._state()))

    def purchase(self, spid, grade, price, query, body):
        if not self.valid_card(spid, grade):
            return self.fail()
        try:
            spid, grade, price = integer(spid), integer(grade), integer(price)
        except (TypeError, ValueError, OverflowError):
            return self.fail()
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.fail('NOT_EXIST_OFFER')
            before = copy.deepcopy(st); _, team, slot = self.active(st)
            if len(team['players']) >= self.h.MAX_PLAYERS:
                return self.fail('Exceed plyer limit')
            self.prepare(st); stamp = now()
            row = next((r for r in self.rows(st,spid,stamp) if r['grade']==grade and r['price']==price),None)
            if not row or row['price'] != price:
                return self.fail('NOT_EXIST_OFFER')
            if self.h.coach_me(st, slot)['money']['ep'] < price:
                return self.fail('NOT_ENOUGH_EP')
            self.settle(st, stamp)
            self.exchange.human_purchase(st,row,stamp)
            self.h.add_ep(st, -price); player = self.h.add_player(team, spid, grade)
            player['_market_origin'] = {'kind':'npc','paid':price,'basis':price,'at':stamp}
            row['count'] -= 1
            self.persist(st, before)
            return self.h._json({'result': True, 'resources': self.h.coach_me_resources(st, slot)})

    def offers(self, query, body):
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.h._json(self.listing(st))
            before = copy.deepcopy(st); self.prepare(st); self.settle(st, now()); self.persist(st, before)
            return self.h._json(self.listing(st))

    def request_price(self, body):
        obj = json.loads(body or b'{}')
        if not isinstance(obj, dict):
            raise ValueError('object required')
        price = integer(obj.get('price'))
        if price <= 0:
            raise ValueError('positive price required')
        return obj, price

    def offer(self, query, body):
        try:
            req, price = self.request_price(body)
        except (TypeError, ValueError, OverflowError):
            return self.fail()
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.fail('NOT_EXIST_OFFER')
            before = copy.deepcopy(st); _, team, slot = self.active(st)
            pid = str(req.get('playerobjectid')); player = next((p for p in team['players'] if self.h.iid(p) == pid), None)
            if not player or player.get('locked') or player.get('lock') or self.h.is_starter(team, player):
                return self.fail('TRANSFERMARKET_SELECT_SELLABLE_PLAYER')
            spid, grade = player['spid'], self.h.grade_of(player)
            if not self.valid_card(spid, grade):
                return self.fail('TRANSFERMARKET_SELECT_SELLABLE_PLAYER')
            band = self.band(spid, grade, st)
            if not band['lower'] <= price <= band['upper']:
                return self.fail('TRANSFERMARKET_LOWERLIMIT')
            _, owner, _, _ = self.prepare(st)
            if sum(o.get('_market_owner') == owner for o in st.get('offers', [])) >= MAX_OFFERS:
                return self.fail('TRANSFERMARKET_MAX_REGISTERED')
            escrow = copy.deepcopy(player)
            # Keep a complete original instance in escrow. Return to reserves on cancel;
            # old formation slots may have been filled while the card was listed.
            self.h.remove_player(team, player)
            offer = {'_id': secrets.token_hex(12), 'spid': spid, 'expandme': 'player', 'grade': grade,
                     'playerobjectid': pid, '_market_player': escrow, '_market_owner': owner, '_market_slot': slot}
            stamp = now(); self.schedule(st, offer, price, stamp); self.settle(st, stamp)
            st.setdefault('offers', []).append(offer); self.persist(st, before)
            return self.h._json({'result': True, 'resources': self.resources(st)})

    def find_offer(self, st, offerid):
        coach, _, _ = self.active(st); owner = coach.get('_market_owner')
        return next((o for o in st.get('offers', []) if o['_id'] == offerid and o.get('_market_owner') == owner and owner), None)

    def cancel(self, status, offerid, query, body):
        if status not in ('selling', 'expired'):
            return self.fail()
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.fail('NOT_EXIST_OFFER')
            before = copy.deepcopy(st); self.prepare(st)
            offer = self.find_offer(st, offerid)
            if not offer or offer['status'] not in ('selling', 'expired') or not offer.get('_market_player'):
                return self.fail('NOT_EXIST_OFFER')
            _, team, _ = self.active(st)
            if len(team['players']) >= self.h.MAX_PLAYERS:
                return self.fail('Exceed plyer limit')
            self.settle(st, now())
            if offer['status'] == 'sold':
                self.persist(st, before)
                return self.fail('NOT_EXIST_OFFER')
            player = copy.deepcopy(offer['_market_player'])
            if any(self.h.iid(p) == self.h.iid(player) for p in team['players']):
                return self.fail('INVALID_PARAM')
            # Preserve the complete player, including original team2/jersey/XP/lock/provenance.
            team['players'].append(player); st['offers'].remove(offer); self.persist(st, before)
            return self.h._json({'result': True, 'resources': self.resources(st)})

    def recreate(self, offerid, query, body):
        try:
            _, price = self.request_price(body)
        except (TypeError, ValueError, OverflowError):
            return self.fail()
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.fail('NOT_EXIST_OFFER')
            before = copy.deepcopy(st); self.prepare(st); offer = self.find_offer(st, offerid)
            if not offer or offer.get('status') not in ('selling', 'expired') or not offer.get('_market_player'):
                return self.fail('NOT_EXIST_OFFER')
            band = self.band(offer['spid'], offer['grade'], st)
            if not band['lower'] <= price <= band['upper']:
                return self.fail('TRANSFERMARKET_LOWERLIMIT')
            stamp = now(); self.settle(st, stamp)
            if offer['status'] != 'expired':
                # Recreate is the client's expired-offer operation, not a free lottery reset.
                self.persist(st, before)
                return self.fail('NOT_EXIST_OFFER')
            self.schedule(st, offer, price, stamp); self.persist(st, before)
            return self.h._json({'result': True, 'resources': self.resources(st)})

    def collect(self, offerid, coupon, query, body):
        with self.h.STATE_LOCK:
            st = self.h._state()
            if not self.has_active(st):return self.fail('NOT_EXIST_OFFER')
            before = copy.deepcopy(st); self.prepare(st)
            owner = self.active(st)[0].get('_market_owner')
            eligible = [o for o in st.get('offers', []) if o.get('_market_owner') == owner and offerid in ('all', o['_id'])]
            if not eligible:
                return self.fail('NOT_EXIST_OFFER')
            self.settle(st, now())
            done = [o for o in eligible if o['status'] == 'sold']
            if not done:
                self.persist(st, before)
                return self.fail('NOT_EXIST_OFFER')
            ep = sum(self.h.sale_net(o) for o in done); self.h.add_ep(st, ep)
            st['offers'] = [o for o in st['offers'] if o not in done]; self.persist(st, before)
            return self.h._json({'result': True, 'ep': ep, 'resources': self.resources(st)})

    def basis(self, player):
        origin=player.get('_market_origin')
        if origin:
            return max(0,int(origin.get('basis',origin.get('paid',0))))
        gross=self.reference(player['spid'],self.h.grade_of(player))
        # An organic ingredient contributes its existing after-tax liquidation value.
        return self.h.sale_net({'price':gross,'completefee':{'base':int(gross*self.h.SALE_FEE)}})

    def lineage(self, players):
        origins=[p['_market_origin'] for p in players if p.get('_market_origin')]
        if not origins:return None
        return {'kind':'npc-derived','basis':sum(self.basis(p) for p in players),
                'paid':sum(self.basis(p) for p in players),
                'at':max(float(o.get('at',now())) for o in origins)}

    def fingerprint(self, players):
        return sorted([{'id':self.h.iid(p),'spid':p['spid'],'grade':self.h.grade_of(p),
                        'team2':p.get('team2'), 'locked':bool(p.get('locked') or p.get('lock')),
                        'levelinfo':copy.deepcopy(p.get('levelinfo')),
                        'origin':copy.deepcopy(p.get('_market_origin'))} for p in players],
                      key=lambda p:p['id'])

    def stage(self, original, st, *args, seed=None, add=None):
        namespace=dict(original.__globals__)
        namespace.update(_state=lambda:st,_save=lambda data:None,_json=lambda data:data)
        if seed is not None:
            namespace['random']=types.SimpleNamespace(Random=lambda *a,**k:random.Random(seed))
        if add is not None:namespace['add_player']=add
        return types.FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)(*args)

    def propose(self, body, make_props=None, scout=False, query=''):
        try:
            req=json.loads(body or b'{}')
            if not isinstance(req,dict):return self.fail()
        except (TypeError,ValueError):return self.fail()
        with self.h.STATE_LOCK:
            st=self.h._state()
            if not self.has_active(st):return self.fail('invalid playerid')
            self.prepare(st);_,team,_=self.active(st)
            sent=req.get('playerids' if scout else 'players',[])
            if not isinstance(sent,list) or (scout and any(not isinstance(x,dict) for x in sent)):
                return self.fail('invalid playerid')
            ids=[str(x.get('id')) for x in sent] if scout else [str(x) for x in sent]
            give=[p for p in team['players'] if self.h.iid(p) in ids]
            if (not 2<=len(give)<=10 or len(ids)!=len(set(ids)) or len(give)!=len(ids)
                    or any(p.get('locked') or p.get('lock') for p in give)):
                return self.fail('invalid playerid')
            owner=self.active(st)[0]['_market_owner']
            signature=sorted((self.h.iid(p),int(p['spid']),self.h.grade_of(p)) for p in give)
            kind='scout:'+str(req.get('id')) if scout else make_props.__name__
            seed=json.dumps([st['market_simulation']['seed'],owner,kind,signature],sort_keys=True)
            if scout:
                out=self.stage(self.original_trade3,st,query,body,seed=seed)
            else:
                out=self.stage(self.original_trade_proposal,st,body,make_props,seed=seed)
            if not out.get('result'):return self.h._json(out)
            trade=st.get('trade') or {}
            lineage=self.lineage(give)
            if lineage:
                budget=lineage['basis']
                for proposal in trade.get('props',[]):
                    if 'ep' in proposal:proposal['ep']=min(max(0,int(proposal['ep'])),budget)
                # Both the displayed proposal and the committed selection use these values.
                out['props']=copy.deepcopy(trade['props'])
            trade['_market_trade']={'owner':owner,'fingerprint':self.fingerprint(give),'lineage':lineage}
            self.h._save(st)
            return self.h._json(out)

    def trade_contract(self, query, body):
        try:
            req=json.loads(body or b'{}')
            if not isinstance(req,dict):return self.fail()
            selection=integer(req.get('select',req.get('selectnum',-1)))
        except (TypeError,ValueError,OverflowError):return self.fail()
        with self.h.STATE_LOCK:
            st=self.h._state()
            if not self.has_active(st):return self.fail('invalid playerid')
            _,team,_=self.active(st);trade=st.get('trade') or {}
            ids=trade.get('players') or [];give=[p for p in team['players'] if self.h.iid(p) in ids]
            props=trade.get('props') or []
            if (not 0<=selection<len(props) or len(give)!=len(ids) or not 2<=len(give)<=10
                    or any(self.h.in_squad(team,p) or p.get('locked') or p.get('lock') for p in give)):
                return self.fail('invalid playerid')
            lineage=self.lineage(give);marker=trade.get('_market_trade')
            owner=self.active(st)[0].get('_market_owner')
            if marker:
                if marker['owner']!=owner or marker['fingerprint']!=self.fingerprint(give):return self.fail('MARKET_STALE_TRADE')
            else:
                # Old proposals have no ownership/fingerprint evidence. Re-proposing
                # keeps every material intact and prevents cross-manager stale quotes.
                return self.fail('MARKET_STALE_TRADE')
            if lineage and now()<lineage['at']+NPC_HOLD_SECONDS:
                return self.fail('MARKET_NPC_HOLD')
            chosen=props[selection]
            if lineage and int(chosen.get('ep',0))>lineage['basis']:return self.fail('invalid playerid')
            def add(team,spid,grade=1):
                player=self.h.add_player(team,spid,grade)
                if lineage:
                    origin=copy.deepcopy(lineage)
                    origin['basis']=origin['paid']=max(0,origin['basis']-int(chosen.get('ep',0)))
                    player['_market_origin']=origin
                return player
            out=self.stage(self.original_trade_contract,st,query,body,add=add)
            if out.get('result'):
                self.h._save(st)
                out['resources']=self.h.coach_me_resources(st,self.h._default_slot(st))
            return self.h._json(out)

    def status(self, params):
        st=self.h._state();market=st.get('market_simulation') or {}
        return {'version':2,'supply_version':SUPPLY_VERSION,'reference_policy':'one-time model seed; persistent trade-only current prices; inherited grade multiplier',
                'npc_exchange':self.exchange.status(st,now()),
                'background':dict(self._worker_status, running=self._worker is not None and self._worker.is_alive(),
                                  interval_seconds=BACKGROUND_SECONDS),
                'refresh_seconds':REFRESH_SECONDS,'listing_lifetime_seconds':EXPIRE_SECONDS,
                'discovery_refresh_seconds':DISCOVERY_SECONDS,'rare_discovery_limit':RARE_DISCOVERY_LIMIT,
                'npc_hold_seconds':NPC_HOLD_SECONDS,'max_offers_per_manager':MAX_OFFERS,
                'probability24h':[{'ask_over_fair_value':ratio,'probability':p} for ratio,p in SALE_PROBABILITIES],
                'conditional_wait_seconds':[{'ratio':r,'min':lo,'max':hi} for r,lo,hi in SALE_WAIT_RANGES],
                'quality_basis':'card_ovr(spid)+GRADE_BOOST[1]; excludes XP/team/current grade',
                'quality_bands':copy.deepcopy(QUALITY_BANDS),
                'regular_high_chances':dict(REGULAR_HIGH_CHANCES),
                'quality_pool_sizes':{key:len(pool) for key,pool in self.quality_pools().items()},
                'rare_world_limits':copy.deepcopy(self.supply_plan()),
                'discovery':'5-minute quality-balanced +7..10 rotation; at most 16 live rare offers; search retains all stock',
                'quote_anchor_bounds':[.6,1.6],'quote_step_anchor_limit':.005,'daily_anchor_movement_limit':.02,
                'quotes':copy.deepcopy(market.get('quotes') or {}),
                'recent_sales':[{k:v for k,v in sale.items() if k!='owner'} for sale in (market.get('sales') or [])[-100:]]}


def install(hc):
    if not isinstance(hc.STATE_LOCK,type(threading.RLock())):
        raise RuntimeError('Initialize STATE_LOCK = threading.RLock() before starting the market service')
    if getattr(hc, '_market_simulation_installed', False):
        return hc.market_engine
    engine = Market(hc); engine.original_top = hc.ep_transfer_top
    engine.original_trade_proposal=hc.trade_proposal
    engine.original_trade_contract=hc.ep_trade_contract
    engine.original_trade3=hc.ep_trade3_proposal
    for fn in (engine.original_trade_proposal,engine.original_trade_contract,engine.original_trade3):
        if fn.__globals__ is not hc.__dict__ or fn.__closure__:
            raise RuntimeError('Install market before other trade adapters')
    replacements = {'ep_transfer_top': engine.top, 'ep_transfer_search': engine.search,
                    'ep_transfer_price': engine.price, 'ep_transfer_purchase': engine.purchase,
                    'ep_transfer_offer': engine.offer, 'ep_offer_collect': engine.collect}
    for name, replacement in replacements.items():
        old = getattr(hc, name)
        hc.ROUTES[:] = [(pat, replacement if fn is old else fn) for pat, fn in hc.ROUTES]
        hc.ENDPOINTS.update({key: replacement for key, fn in hc.ENDPOINTS.items() if fn is old})
        setattr(hc, name, replacement)
    hc.ENDPOINTS['/transfer/my/offer/list'] = engine.offers
    hc.ROUTES.extend([(re.compile(r'/transfer/my/offer/(selling|expired|sold)/(\w+)'), engine.cancel),
                      (re.compile(r'/transfer/offer/from/(\w+)'), engine.recreate)])
    old=hc.ep_trade_contract
    hc.ENDPOINTS.update({key:engine.trade_contract for key,fn in hc.ENDPOINTS.items() if fn is old})
    hc.ep_trade_contract=engine.trade_contract
    hc.trade_proposal=lambda body,make_props:engine.propose(body,make_props)
    hc.ep_trade3_proposal=lambda query,body:engine.propose(body,scout=True,query=query)
    hc.ENDPOINTS['/trade3/proposal']=hc.ep_trade3_proposal
    original_pair=hc.enhance_pair
    def pair(team,a,b):
        keep,gone=original_pair(team,a,b)
        if keep is not None:
            origin=engine.lineage([keep,gone])
            if origin:keep['_market_merge_snapshot']=origin
        return keep,gone
    hc.enhance_pair=pair
    original_merge = hc.merge_into
    def merge(team, keep, gone):
        # Market materials cannot launder provenance by being merged into a fresh target.
        # The target grade has already changed here. Use the before-enhancement
        # snapshot so a new grade cannot inflate an organic ingredient's basis.
        origin=keep.pop('_market_merge_snapshot',None) or engine.lineage([keep,gone])
        if origin:keep['_market_origin']=origin
        return original_merge(team, keep, gone)
    hc.merge_into = merge
    original_owned=hc.owned_team
    def owned(raw):
        team=original_owned(raw)
        team['players']=[{k:v for k,v in p.items() if not k.startswith('_market_')} for p in team['players']]
        return team
    hc.owned_team=owned
    hc.market_reference_price = engine.reference
    hc.market_quote_price = engine.quote
    import admin
    admin.READ_ONLY.add('market_status')
    admin.API['market_status']=engine.status
    hc.market_engine = engine
    hc._market_simulation_installed = True
    return engine
