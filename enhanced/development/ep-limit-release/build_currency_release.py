from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;O=R/'compact-module';S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
font=C/'data/ui/localization/fontconfig.dat';original=font.read_bytes();assert original[:2]==b'\xff\xfe';raw=original.decode('utf-16');marker='[FontConfig "chi"]'
at=raw.index(marker);head,body=raw[:at],raw[at:]
needle='map "$NormalFont" = "HelveticaNeueLT Std Med" Normal'
assert body.count(needle)==1
body=body.replace(needle,'map "$NormalFont" = "FZLanTingHei-R-GB18030" Regular')
(O/'payload/fontconfig.dat').write_bytes((head+body).encode('utf-16'))
play=(S/'play-local.bat').read_bytes();needle=b'patches\\fc_retirement_preflight.py';assert play.count(needle)==1
(O/'payload/play-local.bat').write_bytes(play.replace(needle,b'patches\\compact_currency_preflight.py'))
rows=[]
for root,relative,payload in [('server','play-local.bat','play-local.bat'),
     ('server','patches/compact_currency_preflight.py','player_value_preflight.py'),
     ('client','data/ui/libs/Module.big','Module.big'),
     ('client','data/ui/localization/fontconfig.dat','fontconfig.dat')]:
    rows.append(dict(root=root,relative=relative,payload=payload,parent_sha256=sha((S if root=='server' else C)/relative),sha256=sha(O/'payload'/payload)))
m=dict(schema=1,release_id='20261106-currency-compact-chinese-font-v1',phase='CURRENCY_COMPACT_MODULE_FONT',client_root=str(C),
       state_shop_replaced=False,fontconfig_parent_sha256=sha(font),
       parent_files={n:sha(S/n) for n in ('patches/fc_retirement_preflight.py','patches/fc-retirement-release-manifest.json','patches/fc-retirement-release-installed.json')},
       files=rows,reports={n:sha(O/n) for n in ('build.json','test-result.json','install-test-result.json')})
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
code=(R/'install.py').read_text(encoding='utf-8').replace("status='INSTALLED_PLAYER_VALUE_DIV1000'","status='INSTALLED_CURRENCY_COMPACT'")
(O/'install.py').write_text(code,encoding='utf-8')
print(json.dumps(dict(status='BUILT',targets=4,font_locale_scope='chi only',module_other_methods_preserved=True),indent=2))
