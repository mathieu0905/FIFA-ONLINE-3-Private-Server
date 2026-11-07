from pathlib import Path
import json,hashlib
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
s=Path(r'D:\fifaol3\probability-number-box\install.py').read_text('utf8')
s=s.replace('probability-number-box','enhancement-font-fix').replace('probability_number_box','enhancement_font_fix').replace('PROBABILITY_NUMBER_BOX','ENHANCEMENT_FONT_FIX')
a=s.index(' entry=');b=s.index(" (W/'工程经验.txt')",a)
entry='''\r\n\r\nFO3-ENHANCE-EMBEDDED-FONT-BUTTON-001（2026-11-07）\r\n用户实机截图证实此前自建TextField使用Microsoft YaHei/Arial出现方块/缺字。正式fontconfig.dat的chi段将$NormalFont映射FZLanTingHei-R-GB18030；已直接解析正式fonts_cn.gfx的DefineFont3字表，含28454字形，确认数字、小数点、百分号和强化保护费用中文有字形。仅将两强化ABC的这两个新增字体常量替换成$NormalFont，六处embedFonts false改true，保留索引、全部其它指令、原生标题和数字框位置；字体配置及字库只读并加入完整guard，不改字体资源本身。\r\n用户报告马特乌斯+5/+3按钮灰色：正式只读预览result=true、100%、手续费1324217915，实时EP10494743721853足够，两个实例无锁，未发真实强化测试。静态发现原生余额通知只更新文字而不重算按钮；Control22补重算、Control26末尾按当前两实例对象严格匹配的最新预览同步费用/按钮。保留_available忙锁、余额限制、正数有限费用、过期对象不启用；blocked报价仅允许已有只读说明，原首条guard继续零PUT。不静默切普通付费、不改成功率/保护费/服务端执行/真实资产。按钮漂移修正通过模型回归，不能冒称已重现实机全部触发时序。\r\nD:/fifaol3/enhancement-font-fix保存字体证据、完整指令差分、数值/保护/按钮状态回放和七方法栈流检查。游戏运行只构建/临时回归，任何正式写入前检测并延期；自然退出后fresh正式父层、共同锁、完整guards/receipt policies、seed/valuation/在线配置校验、player_import及目标CAS增量安装，无服务重启/GUI。字体及按钮最终画面待原生验收，不把回放等同实机通过。\r\n'''
s=s[:a]+" entry="+repr(entry)+"\n"+s[b:]
needle=" assert {(r['root'],r['relative']) for r in files}==TARGETS"
assert needle in s
s=s.replace(needle,""" for rel,expected in tx.read(W/'font-evidence.json')['dependencies'].items():
  assert tx.sha(C/rel)==expected,'Embedded font dependency changed; rebuild evidence'
  key=('client',rel.casefold())
  if key in guards:assert guards[key]['sha256']==expected
  guards[key]=dict(root='client',relative=rel,sha256=expected)
"""+needle)
s=s.replace(" m=tx.read(W/'manifest.json');", " assert all(tx.read(W/f)['status']=='PASS' for f in ('tests.json','button-tests.json','stacks.json','install-tests.json'))\n m=tx.read(W/'manifest.json');")
compile(s,'install.py','exec');(R/'install.py').write_text(s,encoding='utf8')
(R/'test_install.py').write_text(Path(r'D:\fifaol3\probability-number-box\test_install.py').read_text('utf8'),encoding='utf8')
deps={rel:hashlib.sha256((C/rel).read_bytes()).hexdigest() for rel in ('data/ui/localization/fontconfig.dat','data/ui/localization/fonts_cn.big')}
evidence=dict(dependencies=deps,alias='$NormalFont',chi_registered_font='FZLanTingHei-R-GB18030',glyph_evidence=json.loads((R/'font-glyphs.json').read_text('utf8')),
 replacing_unregistered_device_fonts=['Microsoft YaHei','Arial'],uses_embedded_font=True,native_verified=False)
assert any(f['name'].rstrip('\0')=='FZLanTingHei-R-GB18030' and f['numbers_and_percent'] and f['sample_chinese'] for f in evidence['glyph_evidence']['fonts'])
(R/'font-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
