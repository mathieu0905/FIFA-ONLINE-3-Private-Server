"""Derive the already-regressed file transaction for the IM hierarchy revision."""
from pathlib import Path
import hashlib
R=Path(__file__).resolve().parent
OLD=Path(r'D:\fifaol3\im-balance30')
DOC='''

FO3-IM-HIERARCHY22-002（2026-11-07，im-role-hierarchy-plus22-v2）
用户纠正：IM+10不应压过其它赛季+20，但应强于+18；IM内部也应有合理强弱，允许以整体同档趋势而非逐人同卡严格限制为准。本层替代此前+30；不通过修改旧回执或恢复旧数据库实现。
123张现有IM按当前本地FC ICON(12)共同来源的overallrating分档，同档再按IM原位置的加权能力排序。内部参考是本地游戏设计数据，不冒称客观足球历史排名。按同位置排序后的其它赛季同档基线配对，IM底板领先21..23点（中心22）；最高参考档+23，中档+22，低档+21。较高参考档不低于较低档。
33项属性使用本人ICON的同一份属性形状再作等幅移位；当前IM的playerid、位置、模型、身体、花式、逆足、特性及所有非能力字段保持。原平衡记录嵌入prior_balance留痕。其它赛季与数据库其它表逐行保持，BIG只替换UI SQLite成员，原生身份/模型/Lua/语言及非目标成员原压缩字节保持。
同等级、同位置、同排名档次，双方满强化套、IM触发11人额外加成时：IM+10（24+7+5）对普通+18（40+15）领先2..4点，对普通+20（44+17）落后2..4点。未计各队原俱乐部/国家/特殊套差异，不保证每个同人比较，更不以OVR证明实机手感。
发布沿用最新父层全部guards/receipt policies、共同双锁、保护停服、新资产快照、备份/CAS、独立player_import及正式完整证书。游戏运行即延后，不自动强退、停服、改资源或使用游戏GUI，不改变真实卡/经验/强化/余额/库存/球队/阵容、价格/成交历史、强化概率或套装规则。
验证：123卡×33项与28位置、全部同位置参考档排序、同档+18/+20边界、五组主要排序、有序BIG/非目标字节、全表差异、双端回读及player_import --full。正式安装/接口/服务/热包/资产验收看D:/fifaol3/im-balance22/installed-handback.json；工作产物及延期不代表正式生效，原生/比赛/半场/换人仍待验证。
'''
def main():
    source=(OLD/'install.py').read_text('utf8')
    assert hashlib.sha256(source.encode()).hexdigest()=='b07fffaacbbff7e00808c07d14ae477896d59df665b598f588004cbc8d6c713f'
    start=source.index("DOC_ENTRY='''");end=source.index("\n'''",start)+4
    source=source[:start]+"DOC_ENTRY="+repr(DOC)+source[end:]
    source=source.replace('im-balance30','im-balance22').replace('im_balance30_','im_balance22_').replace('INSTALLED_IM_BALANCE30','INSTALLED_IM_HIERARCHY22').replace('IM_BALANCE30_PREFLIGHT_PASS','IM_HIERARCHY22_PREFLIGHT_PASS')
    # The fresh data plan remains identical; only the reviewed revision/report changes.
    source=source.replace("assert b'FO3-IM-BALANCE30-001' not in doc", "assert b'FO3-IM-HIERARCHY22-002' not in doc")
    source=source.replace("base_rating_range=[p['build']['base_min'],p['build']['base_max']],highlights=p['build']['highlights'],",
        "base_rating_range=p['build']['base_range'],rank_pairs=json.loads((R/'installed-tests.json').read_text('utf8'))['rank_pairs'],comparison_scope=p['build']['comparison_scope'],im10_vs_peer18_range=p['build']['im10_vs_peer18_range'],im10_vs_peer20_range=p['build']['im10_vs_peer20_range'],")
    assert "p['build']['base_min']" not in source and "p['build']['highlights']" not in source
    source=source.replace("if __name__=='__main__':main()",'''if __name__=='__main__':
    try:main()
    except RuntimeError as exc:
        if str(exc)!='更新已延后，当前游戏继续运行':raise
        save(R/'pending-handback.json',dict(status='DEFERRED_GAME_RUNNING',reason=str(exc),formal_files_written=False,services_restarted=False,state_shop_written=False,game_gui_used=False,latest_build=str(R/'latest-build.json')))
        print(str(exc),flush=True)
''')
    compile(source,'install.py','exec');(R/'install.py').write_text(source,'utf8')
    tests=(OLD/'test_install.py').read_text('utf8')
    compile(tests,'test_install.py','exec');(R/'test_install.py').write_text(tests,'utf8')
    print('Prepared hierarchy installer; no official files or services touched')
if __name__=='__main__':main()
