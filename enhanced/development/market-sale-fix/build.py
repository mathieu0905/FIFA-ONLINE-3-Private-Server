"""Build minimal source delta against current official server; no formal writes."""
from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
p=S/'market_simulation.py';source=p.read_text('utf8');s=source
def replace(old,new):
 global s
 assert s.count(old)==1,(old,s.count(old))
 s=s.replace(old,new)
replace('    def sale_probability(ratio):\n', '    def sale_probability(ratio):\n        if ratio <= 1.:return 1.\n')
replace('    def wait_range(ratio):\n', '''    def wait_range(ratio):
        # Fair/discounted listings have bounded demand, independent of the lottery.
        if ratio <= .5:return (60,180)
        if ratio <= .8:
            f=(ratio-.5)/.3;return (60+120*f,180+420*f)
        if ratio <= 1.:
            f=(ratio-.8)/.2;return (180+420*f,600+1200*f)
''')
replace("        if plan and plan['price']==price and plan['quote']==q:","        if plan and plan.get('policy')==2 and plan['price']==price and plan['quote']==q:")
replace("if remaining>60 else p['_market_trial_expires']", "if remaining>0 else p['_market_trial_expires']")
replace("        if hit and due<p['_market_trial_expires']:due=max(due,stamp+60)","        if hit and due<p['_market_trial_expires']:due=max(stamp,min(p['_market_trial_expires']-1,max(due,stamp+60)))")
replace("p['_market_trial_plan']={'price':price,'quote':q,'due':due}","p['_market_trial_plan']={'policy':2,'price':price,'quote':q,'due':due}")
replace("                     _market_probability24=probability)","                     _market_probability24=probability, _market_sale_policy=2,\n                     _market_guaranteed=price<=q)")
replace('''            if stamp >= offer['_market_due'] and offer['_market_due'] < offer['_market_expires']:''','''            # Adopt only still-live contracts. Never revive an expired or sold card.
            if (offer.get('_market_sale_policy')!=2 and offer.get('_market_player')
                    and stamp < offer['_market_expires']):
                # Freeze the original quoted basis, not a newly moved market price.
                # schedule normally uses the current quote; old contracts are eligible
                # for the guarantee only when their price is still reasonable now.
                listed=offer.get('_market_listed',stamp);fee=copy.deepcopy(offer['completefee'])
                prior_due=offer['_market_due'];prior_expires=offer['_market_expires']
                self.schedule(st,offer,offer['price'],stamp)
                offer['completefee']=fee
                offer['_market_listed']=listed
                if offer['_market_guaranteed']:
                    _,hi=self.wait_range(offer['price']/offer['_market_quote'])
                    origin=offer['_market_player'].get('_market_origin',{})
                    hold=float(origin.get('at',stamp))+NPC_HOLD_SECONDS if origin else stamp
                    offer['_market_due']=max(hold,min(offer['_market_due'],max(stamp,listed+hi)))
                if prior_due < prior_expires:offer['_market_due']=min(prior_due,offer['_market_due'])
                offer['_market_player']['_market_trial_plan']['due']=offer['_market_due']
            if stamp >= offer['_market_due'] and offer['_market_due'] < offer['_market_expires']:''')
replace("                if demand['count']>=limit or demand['day']>day:","                if not offer.get('_market_guaranteed') and (demand['count']>=limit or demand['day']>day):")
replace("        return {'offerexpireoffset': EXPIRE_SECONDS*1000, 'boost': self.h.NO_BOOST, 'offers': offers}","        for offer in offers:\n            if offer.get('status')=='selling':offer['status']='waiting'\n        return {'offerexpireoffset': EXPIRE_SECONDS*1000, 'boost': self.h.NO_BOOST, 'offers': offers}")
replace("        if status not in ('selling', 'expired'):","        if status not in ('selling', 'waiting', 'expired'):")
replace("            if offer['status'] != 'expired':\n                # Recreate is the client's expired-offer operation, not a free lottery reset.","            if offer['status'] == 'sold':\n                # Settlement wins a race with repricing; preserve the earned claim.\n")
replace("            self.schedule(st, offer, price, stamp); self.persist(st, before)","            if offer['status']=='expired' or price!=offer['price']:\n                self.schedule(st, offer, price, stamp)\n            self.persist(st, before)")
replace("r'/transfer/my/offer/(selling|expired|sold)/(\\w+)'", "r'/transfer/my/offer/(selling|waiting|expired|sold)/(\\w+)'")
replace("'probability':p} for ratio,p in SALE_PROBABILITIES]", "'probability':(1. if ratio<=1. else p)} for ratio,p in SALE_PROBABILITIES]")
replace("'conditional_wait_seconds':[{'ratio':r,'min':lo,'max':hi} for r,lo,hi in SALE_WAIT_RANGES]", "'conditional_wait_seconds':[{'ratio':r,'min':self.wait_range(r)[0],'max':self.wait_range(r)[1]} for r,lo,hi in SALE_WAIT_RANGES]")
replace("'npc_hold_seconds':NPC_HOLD_SECONDS,'max_offers_per_manager':MAX_OFFERS,", "'npc_hold_seconds':NPC_HOLD_SECONDS,'max_offers_per_manager':MAX_OFFERS,\n                'player_sale_policy':2,'native_offer_status':'waiting','reprice_while_selling':True,\n                'guaranteed_sale':{'maximum_ask_over_quote':1.,'maximum_wait_seconds':1800,'daily_buyer_cap':False,'npc_origin_hold_preserved':True},")
# Fix documentation that described the old lottery-only cheap sale path.
s=s.replace('A cheap card that hits\n        # the 92% trial chance clears in minutes;', 'A fair or discounted card\n        # has guaranteed demand;')
s=s.replace('''                # Freeze the original quoted basis, not a newly moved market price.
                # schedule normally uses the current quote; old contracts are eligible
                # for the guarantee only when their price is still reasonable now.''','''                # Old contracts gain the guarantee only at a still-reasonable price;
                # their agreed gross amount, card and fee remain unchanged.''')
compile(s,str(p),'exec');(W/'market_simulation.py').write_text(s,'utf8')
(W/'baseline.json').write_text(json.dumps({'market_simulation.py':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2),'utf8')
print('Built current-source market delta')
