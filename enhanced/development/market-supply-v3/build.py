from pathlib import Path
p=Path('D:/fifaol3/market-supply-v3/market_simulation.py')
s=p.read_text('utf-8')
a=s.index('LOW_SUPPLY = (');b=s.index('\nnow =',a)
s=s[:a]+'''LOW_SUPPLY = (
    ((11,),1,768,1.), ((12,),1,576,1.), ((13,),1,384,1.),
    ((14,),1,192,1.), ((15,),1,144,1.), ((16,),1,96,1.),
    ((17,),1,48,1.), ((18,),1,36,1.), ((19,),1,24,1.), ((20,),1,12,1.),
)
REGULAR_HIGH_CHANCES = {7: .95, 8: .85, 9: .70, 10: .55}
SUPPLY_VERSION = 3
''' +s[b:]
s=s.replace("if m.get('supply_version',1)<2:","if m.get('supply_version',1)<SUPPLY_VERSION:")
s=s.replace("m['legacy_supply']=[copy.deepcopy(row) for batch in m['rare_books'].values()\n                for row in batch.get('rows',[])","m['legacy_supply']=[copy.deepcopy(row) for row in\n                (m.get('legacy_supply',[])+[r for batch in m['rare_books'].values() for r in batch.get('rows',[])])")
s=s.replace("m['rare_books']={};m['supply_version']=2;m['supply_started_at']=stamp", "m['rare_books']={};m['supply_version']=SUPPLY_VERSION;m['supply_started_at']=stamp")
s=s.replace('range(1, min(6, self.h.MAX_GRADE) + 1)', 'range(1, min(10, self.h.MAX_GRADE) + 1)')
s=s.replace("chance = dict(zip((4,5,6),regular)).get(g,0)","chance = dict(zip((4,5,6),regular)).get(g,0)\n            if g in REGULAR_HIGH_CHANCES:\n                chance=REGULAR_HIGH_CHANCES[g]*next(b['factor'] for b in QUALITY_BANDS if b['key']==quality)\n            # Preserve already displayed pre-upgrade offers at their exact price.\n            if any(r['spid']==int(spid) and r['grade']==g and r['count']>0\n                   and r['_market_release']<=stamp<r['_market_expires']\n                   for r in m.get('legacy_supply',[])):\n                continue")
s=s.replace("release = start + i*duration + self.unit(seed+':release')*(duration-visible)","release = start + i*duration")
a=s.index('            for row in old:\n',s.index('    def top('))
s=s[:a]+'''            # Rotate across the entire eligible roster, rather than repeatedly
            # showing only the same highest-rated +1 cards. Stock is shared with
            # exact-SPID searches and remains consumed for this refresh epoch.
            cards=self.candidates()
            epoch=int(stamp//REFRESH_SECONDS)
            offset=int(self.unit(f'{st["market_simulation"]["seed"]}:featured:{epoch}')*len(cards)) if cards else 0
            featured=[]
            for i in range(min(160,len(cards))):
                sid=cards[(offset+i*7919)%len(cards)]
                if limits is not None:
                    with self.h.closing(self.h._db()) as db:
                        pos=db.execute('SELECT preferredposition1 FROM players WHERE spid=?',(sid,)).fetchone()
                    if not pos or pos[0] not in limits:continue
                rows=self.book(st,sid,stamp)['rows']
                grade=(10,9,8,7)[i%4]
                chosen=next((r for r in rows if r['grade']==grade and r['count']>0),None)
                if chosen:featured.append(self.public_row(chosen))
                if len(featured)>=24:break
            result.extend(featured[:max(0,40-len(result))])
''' +s[a:]
s=s.replace("'version':2,'supply_version':2", "'version':2,'supply_version':SUPPLY_VERSION")
s=s.replace("'quality_bands':copy.deepcopy(QUALITY_BANDS),", "'quality_bands':copy.deepcopy(QUALITY_BANDS),\n                'regular_high_chances':dict(REGULAR_HIGH_CHANCES),")
p.write_text(s,'utf-8')
compile(s,str(p),'exec')
