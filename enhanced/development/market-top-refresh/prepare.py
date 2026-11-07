from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
files=['market_simulation.py','legend_moments_bulk_npc.py','gamedata/custom_rosters.json']
baseline={f:hashlib.sha256((S/f).read_bytes()).hexdigest() for f in files}
m=(S/'market_simulation.py').read_text('utf8')
m=m.replace('DISCOVERY_SECONDS = 300','DISCOVERY_SECONDS = 300\nSPOTLIGHT_TIERS = ((84,4),(30,3),(93,4),(19,3),(48,2))\nSPOTLIGHT_LIMIT = sum(q for _,q in SPOTLIGHT_TIERS)')
needle='''        result = []
        seen = set()
        # Equal exposure across quality bands; stock availability still follows'''
insert='''        result = []
        seen = set()
        # Each prominent season gets rotating slots. Advance by its quota so
        # consecutive pages do not repeat the same random slice indefinitely.
        # This reads the existing epoch book; it never rerolls or refills stock.
        all_cards=[sid for values in groups for sid in values[0]]
        for season,quota in SPOTLIGHT_TIERS:
            cards=[sid for sid in all_cards if sid//1000000==season]
            if not cards:continue
            offset=(int(self.unit(f'{seed}:spotlight-origin:{season}')*len(cards))+epoch*quota)%len(cards)
            shown=0
            for index in range(len(cards)):
                sid=cards[(offset+index)%len(cards)]
                if sid in seen:continue
                rows=self.book(st,sid,stamp)['rows']+self.exchange.listings(st,stamp,sid)
                start=(epoch+index+season)%4;grades=(10,9,8,7);preference=grades[start:]+grades[:start]+(6,5,4,3,2,1)
                row=None
                for grade in preference:
                    available=[r for r in rows if r['grade']==grade and r['count']>0]
                    if available:row=min(available,key=lambda r:r['price']);break
                if row is None:continue
                result.append(self.public_row(row));seen.add(sid);shown+=1
                if len(result)>=limit:return result
                if shown>=quota:break
        # Equal exposure across quality bands; stock availability still follows'''
assert m.count(needle)==1;m=m.replace(needle,insert)
needle='''            result.extend(self.featured_rows(st, stamp, position, limit=50-len(result)))
            self.persist(st, before)'''
insert='''            featured=self.featured_rows(st, stamp, position, limit=50-len(result))
            lead=min(SPOTLIGHT_LIMIT,len(featured))
            result=featured[:lead]+result+featured[lead:]
            self.persist(st, before)'''
assert needle in m;m=m.replace(needle,insert)
m=m.replace("'discovery':'5-minute quality-balanced +7..10 rotation; at most 16 live rare offers; search retains all stock'","'spotlight_seasons':dict(SPOTLIGHT_TIERS),'discovery':'5-minute rotating top-season slots first; quality-balanced remainder; existing stock and rare quotas retained'")
l=(S/'legend_moments_bulk_npc.py').read_text('utf8')
l=l.replace('Exclude the explicitly registered season-84 cards from NPC minting.','Allow registered season-84 NPC supply; keep explicitly retired cards excluded.')
old="""    excluded = frozenset(int(r['fo3_spid']) for r in registry['cards'] if int(r['fo3_spid']) // 1000000 == 84)
    excluded |= frozenset(int(r['fo3_spid']) for r in registry.get('retired_cards', []) if r.get('npc_excluded'))
    if not excluded or any(not engine.valid_card(spid, 1) for spid in excluded):
        raise ValueError('Registered moment card missing from the runtime database')"""
new="""    moments=frozenset(int(r['fo3_spid']) for r in registry['cards'] if int(r['fo3_spid'])//1000000==84)
    excluded=frozenset(int(r['fo3_spid']) for r in registry.get('retired_cards',[]) if r.get('npc_excluded'))
    if not moments or any(not engine.valid_card(spid,1) for spid in moments):
        raise ValueError('Registered moment card missing or unpriced in runtime database')"""
assert old in l;l=l.replace(old,new)
r=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));changed=[]
for card in r['cards']:
 if card['fo3_spid']//1000000==84:card['npc_supply']=True;changed.append(card['fo3_spid'])
for season in r['seasons']:
 if season['id']==84:season['npc_supply']=True
for name,text in [('market_simulation.py',m),('legend_moments_bulk_npc.py',l)]:compile(text,name,'exec');(P/name).write_bytes(text.encode('utf8'))
(P/'custom_rosters.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8')
(P/'baseline.json').write_text(json.dumps(baseline,indent=2),'utf8');print(json.dumps(dict(moment_cards_enabled=len(changed),spotlight_slots=16),ensure_ascii=False))
