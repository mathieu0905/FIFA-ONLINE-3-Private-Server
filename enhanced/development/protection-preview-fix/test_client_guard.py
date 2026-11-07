from pathlib import Path
import sys,json
R=Path(__file__).parent
sys.dont_write_bytecode=True
sys.path.insert(0,r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
s=Path(r'D:\fifaol3\enhancement-protection40\test_client.py').read_text('utf8')
ns={};exec(compile(s[:s.index('def load(name):')],'<client-replay-runtime>','exec'),ns)
a=ns['ABC']((R/'current-control.swf').read_bytes()[0x246ff:])
for reason in ('PROTECTION_NOT_REQUIRED','INVALID_PARAM','RESTORE_OTHER_MANAGER'):
 label='无需保护；请改选“不用”。本次没有扣费或消耗材料。'
 panel={'_preview':dict(result=True,grade=9,levelinfo=dict(level=1,exp=0,to=100),price=0,probability=100,enhancepay=0,needes=90,
  protection=dict(blocked=True,available=False,reason=reason,label=label,fee=0,total_ep=0))}
 vm=ns['VM'](a,panel);vm.run(20,start=7)
 assert not vm.puts and len(vm.dialogs)==1 and vm.dialogs[0]['message']==label
 assert 'buttonHandler' not in vm.dialogs[0]
report=dict(status='PASS',actual_current_client=True,cases=3,nonpayable_preview_click_emits_zero_requests=True,dialog_preserves_server_reason=True,native_game_verified=False)
(R/'client-guard-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
