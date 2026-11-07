from pathlib import Path
import sys,json
O=Path(__file__).parent;D=O/'entry-font-v4'
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work')
sys.path.insert(0,str(W/'experience_native_fix'));sys.path.insert(0,str(W/'experience_levels'))
from avm_patch import ABC
src=(W/'experience_levels/test_client.py').read_text('utf8').split('module=ABC')[0]
src=src.replace('elif op==0x09:pass','elif op in (0x02,0x09):pass')
src=src.replace('   elif op==0x55:', '''   elif op==0x4a:
    key=propname();n=r.u30();argv=[s.pop() for _ in range(n)][::-1];obj=s.pop();s.append(self.get(obj,key)(*argv))
   elif op==0x55:''')
ns={'__file__':str(__file__)};exec(compile(src,'<entry font actual-bytecode replay>','exec'),ns)
r=json.loads((D/'build.json').read_text('utf8'));VM=ns['VM']
old=ABC((O/'batch-text-v3/page.swf').read_bytes()[0x11186:]);new=ABC((D/'page.swf').read_bytes()[0x11186:])
results=[]
for missing in (None,{}, {'player':None},{'player':{}}):
    owner={'selectedPlayerInfo':missing};field={}
    try:VM(old,owner).run(5,start=r['start'],stop=r['end'],locals={5:field});raise AssertionError('old dependency unexpectedly succeeded')
    except (AssertionError,TypeError) as e:
        assert str(e)!='old dependency unexpectedly succeeded'
    field={};VM(new,owner,{'TextFormat':lambda font,size,color:dict(font=font,size=size,color=color)}).run(5,start=r['start'],stop=r['end'],locals={5:field})
    assert field['defaultTextFormat']==dict(font='$NormalFont',size=14,color=0xffffff)
    results.append(str(missing))
(D/'early-font-regression.json').write_text(json.dumps(dict(status='PASS',old_fails_new_passes=results,native_pass=False,scope='Only actual injected font initialization; constructor/render mocked'),indent=2),'utf8')
print('PASS: four empty/unready player-detail states; old font chain fails, new independent initialization succeeds')
