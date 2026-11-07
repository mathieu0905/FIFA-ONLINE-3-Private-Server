from pathlib import Path
import json
W=Path(__file__).parent
s=Path(r'D:\fifaol3\enhancement-font-fix\install.py').read_text('utf8')
s=s.replace('from contextlib import contextmanager','from contextlib import contextmanager,nullcontext')
s=s.replace('enhancement-font-fix','protection-checkbox').replace('enhancement_font_fix','protection_checkbox').replace('ENHANCEMENT_FONT_FIX','PROTECTION_CHECKBOX')
s=s.replace("for p in (SELF,'play-local.bat',DOC)","for p in (SELF,'play-local.bat',DOC,'enhancement_protection40.py')")
s=s.replace("(W/'build.json')", "(W/'client-build.json')")
a=s.index(' entry=');b=s.index(" (W/'工程经验.txt')",a)
entry='''\r\n\r\nFO3-INDEPENDENT-PROTECTION-CHECKBOX-001（2026-11-07）\r\n用户要求保护与黄金强化加成不冲突，保护改独立勾选框；并指出数字框本身太丑。新增默认不勾选的保护选项，下拉保留黄金/白银等原生加成道具，重置/换卡取消保护，忙时不可切换。百分比在贴合原图标区域的深色圆角块中居中，去掉生硬矩形文字边框和旧箭头；其它布局不改。继续使用已验证的$NormalFont与嵌入字形。\r\n勾选时预览URI附protection=1，原生确认页沿用实际preview的完整保护条款/签名，执行路径保留所选黄金等itemid；服务端签名绑定经理/卡实例/等级/经验/价格/概率/配置/加成道具itemid和库存快照，单STATE_LOCK/一次_save扣40%保护费（替代2%手续费）、材料和1个加成道具；成败均耗费，失败保级经验保留，点数/活动继续叠加。旧1000090路径兼容，但不再把伪保护道具注入下拉库存。过期/缺库存/改加成/改数量/改概率/伪造签名拒绝，达到100%和安全档不收费保护、非fatal提示取消勾选，不静默改普通付费。旧恢复权益不覆盖，放弃仍双确认。\r\nControl34拒绝先前勾选/道具/点数/卡组的迟到响应，防止取消保护后旧报价覆盖。原强化执行、恢复、确认和签名URI方法字节保留；上轮字体及按钮重算保留。D:/fifaol3/protection-checkbox含真实路由临时存档回归、客户端交互/样式/字节差分、10方法栈流与事务故障验证。所有测试无真实购包/强化或测试资产写入；未操作GUI，不把回放当实机显示通过。运行中不写正式文件/启停；自然结束后fresh最新父层、双锁、备份/CAS、完整guards/policies/seed/valuation/在线cfg/player_import并守护重启加载服务模块。\r\n'''
s=s[:a]+" entry="+repr(entry)+"\n"+s[b:]
s=s.replace(" payloads=[]", " build=tx.read(W/'server-build.json')\n assert tx.sha(S/'enhancement_protection40.py')==build['source_sha256'],'Protection module changed; rebase required'\n assert tx.sha(W/'enhancement_protection40.py')==build['sha256']\n payloads=[('server','enhancement_protection40.py','enhancement_protection40.py')]")
s=s.replace('def install():','def install(held=False):')
s=s.replace(" m=tx.read(W/'manifest.json');", " if not held:raise RuntimeError('Server code requires guarded cutover.py; do not install without idle restart')\n m=tx.read(W/'manifest.json');")
s=s.replace(' with locks():',' with (nullcontext() if held else locks()):')
s=s.replace("('tests.json','button-tests.json','stacks.json','install-tests.json')", "('server-tests.json','client-tests.json','stacks.json','install-tests.json')")
s=s.replace('no_service_restart=True','no_service_restart=False')
compile(s,'install.py','exec');(W/'install.py').write_text(s,encoding='utf8')
(W/'font-evidence.json').write_bytes(Path(r'D:\fifaol3\enhancement-font-fix\font-evidence.json').read_bytes())
(W/'test_install.py').write_text(Path(r'D:\fifaol3\enhancement-font-fix\test_install.py').read_text('utf8'),encoding='utf8')
