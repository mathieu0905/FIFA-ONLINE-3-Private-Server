"""Build an auditable additive installer from the already regression-tested transaction."""
from pathlib import Path
import ast,hashlib,json,sys,sqlite3
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');U=R.parent/'upstream-review'
sys.path.insert(0,str(S/'tools/value_v11'))
from predict import IdentityValueModel

def replace_function(source,name,body):
 n=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
 lines=source.splitlines(keepends=True);return ''.join(lines[:n.lineno-1])+body+'\n\n'+''.join(lines[n.end_lineno:])

def main():
 model=IdentityValueModel();con=sqlite3.connect(R/'prepared-v3/fifadb.sqlite');con.row_factory=sqlite3.Row
 rows=[[r['spid'],model.predict(dict(r))] for r in con.execute('select * from players where spid/1000000=327 order by spid')];con.close();assert len(rows)==32
 packet=dict(schema=1,revision='china-future-20261107-v1',model_sha256=model.sha256,source_sha256=hashlib.sha256((R/'input/cards.json').read_bytes()).hexdigest(),prices_sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),rows=rows)
 (R/'prices.json').write_text(json.dumps(packet,indent=2),'utf8')
 src=(U/'live_market_extension.py').read_text('utf8').replace('fo4-live-25-26-upstream-ed08cf1','china-future-20261107-v1').replace('688','32').replace('in (300,325)','== 327').replace('FO4_LIVE_PRICE_EXTENSION_PASS','CHINA_FUTURE_PRICE_EXTENSION_PASS')
 compile(src,'price_extension.py','exec');(R/'price_extension.py').write_text(src,'utf8')
 src=(U/'install.py').read_text('utf8')
 changes={
  'upstream_live_preflight.py':'china_future_preflight.py','upstream-live-installed.json':'china-future-installed.json','upstream-live-receipt.json':'china-future-receipt.json',
  'upstream-ed08cf1-live25-26':'china-future-v1','INSTALLED_UPSTREAM_LIVE':'INSTALLED_CHINA_FUTURE','UPSTREAM_LIVE_PREFLIGHT_PASS':'CHINA_FUTURE_PREFLIGHT_PASS',
  'fo4_live_market.py':'china_future_market.py','fo4-live-price-extension.json':'china-future-price-extension.json',
  "R/'live_market_extension.py'":"R/'price_extension.py'","R/'adapted-source/gamedata/china-future-price-extension.json'":"R/'prices.json'",
  "'upstream-live-'":"'china-future-'",'new_cards=688,new_generic_identities=302':'new_cards=32,new_generic_identities=32',
  'new_cards=688,new_generic_identities=302':'new_cards=32,new_generic_identities=32',
  "upstream_commit='ed08cf18aeb14a5e16426a85798c291dc1817656'":"card_edition='China Future custom potential v1'",
  "            native_game_verified=False,match_verified=False,new_cards=688,new_generic_identities=302,":"            native_game_verified=False,match_verified=False,new_cards=32,new_generic_identities=32,",
 }
 for a,b in changes.items():src=src.replace(a,b)
 src=replace_function(src,'payloads','''def payloads():
    files={('server','http_config.py'):(R/'http_config.py').read_bytes(),
      ('server','responses/static_roster.json'):(R/'static_roster.json').read_bytes(),
      ('server','gamedata/china-future-price-extension.json'):(R/'prices.json').read_bytes(),
      ('server','china_future_market.py'):(R/'price_extension.py').read_bytes(),
      ('client','data/data_0.big'):(R/'prepared-v3/data_0.big').read_bytes(),
      ('client','data/ui/components/Label.big'):(R/'Label.big').read_bytes(),
      ('server','patches/Label.big'):(R/'Label.big').read_bytes()}
    for rel in ('fifadb.sqlite','custom_rosters.json','player-imports.json'):
        files[('server','gamedata/'+rel)]=(R/'prepared-v3'/rel).read_bytes()
    for p in sorted((R/'input/portraits').glob('*.png')):
        files[('client','_cache/games/fo3id/externalAssets/players/'+p.name)]=p.read_bytes()
    assert len(files)==42
    return files''')
 src=replace_function(src,'check_inputs','''def check_inputs():
    review=json.loads((R/'reviewed-payloads.json').read_text('utf8'))
    for path,digest in review['files'].items():
        if sha(path)!=digest:raise RuntimeError('Reviewed payload changed: '+path)
    for path,digest in review['formal_baseline'].items():
        if sha(path)!=digest:raise RuntimeError('Formal baseline advanced; fresh/rebuild '+path)
    if json.loads((R/'tests.json').read_text('utf8'))['status']!='PASS':raise RuntimeError('Regression missing')''')
 src=replace_function(src,'helper_source','''def helper_source(parent):
    h=parent['helper'];source=(S/parent['relative']).read_text('utf8')
    receipt=json.loads((S/h.RECEIPT).read_text('utf8'))
    for old,new in ((h.MANIFEST,MANIFEST),(h.RECEIPT,RECEIPT),(h.SELF,SELF),(receipt['status'],'INSTALLED_CHINA_FUTURE'),(parent['proof']['status'],'CHINA_FUTURE_PREFLIGHT_PASS')):
        if old not in source:raise RuntimeError('Fresh parent shape changed '+old)
        source=source.replace(old,new)
    anchor='\\n if not required<=seen:'
    assert source.count(anchor)==1
    source=source.replace(anchor,"\\n required.update({('server','china_future_market.py'),('server','gamedata/china-future-price-extension.json'),('server','gamedata/player-import-validation.json'),('server','responses/static_roster.json')})"+anchor)
    anchor=' return dict('
    assert source.count(anchor)==1
    verification=" spec=importlib.util.spec_from_file_location('_china_future_guard',server/'china_future_market.py');china_ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(china_ext)\\n china_prices=china_ext.verify(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/china-future-price-extension.json')\\n"
    source=source.replace(anchor,verification+' return dict(china_future_prices=china_prices,',1)
    compile(source,SELF,'exec');return source.encode('utf8')''')
 # Keep all publication ordering, stop deferral, rollback, assets, full certificate,
 # guard inheritance and watcher recovery code exactly as the exercised installer.
 tree=ast.parse(src);n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LEDGER' for t in n.targets))
 lines=src.splitlines(keepends=True)
 ledger='\n\nFO3-CHINA-FUTURE-001（2026-11-07）：新增327中国明日之星32名真实身份，王钰栋92/李昊炎92等，+1/LV1/无套装加成主位置显示85–92。能力为用户授权的自定义潜力设定，按真实位置权重计算，不能只填overallrating。出生日期逐人来源记录在registry；依木兰采用新疆体育局2005-05-03，李昊炎采用原达姆官网2012-01-28；体型数值是游戏建模参数，不冒称官方当前测量。32新身份明确内置通用脸+实名剪影，native playerid唯一、六语姓名/双端UI/原生身份/技能码/资源回执经正式prepare与full check；不改变已有模型或同人身份。新卡加入现有传奇系列及传奇时刻额外加成成员，混搭首发人数累计，原加成参数/取最高/替补排除规则不变；旧卡包原池排除327，新卡可市场检索并按已有v11模型仅追加新种子。保留此前上游688卡、双卡强化保护、五档六人、AI+10/LV30及所有旧guards/policies/校准事件。安装依实际游戏状态在写前延期，fresh停服快照，不写测试卡/经理/余额；静态、首页近远景及比赛验收分别记录，无GUI/实机不得冒称通过。证据D:/fifaol3/china-future/tests.json及installed-handback.json。\n'
 ledger+='用户随后明确加入更年轻一批并提高李昊炎：最终32人，原16人另补2009/2010年出生的邝兆镭、万项、谢晋、周雨诺、帅惟浩、吕孟洋、金昱成、南子勋、李钧鹏、张旭尧、秦子牛、江承恩、潘朝伟、徐正鹏、赵松源、顾博宇。李昊炎最终92，与王钰栋同第一档；旧16人/91工作产物已废弃，最终完整产物prepared-v3。\n'
 src=''.join(lines[:n.lineno-1])+'LEDGER='+repr(ledger)+'\n'+''.join(lines[n.end_lineno:])
 src=src.replace("        grade_note='", "        grade_note='")
 # The old grade note belongs to an immutable previous installation, not this one.
 src='\n'.join(line for line in src.split('\n') if not line.startswith('        grade_note='))
 src=src.replace("+grade_note.encode('utf8')",'')
 compile(src,'install.py','exec');(R/'install.py').write_text(src,'utf8')
 print(json.dumps(dict(status='RELEASE_PREPARED',cards=32,price_min=min(p for s,p in rows),price_max=max(p for s,p in rows))))

if __name__=='__main__':main()
