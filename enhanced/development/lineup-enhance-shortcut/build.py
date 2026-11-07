"""Incremental patch of current official GFx resources. No official writes."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,Code,R,u30,tags,tag,pack_archive,bigdir,dis,instructions
import avm_patch
W=Path(__file__).resolve().parent
ICON='fo3LineupEnhanceIcon'; REQUEST='fo3LineupEnhanceRequest'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def traits(data,cls,methods):
 src=avm_patch.SOURCE.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []').replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
 ns={'__name__':'trait_bounds'};exec(compile(src,'<bounds>','exec'),ns)
 a=ns['parse'](data,0);row=next(v for v in a['cls'] if v[0]==cls);bounds=[v for v in a['trait_records'] if v['values']==row[3]];assert len(bounds)==1
 b=bounds[0];r=R(data,b['start']);count=r.u30()
 addition=b''.join(u30(n)+b'\x01\x00'+u30(m) for n,m in methods)
 return data[:b['start']]+u30(count+len(methods))+data[r.p:b['end']]+addition+data[b['end']:]
def method(a,c,scope,locals):return a.add_method(c.done(),scope,local_count=locals)
def endcall(a,mid,name):
 end=next(at for at,_,op,_ in reversed(list(instructions(a.A['body'][mid]))) if op==0x47)
 a.modify(mid,{end:Code(a).local(0).op(0x20).call(name,1).op(0x29).done()})
def screen(c,local,done):
 c.local(0).prop('parent').store(local).label('parents')
 c.local(local).jump(0x12,done)
 c.local(local).string('teamManagementTab').call('hasOwnProperty',1).jump(0x11,'screen')
 c.local(local).prop('parent').store(local).jump(0x10,'parents').label('screen')

def renderer(a):
 scope=a.A['body_records'][28]['fields'][2];added=[]
 # Bound public callback reads the renderer's current data, including after recycling.
 c=Code(a).local(0).op(0x30).local(1).call('stopImmediatePropagation',0).op(0x29)
 c.local(0).prop('data').store(2);c.local(2).jump(0x12,'done')
 c.local(2).prop('id').jump(0x12,'done');screen(c,3,'done')
 c.local(3).string(REQUEST).call('getChildByName',1).store(4)
 c.local(4).jump(0x11,'carrier')
 c.lex('MovieClip','flash.display').op(0x42,0).store(4)
 c.local(4).string(REQUEST).set('name');c.local(4).op(0x27).set('visible')
 c.local(3).local(4).call('addChild',1).op(0x29)
 c.label('carrier')
 for key in ('id','spid','grade'):c.local(4).local(2).prop(key).set('fo3'+key)
 c.local(4).lex('getTimer','flash.utils').op(0x20).op(0x41,0).set('fo3time')
 c.local(3).prop('teamManagementTab')
 c.string('pageClassname').string('TeamManagementPlayerTabPage').op(0x55,1)
 c.string('tabname').string('playerSettingTab').string('pageClassname').string('TeamManagementPlayerEnhancementTabPage').op(0x55,2)
 c.op(0x56,2).call('switchTabPage',1).op(0x29).label('done').op(0x47)
 click=method(a,c,scope,5);added.append((a.name('fo3LineupEnhanceClick'),click))
 # Create an independent vector button, keeping all existing native button objects.
 c=Code(a).local(0).op(0x30)
 c.local(0).string(ICON).call('getChildByName',1).store(2);c.local(2).jump(0x11,'done')
 c.lex('MovieClip','flash.display').op(0x42,0).store(2)
 c.local(2).string(ICON).set('name');c.local(2).op(0x26).set('buttonMode');c.local(2).op(0x27).set('mouseChildren');c.local(2).op(0x27).set('visible')
 c.local(2).prop('graphics').store(3)
 c.local(3).number(0x244452).call('beginFill',1).op(0x29)
 c.local(3).number(0).number(0).number(22).number(22).number(4).call('drawRoundRect',5).op(0x29)
 c.local(3).call('endFill',0).op(0x29)
 c.local(3).number(2).number(0x8ff1c0).call('lineStyle',2).op(0x29)
 for fn,x,y in [('moveTo',11,17),('lineTo',11,5),('moveTo',6,10),('lineTo',11,5),('lineTo',16,10),('moveTo',5,18),('lineTo',17,18)]:
  c.local(3).number(x).number(y).call(fn,2).op(0x29)
 c.local(2).string('click').local(0).prop('fo3LineupEnhanceClick').call('addEventListener',2).op(0x29)
 c.local(0).local(2).call('addChild',1).op(0x29)
 # Reuse the rightmost native icon position; shift search/lock left one slot.
 for key in ('x','y'):c.local(2).local(0).prop('playerLockButton').prop(key).set(key)
 for key in ('playerDetailInfoButton','playerLockButton','playerUnLockButton'):
  c.local(0).prop(key).store(4);c.local(4).jump(0x12,'skip_'+key)
  c.local(4).local(4).prop('x').number(26).op(0xa1).set('x').label('skip_'+key)
 c.label('done').op(0x47)
 init=method(a,c,scope,5);added.append((a.name('fo3InitEnhanceIcon'),init));endcall(a,10,'fo3InitEnhanceIcon')
 c=Code(a).local(0).op(0x30).local(0).string(ICON).call('getChildByName',1).store(2)
 c.local(2).jump(0x12,'done');c.local(2).op(0x27).set('visible')
 c.local(0).prop('data').jump(0x12,'done')
 # Match the existing row action visibility and never expose on recycled empty rows.
 c.local(0).prop('data').prop('__lockButtonVisible').jump(0x12,'done')
 c.local(0).prop('playerDetailInfoButton').prop('visible').jump(0x12,'done')
 c.local(2).op(0x26).set('visible').label('done').op(0x47)
 sync=method(a,c,scope,3);added.append((a.name('fo3UpdateEnhanceIcon'),sync))
 for mid in (28,33):endcall(a,mid,'fo3UpdateEnhanceIcon')
 return 'PlayerPoolItemListRenderer',added,dict(click=click,init=init,sync=sync)

def base(a):
 c=Code(a).local(0).string(ICON).call('getChildByName',1).jump(0x12,'done')
 c.local(0).op(0x20).call('fo3UpdateEnhanceIcon',1).op(0x29).label('done')
 a.modify(37,{136:c.done()});return None,[],{}

def panel(a):
 scope=a.A['body_records'][54]['fields'][2];c=Code(a).local(0).op(0x30)
 c.local(0).prop('stage').jump(0x12,'done')
 # Walk the actual display ancestry: never consume from a cached hidden page.
 c.local(0).store(2).label('visibility');c.local(2).prop('visible').jump(0x12,'done')
 c.local(2).string('teamManagementTab').call('hasOwnProperty',1).jump(0x11,'screen')
 c.local(2).prop('parent').store(2);c.local(2).jump(0x11,'visibility').jump(0x10,'done')
 c.label('screen').local(2).string(REQUEST).call('getChildByName',1).store(3)
 c.local(3).jump(0x12,'done')
 c.lex('getTimer','flash.utils').op(0x20).op(0x41,0).local(3).prop('fo3time').op(0xa1).store(4)
 c.local(4).number(0).jump(0x15,'consume');c.local(4).number(60000).jump(0x17,'consume')
 c.local(0).ownprop('_players').store(5);c.local(5).jump(0x12,'done')
 c.local(5).prop('length').jump(0x12,'done')
 c.number(0).store(6).op(0x20).store(7)
 c.label('loop').local(6).local(5).prop('length').jump(0x0c,'consume')
 c.local(5).local(6).op(0x66,a.A['mn'].index('[late]')).store(7)
 c.local(7).prop('_id').local(3).prop('fo3id').jump(0x13,'found')
 c.local(6).number(1).op(0xa0).store(6).jump(0x10,'loop')
 c.label('found')
 for key in ('spid','grade'):c.local(7).prop(key).local(3).prop('fo3'+key).jump(0x14,'consume')
 # Remove the request before native callbacks: re-entry cannot replay selection.
 c.local(2).local(3).call('removeChild',1).op(0x29)
 c.local(0).owncall('clearSelectedPlayer',0).op(0x29)
 c.local(0).local(7).owncall('availableEnhancePlayer',1).jump(0x12,'done')
 c.local(0).local(7).op(0x20).owncall('selectTarget',2).op(0x29)
 c.local(0).owncall('invalidatePlayerList',0).op(0x29).jump(0x10,'done')
 c.label('consume').local(2).local(3).call('removeChild',1).op(0x29)
 c.label('done').op(0x47)
 mid=method(a,c,scope,8);name='fo3AcceptLineupPrimary';endcall(a,54,name);endcall(a,15,name)
 return 'EnhancePlayerPanel',[(a.name(name),mid)],dict(accept=mid)

report={}
for key,patchers in [('components-ScrollingList',{'PlayerPoolItemListRenderer':renderer,'PlayerListItemRendererNew':base}),('TeamManagementPlayerEnhancementTabPage',{'EnhancePlayerPanel':panel})]:
 source=W/(key+'-baseline.big');swf=(W/(key+'-baseline.swf')).read_bytes();start=8+(5+4*(swf[8]>>3)+7)//8+4
 parts=[];blocks={};seen=set()
 for ordinal,(kind,body,raw) in enumerate(tags(swf,start,len(swf))):
  if kind==82:
   head=body.index(b'\0',4)+1;a=ABC(body[head:]);classes=[v[0] for v in a.A['cls']]
   for cls,fn in patchers.items():
    if cls not in classes:continue
    # Skip timeline subclass ABCs carrying the same simple class name.
    if cls=='EnhancePlayerPanel' and '_players' not in a.A['mn']:continue
    assert cls not in seen;seen.add(cls);before=body[head:];old=ABC(before)
    traitcls,add,meta=fn(a);updated=a.output()
    if add:updated=traits(updated,traitcls,add)
    b=ABC(updated);prefix=f'{key}-{ordinal}'
    for mid,row in old.A['body_records'].items():
     if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
    assert old.A['sig']==b.A['sig'][:len(old.A['sig'])]
    for oldcls,newcls in zip(old.A['cls'],b.A['cls']):
     if oldcls[0]==traitcls and add:assert oldcls[:3]==newcls[:3] and oldcls[3]==newcls[3][:-len(add)] and oldcls[4:]==newcls[4:]
     else:assert oldcls==newcls
    (W/(prefix+'-after.abc')).write_bytes(updated)
    (W/(prefix+'-patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    blocks[prefix]=dict(class_name=cls,changed=sorted(a.changed),added=list(range(len(old.A['meth']),len(b.A['meth']))),callbacks=meta)
    raw=tag(kind,body[:head]+updated)
  parts.append(raw)
 assert seen==set(patchers)
 out=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out))
 member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 target=W/(key+'.big');pack_archive(source,target,{member:b'CFX'+out[3:8]+zlib.compress(out[8:],9)},[])
 oldtags=list(tags(swf,start,len(swf)));newtags=list(tags(out,start,len(out)))
 assert len(oldtags)==len(newtags)
 assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82)
 for name,*_ in bigdir.entries(source):
  if name!=member:assert bigdir.read(source,name)==bigdir.read(target,name)
 report[key]=dict(source_sha256=sha(source),sha256=sha(target),blocks=blocks,unchanged_members_preserved=True,unchanged_methods_and_traits_preserved=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
