"""Small squad validation + atomic state saves with two valid-state backups.
Install after the normal http_config module is defined. Does not migrate or reset user data.
"""
import functools,json,os,pathlib,tempfile

BACKUP_COUNT=2

def _valid_state(st):
 return isinstance(st,dict) and isinstance(st.get('coaches'),list) and isinstance(st.get('teams'),dict) and 'defaultcoachid' in st and isinstance(st['defaultcoachid'],str)

def _atomic_bytes(path,data):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:
   f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  try:os.unlink(tmp)
  except FileNotFoundError:pass

def _valid_bytes(path):
 try:
  raw=pathlib.Path(path).read_bytes();st=json.loads(raw)
  return raw if _valid_state(st) else None
 except (FileNotFoundError,ValueError,UnicodeError):return None

def _squad_ok(hc,team,req):
 if not isinstance(req,dict) or not isinstance(req.get('squad'),dict):return False
 positions=req['squad'].get('positions')
 if not isinstance(positions,list):return False
 cards={hc.iid(p):p for p in team.get('players',[])};ids=[];bases=[];xi=[]
 for p in positions:
  if not isinstance(p,dict):return False
  pid=str(p.get('id'));pos=p.get('pos')
  if isinstance(pos,bool) or not isinstance(pos,int) or pos<0:return False
  # The original client may include reserve rows beyond SUB; they are not a saved squad slot.
  if pos>hc.POS_SUB:continue
  if pid not in cards:continue
  ids.append(pid);bases.append(int(cards[pid]['spid'])%1000000)
  if pos<hc.POS_SUB:xi.append(pos)
 if not 11<=len(ids)<=18 or len(xi)!=11 or len(set(xi))!=11 or xi.count(0)!=1:return False
 if len(set(ids))!=len(ids) or len(set(bases))!=len(bases):return False
 idx=req.get('presetidx')
 if idx is not None and (isinstance(idx,bool) or not isinstance(idx,int) or not 0<=idx<hc.PRESET_SQUADS):return False
 captain=req.get('captain')
 if captain not in (None,'',0) and str(captain) not in cards:return False
 kickers=req.get('kickers')
 if kickers is not None:
  if not isinstance(kickers,list) or len(kickers)>hc.KICKERS:return False
  if any(k not in (None,'',0) and str(k) not in cards for k in kickers):return False
 return True

def install(hc):
 if getattr(hc,'_persistence_guard_installed',False):return
 hc._persistence_guard_installed=True
 original_state=hc._state
 @functools.wraps(original_state)
 def load_state():
  path=pathlib.Path(hc.STATE);backup_paths=[path.with_name(path.name+f'.bak{i}') for i in range(1,BACKUP_COUNT+1)]
  try:
   raw=path.read_bytes();st=json.loads(raw)
   if not _valid_state(st):raise ValueError('state schema is incomplete')
   return st
  except (FileNotFoundError,ValueError,UnicodeError) as exc:
   for backup in backup_paths:
    raw=_valid_bytes(backup)
    if raw is not None:
     print(f'[state] recovered valid snapshot from {backup.name}; next successful save repairs primary',flush=True)
     return json.loads(raw)
   # A genuinely fresh install is empty. Existing but unreadable saves/backups never reset silently.
   if isinstance(exc,FileNotFoundError) and not any(p.exists() for p in backup_paths):return original_state()
   raise
 hc._state=load_state
 def save_state(st):
  if not _valid_state(st):raise ValueError('refusing to save incomplete state')
  # Serialize before opening anything, so serialization errors cannot truncate the current save.
  data=json.dumps(st,ensure_ascii=True).encode('utf-8');path=pathlib.Path(hc.STATE)
  old=_valid_bytes(path)
  if old is not None:
   for i in range(BACKUP_COUNT,1,-1):
    prior=path.with_name(path.name+f'.bak{i-1}');raw=_valid_bytes(prior)
    if raw is not None:_atomic_bytes(path.with_name(path.name+f'.bak{i}'),raw)
   _atomic_bytes(path.with_name(path.name+'.bak1'),old)
  _atomic_bytes(path,data)
 hc._save=save_state
 original_apply=hc.apply_squad
 @functools.wraps(original_apply)
 def apply_squad(team,req):
  return original_apply(team,req) if _squad_ok(hc,team,req) else False
 hc.apply_squad=apply_squad
 original_endpoint=hc.ep_coach_squad
 @functools.wraps(original_endpoint)
 def coach_squad(query,body):
  try:request=json.loads(body or b'{}')
  except (TypeError,ValueError,UnicodeError):request=None
  st=hc._state();team=st.get('teams',{}).get(str(hc._default_slot(st)))
  if team is None or not _squad_ok(hc,team,request):
   return hc._json({'result':False,'reason':'PLAYERLIST_CHANGEPLAYER_FAIL_POPUP_INFO_UNUSABLEPLAYER'})
  return original_endpoint(query,body)
 hc.ep_coach_squad=coach_squad;hc.ENDPOINTS['/coach/me/squad']=coach_squad
