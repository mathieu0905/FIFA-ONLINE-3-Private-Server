from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;V3=W.parent/'lineup-enhance-v3'
src3=(V3/'test.py').read_text('utf8');exec(compile(src3.split('\nbuild=json.loads')[0],'<AVM replay support>','exec'))
build=json.loads((W/'client-build.json').read_text());stacks={};checks=[]
for key,row in build.items():
 a=ABC((W/(row['prefix']+'-after.abc')).read_bytes());stacks[row['prefix']]={str(row['method']):stackns['check'](a,row['method'])}
 for mid,code in a.A['body'].items():assert all(code[t]==9 for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at),(key,mid)
renderer=ABC((W/'components-ScrollingList-3451-after.abc').read_bytes());screen=ABC((W/'TeamManagementScreen-29-after.abc').read_bytes());panel=ABC((V3/'TeamManagementPlayerEnhancementTabPage-289-after.abc').read_bytes());eventabc=ABC((V3/'native-ListEvent.abc').read_bytes())
rm=dict(click=42,init=43,sync=44);drive=20;PENDING='fo3LineupRequestV2';ICON='fo3LineupEnhanceV3'
fixture=src3[src3.index('class Display'):src3.index('x=setup();row=')].replace("width=64,height=37","width=67,height=35").replace("name=='TransferMarketRollOverButton'","name=='PlayerSwapButton'")
exec(compile(fixture,'<native list fixture>','exec'))
x=setup();row=x['row'];before={key:dict(row[key]) for key in ('playerDetailInfoButton','playerLockButton','playerUnLockButton')}
x['machine'](renderer,row).run(rm['init'],(None,));x['machine'](renderer,row).run(rm['sync'],(None,));icon=row['getChildByName'](ICON)
assert (icon['width'],icon['height'])==(67,35) and not icon['children'] and x['skins']==['PlayerSwapButton']
assert all(dict(row[k])==v for k,v in before.items())
checks.append('Unmodified native PlayerSwapButton capsule at natural size: no graphics overlay, no child glyph, no compound resizing; original search/lock/unlock untouched')
flow=src3[src3.index("x=setup();click(x);assert not x['nav']"):src3.index('original=(W.parent/')]
exec(compile(flow,'<native click readiness cases>','exec'))
raw=json.loads((W/'real-avm-results.json').read_text('utf8'))
assert 'VerifyError: Error #1021' in raw['broken']['output']
assert 'DRIVE_RETURNED' in raw['labels_fixed']['output'] and 'VerifyError' not in raw['labels_fixed']['output']
diag=ABC((W/'labels_fixed.abc').read_bytes());assert diag.A['body'][20]==screen.A['body'][20]
checks.append('Real AVMplus verifier: exact shipped drive method reproduces #1021; same body with two explicit loop labels returns normally; tested method equals produced method byte-for-byte; only diagnostic constructor/UI dependencies stubbed')
enh=Path(r'D:\FO3ID\32795\data\ui\TeamManagementPlayerEnhancementTabPage.big');assert hashlib.sha256(enh.read_bytes()).hexdigest()=='cd8f7b2d8dd747eb617b6b64b93631602a99ad77bdead962403b690fbbdde314'
checks.append('Stable native enhancement BIG remains untouched')
result=dict(status='PASS',checks=checks,stack_checks=stacks,source_sha256={k:v['source_sha256'] for k,v in build.items()},output_sha256={k:v['sha256'] for k,v in build.items()},real_avm_verifier_pass=True,game_GUI_used=False,native_game_verified=False,unique_game_crash_cause_proven=False)
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
