"""Current-parent guarded install of the timeline/native-instance-method correction."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'random-pack-click-fix'
source=(OLD/'install.py').read_text('utf8')
source=source.replace('random-pack-click-fix','random-pack-click-fix-v2').replace('RANDOM_PACK_CLICK_FIX','RANDOM_PACK_CLICK_FIX_V2')
source=source.replace("    assert read(ROOT/'client/client-tests.json')['status']=='PASS'",
    "    assert read(ROOT/'client/client-tests.json')['status']=='PASS'\n"
    "    assert read(ROOT/'client/structure-tests.json')['status']=='PASS'\n"
    "    assert read(ROOT/'installer-tests.json')['status']=='PASS'")
start=source.index('        addition=')
end=source.index("        entry('server',doc,",start)
addition=("\r\n\r\nFO3-RANDOM-PACK-CLICK-FIX-002（2026-11-07）\r\n"
          "用户实机再次反馈点击无响应，日志无新的bulk请求且原单开/连续仍可点。此前动态新组件+newfunction的事件链模型未证明真实鼠标入口，不能把模拟派发通过写成实机修复通过；ObjectUtil清理闭包强持有listener，不能仅凭weak=true判定GC根因。"
          "本次把第三原生按钮放入mainButtonContainer首帧PlaceObject3，追加同类型slot，按原生configUI绑定新的screen实例method68；复用旧bound26已实际发过bulk的事务代码与原65/66回调作用域，保留26连续及单开。"
          "三按钮同原生皮肤、宽240、最终y0；入口与忙/教学/库存/空位guard提供可见文字状态，避免静默返回。仅修改客户端目标BIG和新发布层/工程记录，不改后台热包、价格、头像、强化或存档；完整guards/policies、双锁、最新基线备份/CAS及游玩保护继续保留。"
          "证据见D:/fifaol3/random-pack-click-fix-v2/client；未操作游戏GUI，实际点击仍需以本次运行证据验收，不用真实测试卡或余额造验证。\r\n")
source=source[:start]+'        addition='+repr(addition)+'\n'+source[end:]
ast.parse(source)
(ROOT/'install.py').write_text(source,encoding='utf8')
for name in ('test_installer.py','handback.py'):
    data=(OLD/name).read_text('utf8').replace('random-pack-click-fix','random-pack-click-fix-v2')
    ast.parse(data)
    (ROOT/name).write_text(data,encoding='utf8')
print('TIMELINE_NATIVE_BINDING_INSTALLER_READY')
