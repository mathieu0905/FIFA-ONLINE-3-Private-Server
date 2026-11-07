"""Validated online market configuration. Never writes manager state or price data."""
import copy,hashlib,json,math,os,re,tempfile
from pathlib import Path
BANDS=('low','mid','high','elite')
DEFAULTS=dict(schema=1,rare_listing_seconds=1800,npc_listing_seconds=1800,regular_refresh_seconds=900,discovery_seconds=300,background_seconds=15,
 regular_counts={str(g):{1:12,2:6,3:3}.get(g,1) for g in range(1,11)},
 regular_chances={b:{str(g):(r[g-4] if g<=6 else {7:.95,8:.85,9:.70,10:.55}[g]*f) for g in range(4,11)} for b,r,f in (('low',(.85,.65,.45),1.),('mid',(.65,.45,.25),.9),('high',(.4,.25,.12),.8),('elite',(.2,.1,.04),.7))},
 rare_overrides={})

def number(value,lo,hi,integer=False):
 if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi or (integer and type(value) is not int):raise ValueError('Invalid market configuration number')
 return value

def validate(value):
 if type(value) is dict:
  value=copy.deepcopy(value);value.setdefault('rare_listing_seconds',1800);value.setdefault('npc_listing_seconds',1800)
 if type(value) is not dict or set(value)!=set(DEFAULTS) or type(value['schema']) is not int or value['schema']!=1:raise ValueError('Invalid market configuration schema')
 for k,lo,hi in (('rare_listing_seconds',60,86400),('npc_listing_seconds',60,86400),('regular_refresh_seconds',60,86400),('discovery_seconds',30,86400),('background_seconds',5,300)):number(value[k],lo,hi,True)
 if type(value['regular_counts']) is not dict or set(value['regular_counts'])!=set(DEFAULTS['regular_counts']):raise ValueError('Expected grades 1..10 counts')
 for n in value['regular_counts'].values():number(n,0,100,True)
 if type(value['regular_chances']) is not dict or set(value['regular_chances'])!=set(BANDS):raise ValueError('Expected four quality bands')
 for b in BANDS:
  rates=value['regular_chances'][b]
  if type(rates) is not dict or set(rates)!={str(g) for g in range(4,11)}:raise ValueError('Expected grades 4..10 chances')
  for n in rates.values():number(n,0,1)
 overrides=value['rare_overrides']
 if type(overrides) is not dict or len(overrides)>40:raise ValueError('Invalid rare overrides')
 for key,rule in overrides.items():
  if not re.fullmatch(r'(low|mid|high|elite)_(1[1-9]|20)',key) or type(rule) is not dict or set(rule)!={'period_seconds','slots','chance','quantity'}:raise ValueError('Invalid rare tier rule')
  number(rule['period_seconds'],300,365*86400,True);number(rule['slots'],1,4096,True);number(rule['chance'],0,1);number(rule['quantity'],0,100,True)
  if rule['period_seconds']/rule['slots']<5:raise ValueError('Rare release slots must be at least 5 seconds apart')
 return copy.deepcopy(value)

class SupplySettings:
 def __init__(self,path,lock):
  self.path=Path(path);self.lock=lock;self.data=copy.deepcopy(DEFAULTS);self.active_revision='defaults';self.disk_revision='defaults';self.error=None;self.refresh()
 @staticmethod
 def digest(raw):return hashlib.sha256(raw).hexdigest() if raw is not None else 'defaults'
 def raw(self):return self.path.read_bytes() if self.path.exists() else None
 def refresh(self):
  with self.lock:
   try:
    raw=self.raw();revision=self.digest(raw)
    if revision==self.disk_revision and self.error is None:return
    self.disk_revision=revision;data=validate(json.loads(raw.decode('utf-8-sig'))) if raw is not None else copy.deepcopy(DEFAULTS)
    self.data=data;self.active_revision=revision;self.error=None
   except (ValueError,OSError,UnicodeError) as e:self.error=str(e)
 def get(self,params=None):
  self.refresh()
  with self.lock:return dict(revision=self.disk_revision,active_revision=self.active_revision,error=self.error,settings=copy.deepcopy(self.data),defaults=copy.deepcopy(DEFAULTS),apply_policy='Current offers and drawn batches stay frozen; regular settings apply on next book expiry; rare rules apply at next batch, with future quota extension on increases; listing TTL is independent of release frequency and surviving offers carry across batches; worker delay applies after current wait')
 def set(self,params):
  data=validate(params.get('settings'))
  with self.lock:
   if params.get('revision')!=self.digest(self.raw()):raise ValueError('Market configuration changed; reload before saving')
   raw=(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf8');self.path.parent.mkdir(parents=True,exist_ok=True)
   fd,tmp=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.tmp',dir=self.path.parent)
   try:
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,self.path)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
   self.data=data;self.disk_revision=self.digest(raw);self.active_revision=self.disk_revision;self.error=None
   return self.get()
 def register(self):
  import admin
  admin.READ_ONLY.add('market_supply_config');admin.API['market_supply_config']=self.get;admin.API['market_supply_config_set']=self.set
