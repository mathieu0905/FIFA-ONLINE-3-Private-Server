from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;BASE=W.parent/'enhancement-ui-loop-fix'
for name in ('client_tools.py','test_install.py','verify_live.py'):(W/name).write_bytes((BASE/name).read_bytes())
sys.path.insert(0,str(W))
from client_tools import *
snapshot()
report={}
for name,expected in zip(NAMES,('1bc2ff1e50e5ba7dd74462295e0846fc13b5bcb370bf3c3ce498ab8cd5b22a44','1d2f611d26cde0a07c0d71200aaa877c5c1a36710622e8547d828ff7eebb8815')):
 source=W/(name+'-baseline.big');assert sha(source)==expected,'Fresh merge required'
 swf=(W/(name+'-baseline.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];changed=False
 for kind,body,raw in tags(swf,start,len(swf)):
  if kind==82 and name==NAMES[0]:
   head=body.index(b'\0',4)+1;a=ABC(body[head:])
   if any(c[0]=='EnhanceControlPanel' for c in a.A['cls']) and '_preview' in a.A['mn']:
    assert not changed;changed=True
    before=body[head:];good=ABC(Path('D:/fifaol3/enhancement-remember/TeamManagementPlayerEnhancementTabPage-before.abc').read_bytes())
    assert all(a.values[k][:len(good.values[k])]==good.values[k] for k in range(7))
    mid=45;a.A['body'][mid]=good.A['body'][mid];a.A['body_records'][mid]=good.A['body_records'][mid]
    # This is a lexical event closure. local0 is its call receiver, NOT the
    # control panel. The already-validated currentTarget is the actual button.
    c=Code(a).local(2).local(2).prop('selected').op(0x76).set('fo3RememberProtection')
    at=next(int(line.split(':',1)[0]) for line in dis(a.A,a.A['body'][mid]) if 'findpropstrict requestPreview' in line)
    a.modify(mid,{at:c.done()});updated=a.output();b=ABC(updated)
    assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig']
    assert all(r['raw']==b.A['body_records'][i]['raw'] for i,r in ABC(before).A['body_records'].items() if i!=45)
    (W/(name+'-before.abc')).write_bytes(before);(W/(name+'-after.abc')).write_bytes(updated)
    (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    raw=tag(kind,body[:head]+updated)
  parts.append(raw)
 if name==NAMES[0]:
  assert changed
  new=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
  member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
  pack_archive(source,W/(name+'.big'),{member:b'CFX'+new[3:8]+zlib.compress(new[8:],9)},[])
  (W/(name+'.swf')).write_bytes(new)
 else:
  (W/(name+'.big')).write_bytes(source.read_bytes());(W/(name+'.swf')).write_bytes(swf)
 report[name]=dict(source_sha256=expected,sha256=sha(W/(name+'.big')),changed_methods=[45] if changed else [],other_method_records_traits_signatures_preserved=True,native_game_verified=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
installer=(BASE/'install.py').read_text('utf8')
for old,new in [('enhancement_ui_loop_fix_preflight','enhancement_protection_click_fix_preflight'),('enhancement-ui-loop-fix','enhancement-protection-click-fix'),('ENHANCEMENT_UI_LOOP_FIX','ENHANCEMENT_PROTECTION_CLICK_FIX')]:installer=installer.replace(old,new)
begin=installer.index("    note='");end=installer.index('    payload=[]',begin)
note='\n\nFO3-ENHANCEMENT-PROTECTION-CLICK-FIX（2026-11-07）\n实机17:23:35 telemetry/ui/errors报告TypeError #1006 getChildByName is not a function at method45：勾选先切换成功，新增偏好记忆代码把事件闭包local0误当control，记忆写入/新保护preview中断。只修正45：使用原生回调已取得并校验的event.currentTarget(local2)记录fo3RememberProtection；保持原生词法requestPreview查找，禁止用闭包receiver找面板。其它方法、类traits/签名、全部便捷记忆与双卡重选及循环label修复、概率/身价/保护后端均保留。\n真实AVM诊断以原生init作用域创建45闭包，用独立事件receiver实际分发：旧方法复现#1006，新方法连续勾选/取消并保存偏好、标记同步、每次一次新preview；禁用或无双卡不发请求。外部UI依赖为桩，仍不冒称游戏内结果已验证。工程证据D:/fifaol3/enhancement-protection-click-fix；游戏运行则在锁及正式写入前延期，不停服/强退/操作GUI。安装fresh最新父层全部guards/policies、备份/CAS，真实state/shop不写入。\n'
installer=installer[:begin]+'    note='+repr(note)+".encode('utf8')\n"+installer[end:]
(W/'install.py').write_text(installer,encoding='utf8')
print(json.dumps(report))
