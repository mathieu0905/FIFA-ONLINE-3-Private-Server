from pathlib import Path
R=Path(__file__).parent
s=Path(r'D:\fifaol3\enhancement-probability-ui\build.py').read_text('utf8')
a=s.index('def render(');b=s.index('\ndef control_patch(',a)
s=s[:a]+'''def render(a,base,container,preview,waiting=False,popup=False):
 c=Code(a)
 if popup:
  c.local(0).ownprop('boostInfoPanel').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('boostInfoContainer').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('boostRate').store(base)
 else:
  # This is the native success-rate bonus section, not the fee panel.
  c.local(0).ownprop('_owner').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('infoPanel').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('enhanceRate').store(base)
 c.local(base).jump(0x12,'done')
 # Reuse the original localized title and its existing CJK glyphs.
 c.local(base).string('__id15_' if popup else '__id7_').call('getChildByName',1).store(base+5)
 c.local(base+5).jump(0x12,'title_done')
 c.local(base+5).string('成功率').set('text')
 c.label('title_done')
 if popup:
  c.local(base).prop('rateContainer').store(base+5)
  c.local(base+5).jump(0x12,'done')
  c.local(base+5).op(0x27).set('visible')
 preview(c);c.store(base+1)
 c.local(base).string(NAME).call('getChildByName',1).op(0x80,a.name('TextField','flash.text')).store(base+2)
 c.local(base+2).jump(0x11,'have_field')
 c.op(0x5d,a.name('TextField','flash.text')).op(0x4a,a.name('TextField','flash.text'),0).store(base+2)
 c.local(base+2).string(NAME).set('name')
 for key in ('selectable','embedFonts','mouseEnabled','multiline','wordWrap'):c.local(base+2).op(0x27).set(key)
 c.op(0x5d,a.name('TextFormat','flash.text')).string('Arial').number(40 if popup else 24).number(0xf2c200).op(0x4a,a.name('TextFormat','flash.text'),3).store(base+5 if not popup else base+4)
 fmt=base+4 if popup else base+5
 c.local(fmt).string('center').set('align')
 c.local(base+2).local(fmt).set('defaultTextFormat')
 for key in ('border','background'):c.local(base+2).op(0x26).set(key)
 c.local(base+2).number(0x627580).set('borderColor')
 c.local(base+2).number(0x17232b).set('backgroundColor')
 c.local(base).local(base+2).call('addChild',1).op(0x29)
 c.label('have_field')
 if popup:
  c.local(base+2).local(base+5).prop('x').set('x')
  c.local(base+2).local(base+5).prop('y').number(15).op(0xa0).set('y')
  c.local(base+2).local(base+5).prop('width').set('width')
  c.local(base+2).number(70).set('height')
 else:
  for key,value in [('x',0),('y',36),('width',180),('height',40)]:c.local(base+2).number(value).set(key)
 c.string('...' if waiting else '-').store(base+3)
 c.local(base+1).jump(0x12,'set_text')
 c.local(base+1).prop('probability').store(base+4)
 c.local(base+4).op(0x95).string('number').jump(0x14,'set_text')
 c.op(0x5d,a.name('isFinite')).local(base+4).call('isFinite',1).jump(0x12,'set_text')
 c.local(base+4).number(0).op(0xad).jump(0x11,'set_text')
 c.local(base+4).number(100).op(0xaf).jump(0x11,'set_text')
 c.local(base+4).call('toString',0).string('%').op(0xa0).store(base+3)
 c.label('set_text').local(base+2).local(base+3).set('text')
 c.local(base+2).op(0x26).set('visible')
 c.label('done');return c.done()
''' +s[b:]
# Replace only the five display/clearing injections from the installed layer.
# Keep every original instruction, including all protection hooks.
s=s.replace("base=a.A['body_records'][mid]['fields'][1]\n  code=render", "row=json.loads((Path(r'D:\\fifaol3\\enhancement-probability-ui')/'TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())[str(mid)]\n  assert a.A['body'][mid]==bytes.fromhex(row['updated'])\n  a.A['body'][mid]=bytes.fromhex(row['original'])\n  base=a.A['body_records'][mid]['fields'][1]\n  code=render")
s=s.replace("mid=25;offset=len(a.A['body'][mid])-1;", "mid=25;row=json.loads((Path(r'D:\\fifaol3\\enhancement-probability-ui')/'TeamManagementPlayerEnhancingPopupScreen-ABC.patch.json').read_text())[str(mid)];assert a.A['body'][mid]==bytes.fromhex(row['updated']);a.A['body'][mid]=bytes.fromhex(row['original']);offset=len(a.A['body'][mid])-1;")
(R/'build.py').write_text(s,encoding='utf8')

