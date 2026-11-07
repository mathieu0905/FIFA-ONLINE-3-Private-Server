from pathlib import Path
import os,sys,json,math
from unittest.mock import patch
R=Path(__file__).resolve().parent;P=R/'sandbox/server'
sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
import admin as a
from pack_probability import clean,probabilities,grades
a.hc=h
checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
check('Approved six-grade curve',probabilities(6,11)==[30,28,25,10,6,1])
for low in range(1,21):
    for high in range(low,21):
        values=probabilities(low,high)
        assert len(values)==high-low+1 and abs(sum(values)-100)<1e-8 and all(x>=0 for x in values)
check('All 210 valid ranges normalized including fixed grades',True)
for bad in [dict(min_grade=12,grade=11),dict(min_grade=0,grade=11),dict(min_grade=6,grade=21),dict(min_grade=6,grade=11,probability_mode='manual',grade_probabilities=[30,28,25,10,6,2]),dict(min_grade=6,grade=11,probability_mode='manual',grade_probabilities=[30,28,25,10,6,float('nan')]),dict(min_grade=6,grade=11,probability_mode='manual',grade_probabilities=[30,28,25,10,6]),dict(min_grade=6,grade=11,probability_mode='wat')]:
    try:clean(bad)
    except ValueError:pass
    else:raise AssertionError(bad)
check('Reject invalid ranges, sum, missing grades, NaN and unknown modes',True)
draft=dict(name='概率回归草稿',icon='2000006',seasons=[],all=True,min_grade=6,grade=11,probability_mode='formula')
definition=a.check_def('packs',draft,99980001)
entry=h.pack_from(definition)
check('Admin serialization retains both bounds and all odds',h.pack_to(entry)['grade_probabilities']==[30,28,25,10,6,1] and h.pack_to(entry)['min_grade']==6)
h.PACKS[99980001]=entry
check('Actual draw engine uses exact preview probabilities',h.pack_grades(99980001)==list(zip(range(6,12),a.pack_probability_preview(draft)['grade_probabilities'])))
draft.update(probability_mode='manual',grade_probabilities=[25,25,25,15,8,2])
definition=a.check_def('packs',draft,99980001);h.PACKS[99980001]=h.pack_from(definition)
check('Manual odds reach actual draw engine',h.pack_grades(99980001)==list(zip(range(6,12),[25,25,25,15,8,2])))
with patch.object(h.random,'choices',return_value=[11]) as draw:
    assert h.pack_grade(99980001)==11
    assert draw.call_args.args==([6,7,8,9,10,11],[25,25,25,15,8,2])
check('Opening samples configured weights',True)
for itemid in (97500022,97600911,97300011,97100022,97010004):
    assert a.probability_frozen(itemid)
    definition=a.probability_definition(itemid,h.PACKS[itemid])
    assert definition['probability_locked']
    assert all(abs(w-dict(h.pack_grades(itemid))[g]*100/sum(w for _,w in h.pack_grades(itemid)))<1e-8 for g,w in grades(definition))
check('Issued packs display actual frozen odds and are locked',True)
excluded=set(h.product_packs.get('excluded_retired_cards',[]))
check('New issues exclude retired cards while original pools stay frozen',all(not excluded.intersection(t['pool']) for section in ('risk_packs','strength_packs') for d in h.product_packs[section].values() for t in d['tiers']))
a.check_i18n()
check('Admin locale integrity',True)
(R/'probability-test-results.json').write_text(json.dumps(dict(status='PASS',count=len(checks),checks=checks),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=True))
