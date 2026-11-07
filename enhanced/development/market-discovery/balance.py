from pathlib import Path
p=Path('D:/FO3ID/server/market_simulation.py');s=p.read_text('utf8')
a=s.index('        for index in range(max((len(g[0]) for g in groups), default=0)):');b=s.index('\n        return result',a)
s=s[:a]+'''        def available(group, values):
            cards, offset, step = values
            for index in range(len(cards)):
                sid = cards[(offset + index * step) % len(cards)]
                if sid in seen:
                    continue
                rows = self.book(st, sid, stamp)['rows']
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
''' +s[b:]
p.write_text(s,'utf8')
