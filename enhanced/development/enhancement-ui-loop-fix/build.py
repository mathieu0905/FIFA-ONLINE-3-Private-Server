"""Restore convenience features and repair invalid new AVM2 loop headers."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent
BASE=W.parent/'enhancement-entry-fix'
for name in ('client_tools.py','test_install.py','verify_live.py'):(W/name).write_bytes((BASE/name).read_bytes())
sys.path.insert(0,str(W))
from client_tools import *
snapshot()
current_expected=('520499d9d750c75be886b8577f1bc77f99155a6fe689e340811aac2649eb7fdd','b33899370ed4a0b500f4350fe7b453628b1a3e1ac47578bbda0a7327042d15c5')
full_expected=('a5d0fd0d0d9e190602392b0f02f8b9f7799ee6c6bbb1ea7dd1ef8e3e4c3ea278','1d2f611d26cde0a07c0d71200aaa877c5c1a36710622e8547d828ff7eebb8815')
report={}
for name,ch,fh in zip(NAMES,current_expected,full_expected):
 assert sha(W/(name+'-baseline.big'))==ch,'Current resource changed; fresh merge required'
 source=BASE/(name+'.big');assert sha(source)==fh
 swf=(BASE/(name+'.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4
 current=(W/(name+'-baseline.swf')).read_bytes()
 assert all(x[2]==y[2] for x,y in zip(tags(swf,start,len(swf)),tags(current,start,len(current))) if x[0]!=82)
 member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 assert all(bigdir.read(source,n)==bigdir.read(W/(name+'-baseline.big'),n) for n,*_ in bigdir.entries(source) if n!=member)
 parts=[];changes=[]
 for kind,body,raw in tags(swf,start,len(swf)):
  if kind==82:
   head=body.index(b'\0',4)+1;a=ABC(body[head:]);classes={row[0] for row in a.A['cls']}
   target=30 if 'EnhanceControlPanel' in classes and '_preview' in a.A['mn'] else 89 if 'EnhancePlayerPanel' in classes and '_players' in a.A['mn'] else None
   if target is not None:
    code=a.A['body'][target]
    loops={t for at,end,op,ts in instructions(code) for t in (ts or []) if t<=at and code[t]!=0x09}
    assert len(loops)==1,(classes,target,loops)
    a.modify(target,{offset:b'\x09' for offset in loops})
    updated=a.output();b=ABC(updated)
    assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig'] and not a.methods
    assert all(row['raw']==b.A['body_records'][mid]['raw'] for mid,row in a.A['body_records'].items() if mid!=target)
    newcode=b.A['body'][target]
    assert all(newcode[t]==0x09 for at,end,op,ts in instructions(newcode) for t in (ts or []) if t<=at)
    prefix=name if target==30 else 'EnhancePlayerPanel'
    (W/(prefix+'-before.abc')).write_bytes(body[head:]);(W/(prefix+'-after.abc')).write_bytes(updated)
    (W/(prefix+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    raw=tag(kind,body[:head]+updated);changes.append(dict(class_name=next(c for c in classes if c in ('EnhanceControlPanel','EnhancePlayerPanel')),method=target,loop_offsets=sorted(loops),opcode_added='label 0x09',all_other_method_records_identical=True))
  parts.append(raw)
 if name==NAMES[0]:
  assert len(changes)==2
  new=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
  pack_archive(source,W/(name+'.big'),{member:b'CFX'+new[3:8]+zlib.compress(new[8:],9)},[])
  (W/(name+'.swf')).write_bytes(new)
 else:
  assert not changes
  (W/(name+'.big')).write_bytes(source.read_bytes());(W/(name+'.swf')).write_bytes(swf)
  for suffix in ('-before.abc','-after.abc','-ABC.patch.json'):(W/(name+suffix)).write_bytes((BASE/(name+suffix)).read_bytes())
 report[name]=dict(source_sha256=ch,sha256=sha(W/(name+'.big')),restored_full_feature_source_sha256=fh,changes=changes,non_abc_resources_and_archive_members_preserved=True,native_verified=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
# The installer rebinds the actual current top under both shared locks.
installer=(BASE/'install.py').read_text('utf8')
for old,new in [('enhancement_entry_fix_preflight','enhancement_ui_loop_fix_preflight'),('enhancement-entry-fix','enhancement-ui-loop-fix'),('ENHANCEMENT_ENTRY_FIX','ENHANCEMENT_UI_LOOP_FIX')]:installer=installer.replace(old,new)
begin=installer.index("    note='");end=installer.index('    payload=[]',begin)
note='\n\nFO3-ENHANCEMENT-UI-LOOP-FIX（2026-11-07，恢复全部便捷功能，原生游戏入页待验收）\n真实Redtamarin AS3虚拟机对失败版本的control.updateBoostItemList30稳定报VerifyError #1021，稳定旧版不报；新增循环回跳目标没有label opcode0x09，且没有预先的前向分支目标帧。Adobe AVMplus Verifier::checkTarget明确拒绝这种回跳。上一轮局部VM/栈高度校验没有这个规则，导致漏检；不能再以它们代替真实虚拟机验证。\n恢复entry-fix完整功能资源，仅在control30强化券恢复循环和owner89双卡搜索循环的回跳入口各插入一个0x09 label并重定位分支。其余方法/类traits/签名和所有非ABC资源逐字节保留；无新增闭包或方法，原生确认仍保留，额外费用弹窗继续免除。选项记忆、受保护失败后同一主副卡恢复、新鲜预览、锁/等级/库存检查均恢复。后台概率/身价/保护和真实资产不写入/不回退。\n工程证据D:/fifaol3/enhancement-avm-check及enhancement-ui-loop-fix。真实AVM校验使用隔离的外部UI依赖桩，不等同游戏内页面和比赛验收；正式输入安装沿用最新父层guards/policies、双锁、备份/CAS，游戏运行时延期，不停服/不操作游戏GUI。\n'
installer=installer[:begin]+'    note='+repr(note)+".encode('utf8')\n"+installer[end:]
# Require the independent real-AVM comparison too, not only the custom VM.
installer=installer.replace("    build=read(W/'client-build.json');tests=read(W/'client-tests.json')", "    build=read(W/'client-build.json');tests=read(W/'client-tests.json')\n    assert read(W/'real-avm-tests.json')['status']=='PASS'")
(W/'install.py').write_text(installer,encoding='utf8')
print(json.dumps(report))
