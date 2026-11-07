"""Narrow entry-crash repair: native TextField controls replace dynamic skin constructors.

The failing 2555 artifact and all previous evidence remain intact. This avoids three
new timeline/CLIK button instances during page initialization and uses MouseEvent
click plus TextField.mouseEnabled, while retaining one bound quantity calculation.
"""
from pathlib import Path
O=Path(__file__).parent
source=(O/'build_batch_bound.py').read_text('utf8')
source=source.replace("OUT=Path(__file__).parent/'batch-bound-v1'","OUT=Path(__file__).parent/'batch-text-v2'")
needle="defs=old[old.index('lex,owner,capsule,field='):old.index(\"g=b.bigdir.read(ORIGINAL\")]"
prep='''
old=old.replace("field(c,name);c.op(0x26 if enabled else 0x27).set('enabled')", "field(c,name);c.op(0x26 if enabled else 0x27).set('mouseEnabled')")
old='\\n'.join(line.replace(".set('enabled')", ".set('mouseEnabled')") if ("field(c,'fo3Exp" in line or 'field(locked,control)' in line) else line for line in old.split('\\n'))
at=old.index('def add_button(');end=old.index('# Reuse the reviewed base patch machinery;',at)
replacement="""def add_button(c,name,label,width,xoff,callback,repeat=False):
    b.add_text(c,name,label,width,28,xoff,-36,False)
    for key in ['border','background']:c.local(5).op(0x26).set(key)
    c.local(5).number(0x172633).set('backgroundColor')
    c.local(5).number(0xffce35).set('borderColor')
    c.local(5).op(0x27).set('mouseEnabled')
    c.local(5).string('click').op(0x40,callback).call('addEventListener',2).op(0x29)

"""
old=old[:at]+replacement+old[end:]
'''
assert needle in source;source=source.replace(needle,prep+'\n'+needle)
old="source=Path('D:/FO3ID/32795/data/ui/TeamManagementExpCapsuleScreen.big')"
new="source=Path('D:/FO3ID/server/backups/xp30-batch-module-20261106-145705-239491/6.backup')"
assert old in source;source=source.replace(old,new)
source=source.replace('target=OUT/source.name',"target=OUT/'TeamManagementExpCapsuleScreen.big'")
exec(compile(source,'<batch TextField entry repair>','exec'),{'__file__':str(O/'build_batch_text.py')})
