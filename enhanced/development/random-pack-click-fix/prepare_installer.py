"""Reuse the guarded current-parent client transaction, with this fix's own evidence."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'random-pack-dual'
source=(OLD/'install.py').read_text('utf8')
source=source.replace('random-pack-dual','random-pack-click-fix').replace('RANDOM_PACK_DUAL','RANDOM_PACK_CLICK_FIX')
start=source.index('        addition=(')
end=source.index("        entry('server',doc,",start)
addition=("\r\n\r\nFO3-RANDOM-PACK-CLICK-FIX-001（2026-11-07）\r\n"
          "用户实机反馈一键全开不可点击且样式不一致。旧新增裸MovieClip仅监听click，未复用PlayerCardPackScreenAllButton/ButtonEx/CLIK的ButtonEvent及screen按钮管理链。原btnFive的PlaceObject3初始y=40，configUI回调17以TweenMax单独将原按钮移至y=0；旧新增按钮在draw只复制当时y且未参与该Tween，可能停在y=40，截图正好低约40像素且被底边裁切。"
          "本次复用与连续翻开相同的原生symbol/组件、受管理ButtonEvent事件与按钮使能链，去掉自绘图形/文字，使用原生皮肤和最终静止y=0，三按钮统一宽240；不增加新的入场动效链。保留单开、连续翻牌、批量请求和集中展示，服务端高强包业务与所有路由原样保留。"
          "不能用仅直接调用回调的mock测试替代真实按钮输入接线验证；需核对原生按钮类型/事件/命中范围及使能状态。"
          "测试和本次实际修复证据见D:/fifaol3/random-pack-click-fix/client。游戏运行时在正式写入前延期，不请求退出、不停服、不操作游戏GUI。"
          "仅fresh最新父层和目标资源，继承全部guards/policies，双锁/备份/CAS安装；不写state/shop，不回退其它聊天的高强包、模型或进度。实机效果待验收。\r\n")
source=source[:start]+'        addition='+repr(addition)+'\n'+source[end:]
ast.parse(source)
(ROOT/'install.py').write_text(source,encoding='utf8')
for name in ('test_installer.py','handback.py'):
    data=(OLD/name).read_text('utf8').replace('random-pack-dual','random-pack-click-fix')
    ast.parse(data)
    (ROOT/name).write_text(data,encoding='utf8')
print('GUARDED_CLICK_FIX_INSTALLER_PREPARED')
