"""Explainable, monotone same-player valuation; standard-library inference."""
from pathlib import Path
from contextlib import closing
import hashlib,json,math,sqlite3

EXTRA={'agility','balance','curve','freekickaccuracy','penalties'}

def fields(config):return sorted(set().union(*(set(w) for w in config['role_weights'].values()))|EXTRA)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
def profile(raw,config):
 names=fields(config);value={k:raw[k] for k in names+['playerid','weakfootabilitytypecode','skillmoves']}
 for k,v in value.items():
  if type(v) is not int:raise ValueError('Invalid native integer '+k)
  if k in names and not -3<=v<=255:raise ValueError('Ability outside native range')
 if not 1<=value['weakfootabilitytypecode']<=5 or not 0<=value['skillmoves']<=5:raise ValueError('Invalid native star code')
 value['skillmoves']=min(4,value['skillmoves'])
 return value
def fingerprint(raw,config):return hashlib.sha256(canonical(profile(raw,config))).hexdigest()
def role_scores(raw,config):return {r:sum(max(0,raw[k])*w for k,w in weights.items())/sum(weights.values()) for r,weights in config['role_weights'].items()}
def effective_score(raw,config):
 p=profile(raw,config);roles=role_scores(p,config)
 return max(roles.values())+config['grade1_boost']+(p['weakfootabilitytypecode']-3)*config['weakfoot_score_per_star']+(p['skillmoves']-2)*config['skill_score_per_star']
def segments(score,config):
 knots=config['curve']['knots'];x=max(knots[0],min(knots[-1],score))
 return [max(0.,min(x,b)-a) for a,b in zip(knots,knots[1:])]
def economic_curve(score,config):
 curve=config['curve'];value=math.exp(curve['intercept']+sum(x*s for x,s in zip(segments(score,config),curve['slopes'])))
 # Above the calibrated range, grow linearly in price, not exponentially.
 return value*(1+curve['slopes'][-1]*max(0.,score-curve['knots'][-1]))*config.get('currency_scale',1.)
def strict_floor(raw,config):
 p=profile(raw,config)
 return sum(p[k]+3 for k in fields(config))+25*(p['weakfootabilitytypecode']-1+min(4,p['skillmoves']))
def identity_factor(raw,config):return config.get('identity_factors',{}).get(str(raw['playerid']),{}).get('factor',1.)
def explain(raw,config,market_factor=1.):
 p=profile(raw,config);limits=config['market_factor_bounds']
 if not math.isfinite(market_factor) or not limits[0]<=market_factor<=limits[1]:raise ValueError('Market factor outside common-player bounds')
 score=effective_score(p,config);name=identity_factor(p,config);economics=economic_curve(score,config)*name;floor=strict_floor(p,config)
 roles=role_scores(p,config)
 return dict(playerid=p['playerid'],profile_sha256=fingerprint(p,config),best_role=max(roles,key=roles.get),best_role_native=max(roles.values()),
             effective_score=score,valuation_score_kind='attribute_proxy_not_measured_playability',historical_preference_factor=name,weakfoot=p['weakfootabilitytypecode'],skill_stars=p['skillmoves']+1,identity_factor=name,
             economic_value=economics,strict_floor_ep=floor,fair_price_ep=round(economics)+floor,
             current_price_ep=round(economics*market_factor)+floor,market_factor=market_factor,
             extrapolation='linear_price_tail' if score>config['curve']['knots'][-1] else 'bounded_log_curve')
def catalogue_rows(database,config):
 with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row
  rows=[dict(r) for r in db.execute('select spid,playerid,'+','.join(fields(config)+['weakfootabilitytypecode','skillmoves'])+' from players order by spid')]
 return rows
def verified_catalogue_rows(database,config):
 rows=catalogue_rows(database,config)
 archive=Path(database).parent/'removed-player-profiles.json'
 if archive.exists():
  packet=json.loads(archive.read_text('utf8'))
  former=packet['rows'];expected={231747,13231747,88231747,300231747}
  if packet.get('schema')!=1 or packet.get('playerids')!=[231747] or {r['spid'] for r in former}!=expected or len(former)!=4 or any(r['playerid']!=231747 for r in former):raise ValueError('Invalid removed-player profile archive')
  if any(r['playerid']==231747 or r['spid'] in expected for r in rows):raise ValueError('Removed player reintroduced into gameplay database')
  rows+=former
 return sorted(rows,key=lambda r:r['spid'])

def profile_digest(rows,config):return hashlib.sha256(canonical([[r['spid'],fingerprint(r,config)] for r in sorted(rows,key=lambda r:r['spid'])])).hexdigest()
def build_catalogue(database,config):
 rows=catalogue_rows(database,config);details=[]
 for r in rows:details.append(dict(spid=r['spid'],**explain(r,config)))
 return dict(schema=1,revision=config['revision'],model_sha256=hashlib.sha256(canonical(config)).hexdigest(),profile_sha256=profile_digest(rows,config),rows=details)
def verify_profiles(database,catalogue,config):
 if hashlib.sha256(canonical(config)).hexdigest()!=catalogue['model_sha256']:raise ValueError('Pricing model differs')
 rows=verified_catalogue_rows(database,config)
 if profile_digest(rows,config)!=catalogue['profile_sha256']:raise ValueError('PLAYER_ATTRIBUTES_CHANGED: rebuild valuation catalogue in the same roster publication transaction')
 if len(rows)!=len(catalogue['rows']):raise ValueError('Catalogue coverage differs')
 return dict(status='FAIR_VALUE_PROFILE_BINDING_PASS',rows=len(rows),revision=config['revision'],profile_sha256=catalogue['profile_sha256'])
