from pathlib import Path
R=Path(__file__).parent
s=Path(r'D:\fifaol3\enhancement-probability-ui\install.py').read_text('utf8')
s=s.replace('probability-ui','probability-number-box').replace('probability_ui','probability_number_box').replace('INSTALLED_PROBABILITY_UI','INSTALLED_PROBABILITY_NUMBER_BOX').replace('PROBABILITY_UI_PREFLIGHT_PASS','PROBABILITY_NUMBER_BOX_PREFLIGHT_PASS')
start=s.index(" template=(S/'patches/protection_preview_fix_preflight.py')")
end=s.index(" needle=' if not required<=seen:'",start)
s=s[:start]+''' template=(S/parent_path).read_text(encoding='utf-8')
 parent_status=tx.read(S/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_PROBABILITY_NUMBER_BOX'),(proof['status'],'PROBABILITY_NUMBER_BOX_PREFLIGHT_PASS')]:template=template.replace(old,new)
'''+s[end:]
a=s.index(" entry='''");b=s.index(" (W/'工程经验.txt')",a)
entry='''\r\n\r\nFO3-ENHANCE-PROBABILITY-NUMBER-BOX-001（2026-11-07）\r\n用户反馈新增成功率中文乱码且位置不明显，要求放在“成功率加成”区域的框中，并把该标题直接改成“成功率”。仅替换上一概率显示层五个显示/清空方法中的注入，强化页字段改挂Control._owner.infoPanel.enhanceRate，复用原生中文标题__id7_和原有字形改文案为“成功率”；数字框位于标题下x0/y36/180x40，深底边框、Arial24居中，只显示ASCII数字与百分号，缺失“-”、取数中“...”。保留服务端preview.probability小数和0/100，根据用户截图，确认页定位boostInfoPanel.boostInfoContainer.boostRate，复用原生__id15_标题改为“成功率”，隐藏旧箭头rateContainer，在其原位置添加带边框数字框（宽度跟随原容器、40号Arial、仅百分比），不再在底部提示附近加成功率文字；移除上一新增TextField中的中文输出。其它方法、扣费/签名/blocked保卫/恢复、其它SWF标签和BIG资源成员保持。\r\n工作证据D:/fifaol3/probability-number-box。已做原生静态显示列表路径核对、确定性回放和五方法完整栈流检查，不能代替游戏画面或GFx类型验收。未改变概率/手续费/保护费或真实资产。不启动第二套服务、不启停服务、不操作游戏GUI。游戏运行中准备构建，安装器在任何正式写入前检查并延期；自然结束后fresh顶层、完整guards/receipt policies、seed/valuation/在线配置校验、独立player_import及共同双锁/CAS增量安装。\r\n'''
s=s[:a]+" entry="+repr(entry)+"\n"+s[b:]
compile(s,'install.py','exec');(R/'install.py').write_text(s,encoding='utf8')
(R/'test_install.py').write_text(Path(r'D:\fifaol3\enhancement-probability-ui\test_install.py').read_text('utf8'),encoding='utf8')

