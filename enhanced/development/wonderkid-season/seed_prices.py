from pathlib import Path
import hashlib,json,math,sqlite3,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;P=Path('D:/fifaol3/npc-peer-market')
sys.path.insert(0,str(P/'expanded-training'))
from expanded_value_model import ExpandedValueModel
modelpath=P/'highend-training/results/selected-model.json.gz';model=ExpandedValueModel(modelpath)
B=R/'install-build-v2';rows=[]
with sqlite3.connect((B/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    for row in db.execute('select * from players where spid/1000000=18'):
        raw=dict(row);value=model.log_predict(raw);assert math.isfinite(value)
        price=min(5_600_000_000_000_000,max(1,round(math.exp(value))//1000));rows.append([row['spid'],price])
assert len(rows)==40
data=dict(schema=1,model_sha256=hashlib.sha256(modelpath.read_bytes()).hexdigest(),rows=rows,policy='One-time additive seeds only; preserve all current prices and events; no runtime model import')
(R/'price-seeds.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(cards=40,min=min(p for _,p in rows),max=max(p for _,p in rows))),flush=True)
