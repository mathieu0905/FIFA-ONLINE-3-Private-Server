"""Revert only the failed convenience UI patches; retain native-confirm fee bypass."""
from pathlib import Path
import json, sys
sys.dont_write_bytecode = True
W = Path(__file__).resolve().parent
OLD = W.parent / 'enhancement-entry-fix'
STABLE = W.parent / 'enhancement-remember'
for name in ('client_tools.py', 'test_install.py', 'verify_live.py'):
    (W/name).write_bytes((OLD/name).read_bytes())
sys.path.insert(0, str(W))
from client_tools import *
snapshot()
expected = ('a5d0fd0d0d9e190602392b0f02f8b9f7799ee6c6bbb1ea7dd1ef8e3e4c3ea278', '1d2f611d26cde0a07c0d71200aaa877c5c1a36710622e8547d828ff7eebb8815')
good = ('520499d9d750c75be886b8577f1bc77f99155a6fe689e340811aac2649eb7fdd', 'f6c6510221841f0bf7dc29aed19868d716228bf9017bfe47bf4a6b9aeb3990b8')
report = {}
for name, current_hash, stable_hash in zip(NAMES, expected, good):
    assert sha(W/(name+'-baseline.big')) == current_hash, 'Fresh merge required; never replace another owner edit'
    source = STABLE/(name+'-baseline.big')
    assert sha(source) == stable_hash
    member = next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    gfx = bigdir.read(source, member)
    swf = b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
    start = 8+(5+4*(swf[8]>>3)+7)//8+4
    current = (W/(name+'-baseline.swf')).read_bytes()
    # Recent edits were exclusively ABC. Retain every image/layout/archive member.
    before_tags = list(tags(current, start, len(current)))
    stable_tags = list(tags(swf, start, len(swf)))
    assert len(before_tags) == len(stable_tags)
    assert all(x[2] == y[2] for x,y in zip(before_tags,stable_tags) if x[0] != 82)
    for n,*_ in bigdir.entries(source):
        if n != member: assert bigdir.read(source,n) == bigdir.read(W/(name+'-baseline.big'),n)
    if name == NAMES[0]:
        (W/(name+'.big')).write_bytes(source.read_bytes())
        (W/(name+'.swf')).write_bytes(swf)
        report[name] = dict(source_sha256=current_hash, sha256=sha(source), exact_successful_ui_restored=True)
        continue
    import importlib.util
    spec=importlib.util.spec_from_file_location('fee_bypass',STABLE/'client_patch.py')
    patcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(patcher)
    parts=[];found=False
    for kind,body,raw in stable_tags:
        if kind == 82:
            head=body.index(b'\0',4)+1;a=ABC(body[head:])
            if any(c[0]=='TeamManagementPlayerEnhancingPopupScreen' for c in a.A['cls']) and 'boostInfoPanel' in a.A['mn']:
                assert not found;found=True
                original=body[head:];patcher.popup_patch(a);updated=a.output();b=ABC(updated)
                assert set(a.changed)=={33} and not a.methods
                assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig']
                assert all(row['raw']==b.A['body_records'][mid]['raw'] for mid,row in a.A['body_records'].items() if mid!=33)
                for suffix,data in (('-before.abc',original),('-after.abc',updated)):(W/(name+suffix)).write_bytes(data)
                (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
                raw=tag(kind,body[:head]+updated)
        parts.append(raw)
    assert found
    new=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
    pack_archive(source,W/(name+'.big'),{member:b'CFX'+new[3:8]+zlib.compress(new[8:],9)},[])
    (W/(name+'.swf')).write_bytes(new)
    report[name]=dict(source_sha256=current_hash,sha256=sha(W/(name+'.big')),only_method_33_changed_from_successful_ui=True,all_native_traits_signatures_and_other_methods_identical=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
# Reuse the bounded, tested official-resource transaction, fresh-parent composition.
installer=(OLD/'install.py').read_text('utf8')
for old,new in [('enhancement_entry_fix_preflight','enhancement_ui_stabilize_preflight'),('enhancement-entry-fix','enhancement-ui-stabilize'),('ENHANCEMENT_ENTRY_FIX','ENHANCEMENT_UI_STABILIZE')]:installer=installer.replace(old,new)
start_note=installer.index("    note='");end_note=installer.index("    payload=[]",start_note)
note='\n\nFO3-ENHANCEMENT-UI-STABILIZE（2026-11-07，原生入页仍待验收）\n16:55:40 PE2STATICVALUES后无preview；用户截图证明上一轮入口修正仍失败，不能称已修复。撤下当前聊天新增的选项记忆/双卡自动重选实现，Tab完整回到15:41成功强化的520499d9 UI；Popup回到f6c65102基础，仅保留method33的原生确认后免额外保护费弹窗。没有新增类成员/词法闭包；保留原独立保护、数值概率及字体修正。概率/身价/40%双卡保护后端均不回退。选项记忆和双卡自动重选暂不可用；今后须完成原生加载验证才重新交付，不以自制VM通过代替。\n所有非ABC资源及其它BIG成员与当前版本逐字节一致，原生确认回放验证有签名非阻塞报价仅发一次PUT，仍携带新鲜token；异常报价不绕过收费确认。根因未确证，当前只是撤销回归范围内改动，不能宣称实机已恢复。安装沿用最新父层全guards/receipt policies、双锁、备份/CAS；真实state/shop不写入/不恢复、不停服/不操作GUI，游戏运行则延期。证据D:/fifaol3/enhancement-ui-stabilize。\n'
installer=installer[:start_note]+'    note='+repr(note)+".encode('utf8')\n"+installer[end_note:]
(W/'install.py').write_text(installer,encoding='utf8')
# Keep only reusable VM definitions and the relevant native-confirm regression.
test=(STABLE/'test_client.py').read_text('utf8')
pre=test[:test.index("a=ABC((W/")]
defs=test[test.index('def inject('):test.index('def own():')]
cases=test[test.index('for blocked,token,version,expected'):test.index('for name,abc,patch in ')]
tail="""
assert sha(W/(NAMES[0]+'.big')) == '520499d9d750c75be886b8577f1bc77f99155a6fe689e340811aac2649eb7fdd'
checks.append('Tab is byte-identical to the prior successfully used enhancement UI; no convenience additions remain')
checks.append('Non-ABC tags and other BIG members match current official UI; popup changes only Confirm33 from the successful baseline')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
"""
(W/'test_client.py').write_text(pre+"p=ABC((W/(NAMES[1]+'-after.abc')).read_bytes());pp=json.loads((W/(NAMES[1]+'-ABC.patch.json')).read_text());checks=[]\n"+defs+cases+tail,encoding='utf8')
stacks=(OLD/'test_stacks.py').read_text('utf8')
stacks=stacks[:stacks.index('results={}')]+"a=ABC((ROOT/('TeamManagementPlayerEnhancingPopupScreen-after.abc')).read_bytes())\nr=dict(status='PASS',method33=check(a,33),native_type_verifier_pass=False)\n(ROOT/'stacks.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))\n"
(W/'test_stacks.py').write_text(stacks,encoding='utf8')
print(json.dumps(report))
