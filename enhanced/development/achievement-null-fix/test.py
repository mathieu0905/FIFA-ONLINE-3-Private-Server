from pathlib import Path
import ast,json,sys,re,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,R,instructions
ns={'__file__':str(W/'test.py')}
exec(Path(r'D:\fifaol3\enhancement-remember\test_client.py').read_text('utf8').split('a=ABC((W/')[0],ns)
VM=ns['VM'];U=ns['U']
native=ABC((W/'native-tooltip.abc').read_bytes())
mid=next(m for c in native.A['cls'] if c[0]=='CoachAchievementListTabPage' for kind,n,m in c[3] if n=='onUpdateTooltipData')
old=json.loads((W/'itemnames-live.json').read_text('utf8'))
ids=list(map(int,old));env=dict(EP_ITEM=1,ES_ITEM=2,PACKS=ids[2:],ITEMS=[],PACKAGES=[],MONTHLY=[],item_def=lambda i:{'name':old[str(i)]['ind']},_json=lambda value:value)
exec((W/'replacement.py').read_text('utf8'),env)
new=env['ep_itemnames']({},b'')
assert old.keys()==new.keys()
for key in old:
 assert all(new[key][lang]==value for lang,value in old[key].items())
 assert all(isinstance(new[key][lang],str) and new[key][lang] for lang in ('ind','kor','eng','chi','tha','vie','tai'))
def native_read(row,locale):
 class NativeObject(dict):
  def __missing__(self,key):return U
 row=NativeObject(row)
 v=VM(native,{})
 def remove_html(value):
  if value is U or value is None:raise TypeError('Native removeHTML null string contract')
  return re.sub('<[^>]*>','',value)
 v.globals.update(Localization={'LOCALE':locale},StringUtil={'removeHTML':remove_html})
 v.run(mid,start=228,stop=263,locals_override={12:row})
for locale in ('eng','chi','tha','vie','tai'):
 try:native_read(old['1'],locale)
 except TypeError:pass
 else:raise AssertionError('Missing locale did not reproduce null boundary')
for row in new.values():
 for locale in ('ind','kor','eng','chi','tha','vie','tai',''):native_read(row,locale)
checks=['Current live ITEMNAMES misses 5 locale keys; exact native tooltip bytecode reproduces missing-name null boundary','Replacement preserves every existing ID and ind/kor string','All catalog rows have nonempty strings for 7 supported native locales','Exact native onUpdateTooltipData228-263 succeeds for every row and 7 locales plus empty-locale native kor fallback','No state/shop writes, transactions, service/GUI actions or client changes']
result=dict(status='PASS',checks=checks,rows=len(new),native_method=mid,native_slice=[228,263],game_gui_used=False,native_game_verified=False,formal_files_written=False,source_sha256=hashlib.sha256((W/'replacement.py').read_bytes()).hexdigest())
(W/'tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
