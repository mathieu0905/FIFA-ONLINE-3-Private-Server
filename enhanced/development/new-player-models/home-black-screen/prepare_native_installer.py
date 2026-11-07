"""Reuse the verified streaming transaction with a fresh native-roster child layer."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'install_bellingham_impact.py').read_text('utf8')
s=s.replace('bellingham_impact_preflight.py','native_roster_preflight.py').replace('bellingham-impact','native-roster').replace('BELLINGHAM_IMPACT','NATIVE_ROSTER').replace('Bellingham-Impact','Native-Roster')
s=s.replace("build=json.loads((R/'native-roster/archive-build.json').read_text('utf8'))", "buildrow=json.loads((R/'native-roster/build.json').read_text('utf8'));build=dict(files=[buildrow])")
s=s.replace("S/'patches/sql_http_preflight.py'", "S/'patches/bellingham_impact_preflight.py'")
# Source now refers to the current Impact layer. Transform its own constants,
# retaining every required member/receipt policy in the inherited composition.
start=s.index('        source=source.replace(')
end=s.index('        compile(source,SELF',start)
s=s[:start]+'''        source=source.replace('bellingham-impact','native-roster').replace('bellingham_impact_preflight.py','native_roster_preflight.py').replace('BELLINGHAM_IMPACT','NATIVE_ROSTER').replace('Bellingham-Impact','Native-Roster')
        assert 'native-roster-installed.json' in source and 'data/data_0.big' in source
'''+s[end:]
start=s.index('        note=(');end=s.index('        small={',start)
s=s[:start]+'''        note=('\\n\\nFO3-001 / FO3-UI-NAMES 原生球员库续（'+revision+'）：\\n'
          '实机失败：用户确认前一层能进入首页，切换贝林仍黑屏卡死；01:20:32只读dump PID85916保留，01:20:42 CLIENT_CRASH。骨骼转换未解决此崩溃，不能再据静态mesh校验声称原生修复通过。\\n'
          '确认根因路径：崩溃线程保存EXCEPTION_POINTERS=45b44a9c，record C0000005，EIP008fd780，读地址4，EAX0。原生查询解析器当前token=trainingteamplayers，条件playerid=252371；数据库符号表24表中无此表。原生902b40先SELECT players WHERE playerid，空返回后902bcb走trainingteamplayers并在表符号查找空指针崩溃。当前data/db/fifa_ng_db.db的players62081条确实没有贝林，前序只加SQLite/名字/模型不完整。静态函数解码与真实dump逐项对应；不依赖误导性的最近导出符号名。\\n'
          '本次只在EA二进制库players追加贝林真实记录，全部102字段逐项编码、位宽/范围/回读验证；整数按meta rangelow偏移，float按IEEE32，日期按EA Gregorian编码（32483条原生生日与SQLite匹配）。原生headtype13bit容不下UI保留30001选择器，原生用正常专属头规则headtype1023/headclass0/headasset252371，直接指向贝林原模型；UI主库与Lua映射保持原样。未用姆巴佩外貌/能力替代贝林，仅借有效原生record布局模板且全部字段覆盖。\\n'
          '原62081条raw record逐字节相同，所有其他EA表逐字节相同，players只增1条；修复表与文件CRC、RefPack回读通过。data0按原目录顺序重建，271条成员中270条原压缩payload及size/usize全部相同，正式check_data0_layout PASS。只改data0/新gate/play/本条账本，Module/三份贝林已转换网格/SQLite/语言库/真实state与shop不改，无服务重启。\\n'
          '证据D:/fifaol3/new-player-models/home-black-screen/native-roster/{build.json,crash-evidence.json}与native-roster-installed.json。回归正式patches/native_roster_preflight.py、tools/check_data0_layout.py --changed-member data/db/fifa_ng_db.db --baseline 本次data0备份；原生首页切贝林及比赛仍PENDING。其余8个原缺失球员同样未入EA库，此轮不盲目批量加入：例如部分源skillmoves5越过原生0..4语义范围，需后续逐项转换，不能宣称全部新增球员通过。\\n')
'''+s[end:]
s=s.replace("C/'data/data_0.big',S/'gamedata/shop.json'", "C/'data/ui/libs/Module.big',C/'data/data_4.big',C/'data/data_6.big',S/'gamedata/shop.json'")
assert "payloads={Path(f['target']):Path(f['payload']) for f in build['files']}" in s
assert "source=(S/'patches/bellingham_impact_preflight.py')" in s
assert "C/'data/data_0.big'" not in s
compile(s,'install_native_roster.py','exec')
(R/'install_native_roster.py').write_text(s,encoding='utf8')
print('Native installer ready')
