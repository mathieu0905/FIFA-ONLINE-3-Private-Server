"""Derive the existing verified IM resource pipeline for base-5 and feature doubling."""
from pathlib import Path
R=Path(__file__).resolve().parent;OLD=Path(r'D:\fifaol3\im-balance22')
DOC='''

FO3-IM-BASEMINUS5-003（2026-11-07，im-base-minus5-feature-double-v3）
用户要求IM基础能力再降5，并提高传奇时刻额外套装。仅现有123张84赛季卡的33项能力在本次最新值上各减5；内部排序、属性差、身份/位置/身体/模型/花式/逆足/特性保持，所有非IM及其它表保持，不从旧版本整包覆盖。
独立feature额外套：3..5人由2→4、6..8人3→6、9..10人4→8、11人5→10；不足3人仍无额外加成。同步服务端常量和说明，沿用原独立叠加及首发去重/替补排除，不改其它套装与强化成长。
相对上一层：单卡少5；3..5人套后的IM净少3，6..8人少2，9..10人少1，11人套净能力保持。非IM不会获得额外feature。满套同等级同位置同档次的IM+10仍比其它赛季+18高2..4、比+20低2..4；未计俱乐部/国家/特殊套差异，数值检验不等于实机手感。
DB与客户端BIG/UI同步，BIG非目标成员原压缩字节、原生EA身份/模型/Lua/语言保持；注册表保留prior_balance及新前后行哈希，更新正式完整player_import证书。真实state/shop不写，资产快照以本次停服时最新进度核对。
安装沿用fresh最新父层全部guards/receipt policies、共同双锁、游戏保护/正式停服、备份/CAS和入口最后切换。游戏运行即延期不强退/GUI。正式状态、组合API、三元组哈希、全资源/123卡接口/feature分档/服务热包及资产验收见D:/fifaol3/im-base-minus5/installed-handback.json。原生比赛/半场/换人仍待实机验证。
'''
HTTP_HELPER='''
def patched_http(source):
    old='TC_MOMENTS_GROUPS = _tc_groups((3, 5, 2), (6, 8, 3), (9, 10, 4), (11, 11, 5))'
    new='TC_MOMENTS_GROUPS = _tc_groups((3, 5, 4), (6, 8, 6), (9, 10, 8), (11, 11, 10))'
    assert source.count(old)==1,'Fresh feature tiers changed; review before overwrite'
    source=source.replace(old,new)
    old='首发传奇时刻球员3–5人+2、6–8人+3、9–10人+4、11人+5；与原有套装及强化套叠加'
    new='首发传奇时刻球员3–5人+4、6–8人+6、9–10人+8、11人+10；与原有套装及强化套叠加'
    assert source.count(old)==1
    source=source.replace(old,new);compile(source,'http_config.py','exec');return source
'''
def main():
    source=(OLD/'build.py').read_text('utf8')
    source=source.replace("REVISION='im-role-hierarchy-plus22-v2'","REVISION='im-base-minus5-feature-double-v3'")
    at=source.index('\ndef build():');source=source[:at]+HTTP_HELPER+source[at:]
    source=source.replace('            advantage=22+tier_bonus\n            target=int(num(peer,w)//100)+advantage\n            shift=target-int(num(ref,w)//100)\n            after={**p,**{k:ref[k]+shift for k in FIELDS}}',
        '            target=int(num(p,w)//100)-5\n            advantage=target-int(num(peer,w)//100)\n            shift=target-int(num(ref,w)//100)\n            after={**p,**{k:p[k]-5 for k in FIELDS}}')
    assert 'after={**p,**{k:p[k]-5 for k in FIELDS}}' in source
    source=source.replace('full_im10_vs_peer18=advantage-19,full_im10_vs_peer20=advantage-25',
                          'full_im10_vs_peer18=advantage-14,full_im10_vs_peer20=advantage-20')
    source=source.replace("policy='Common ICON profile and hierarchy; rank-matched same-role power curve +21..23; full-set IM10 beats peer18 by2..4 and loses peer20 by2..4; never claim each same-player pair; metadata/identity/models unchanged.'",
        "policy='Latest current IM 33 stats minus5, internal hierarchy retained; feature tiers doubled to4/6/8/10, full XI offsets base reduction. Same-role rank full IM10 beats peer18 by2..4 and loses peer20 by2..4; metadata/identity/models unchanged.'")
    marker="    save(out/'custom_rosters.json',registry);save(out/'changes.json',result)"
    assert source.count(marker)==1
    source=source.replace(marker,marker+"\n    (out/'http_config.before.py').write_bytes(paths[3].read_bytes())\n    (out/'http_config.py').write_text(patched_http(paths[3].read_text('utf8')),'utf8')")
    source=source.replace("'changes.json','rankings.json')","'changes.json','rankings.json','http_config.py')")
    source=source.replace("Same position and rank/tier, full grade sets and full IM feature; not same-person pairs. Same level and exclude original club/nation/special set differences.",
                          "Same position and rank/tier, full grade sets and full IM feature10; not same-person pairs. Same level and exclude original club/nation/special set differences.")
    compile(source,'build.py','exec');(R/'build.py').write_text(source,'utf8')
    installer=(OLD/'install.py').read_text('utf8')
    start=installer.index('DOC_ENTRY=');end=installer.index('\n@contextmanager',start)
    installer=installer[:start]+'DOC_ENTRY='+repr(DOC)+installer[end:]
    installer=installer.replace('im-balance22','im-base-minus5').replace('im_balance22_','im_base_minus5_').replace('INSTALLED_IM_HIERARCHY22','INSTALLED_IM_BASEMINUS5').replace('IM_HIERARCHY22_PREFLIGHT_PASS','IM_BASEMINUS5_PREFLIGHT_PASS')
    installer=installer.replace("assert b'FO3-IM-HIERARCHY22-002' not in doc","assert b'FO3-IM-BASEMINUS5-003' not in doc")
    old="payloads.update({S/DOC:doc+DOC_ENTRY.encode('utf8'),S/gate:helper.encode('utf8'),S/'play-local.bat':play.replace(matches[0],gate.replace('/','\\\\').encode())})"
    assert installer.count(old)==1
    installer=installer.replace(old,old+"\n    payloads[S/'http_config.py']=(out/'http_config.py').read_bytes()")
    marker="    assert definitions[60084]['type']=='feature' and definitions[10120]['boostgroups'][0]['boosts'][0]['amount']==17"
    assert installer.count(marker)==1
    installer=installer.replace(marker,marker+"\n    assert [(g['count_min'],g['count_max'],g['boosts'][0]['amount']) for g in definitions[60084]['boostgroups']]==[(3,5,4),(6,8,6),(9,10,8),(11,11,10)]")
    installer=installer.replace("base_rating_range=p['build']['base_range'],", "feature_tiers=[[3,5,4],[6,8,6],[9,10,8],[11,11,10]],base_rating_range=p['build']['base_range'],")
    compile(installer,'install.py','exec');(R/'install.py').write_text(installer,'utf8')
    tests=(OLD/'test_install.py').read_text('utf8')
    tests=tests.replace("server/'doc':b'newdoc',", "server/'doc':b'newdoc',server/'http_config.py':b'new-http-code',")
    tests=tests.replace('for failure in (None,*range(1,10)):', 'for failure in (None,*range(1,11)):')
    compile(tests,'test_install.py','exec');(R/'test_install.py').write_text(tests,'utf8')
    print('Prepared code/resource transaction without formal writes')
if __name__=='__main__':main()
