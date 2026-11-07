from pathlib import Path
p=Path('D:/fifaol3/market-supply-v3/market_simulation.py');s=p.read_text('utf8')
s=s.replace("if book and book['epoch'] >= epoch:\n            return book\n        rows = []\n        for g in range(1, min(10, self.h.MAX_GRADE) + 1):", "if book and (book['epoch'] > epoch or (book['epoch']==epoch and book.get('supply_version')==SUPPLY_VERSION)):\n            return book\n        upgrading=bool(book and book['epoch']==epoch)\n        rows = copy.deepcopy(book['rows']) if upgrading else []\n        for g in range(7 if upgrading else 1, min(10, self.h.MAX_GRADE) + 1):")
s=s.replace("book = {'epoch': epoch, 'rows': rows}; books[key] = book", "book = {'epoch': epoch, 'rows': rows, 'supply_version':SUPPLY_VERSION}; books[key] = book")
p.write_text(s,'utf8')
