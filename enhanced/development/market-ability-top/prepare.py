from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');s=(S/'market_simulation.py').read_text('utf8')
baseline=hashlib.sha256((S/'market_simulation.py').read_bytes()).hexdigest()
a=s.index('    def top(self, position, query, body):');b=s.index('    def price(',a)
s=s[:a]+'''    def listing_ability(self,row,ratings):
        grade=min(self.h.MAX_GRADE,max(0,int(row['grade'])))
        level=max(1,min(getattr(self.h,'PLAYER_MAX_LEVEL',23),int((row.get('levelinfo') or {}).get('level',1))))
        level_bonus=getattr(self.h,'player_level_boost',lambda lv:lv-1)(level)
        return ratings[int(row['spid'])]+self.h.GRADE_BOOST[grade]+level_bonus

    def top(self, position, query, body):
        if position and str(position).upper() not in self.h.LINES:
            return self.fail()
        with self.h.STATE_LOCK:
            st=self.h._state()
            if not self.has_active(st):return self.h._json([])
            before=copy.deepcopy(st);self.prepare(st);stamp=now();self.settle(st,stamp)
            market=st['market_simulation']
            # Only an empty market needs an initial supply batch. Ordinary
            # recommendation requests never create or refill additional books.
            if not market['books']:self.featured_rows(st,stamp,limit=50)
            epoch=int(stamp//REFRESH_SECONDS)
            rows=[r for book in market['books'].values() if book['epoch']>=epoch for r in book['rows']]
            rows+=self.rare_stock(st,stamp)+self.exchange.listings(st,stamp)
            eligible=set(self.candidates());limits=self.h.LINES.get(str(position).upper()) if position else None
            positions=None
            if limits is not None:
                with self.h.closing(self.h._db()) as db:positions=dict(db.execute('SELECT spid,preferredposition1 FROM players'))
            variants={}
            for row in rows:
                spid=int(row['spid']);grade=int(row['grade'])
                if spid not in eligible or not 1<=grade<=self.h.MAX_GRADE or row.get('count',0)<=0:continue
                if row.get('price') is None or row['price']<=0:continue
                if row.get('_market_release',float('-inf'))>stamp or row.get('_market_expires',float('inf'))<=stamp:continue
                if positions is not None and positions.get(spid) not in limits:continue
                level=max(1,min(getattr(self.h,'PLAYER_MAX_LEVEL',23),int((row.get('levelinfo') or {}).get('level',1))))
                key=(spid,grade,level)
                # Recommend the cheapest available offer for an identical
                # card/grade/level; retain that offer's actual stock count.
                if key not in variants or row['price']<variants[key]['price']:variants[key]=row
            ratings=self.h.card_ovrs({int(r['spid']) for r in variants.values()})
            ordered=sorted(variants.values(),key=lambda r:(-self.listing_ability(r,ratings),-ratings[int(r['spid'])],-int(r['grade']),r['price'],int(r['spid'])))
            result=[self.public_row(r) for r in ordered[:50]]
            self.persist(st,before)
            return self.h._json(result)

''' +s[b:]
s=s.replace('SPOTLIGHT_TIERS','SUPPLY_FOCUS_TIERS').replace('SPOTLIGHT_LIMIT = sum(q for _,q in SUPPLY_FOCUS_TIERS)\n','')
s=s.replace("'spotlight_seasons':dict(SUPPLY_FOCUS_TIERS),'discovery':'5-minute rotating top-season slots first; quality-balanced remainder; existing stock and rare quotas retained'","'supply_focus_seasons':dict(SUPPLY_FOCUS_TIERS),'top_policy':'actual listed ability descending; no season quotas','discovery':'5-minute supply-focus rotation; recommendation ranks current offers by base OVR plus grade and listed-level bonuses'")
compile(s,'market_simulation.py','exec');(P/'market_simulation.py').write_bytes(s.encode('utf8'));(P/'baseline.json').write_text(json.dumps({'market_simulation.py':baseline},indent=2),'utf8');print('Prepared ability-ranked top; supply rotation and moments availability retained')
