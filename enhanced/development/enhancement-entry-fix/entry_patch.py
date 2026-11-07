from client_tools import *
import importlib.util
spec=importlib.util.spec_from_file_location('prefs_helpers',Path('D:/fifaol3/enhancement-remember/client_patch.py'));prefs=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefs)
STABLE=Path('D:/fifaol3/enhancement-remember')
PAIR=Path('D:/fifaol3/enhancement-pair-remember')
MEMBER='fo3RestoreSelectedPair'
def restore(a,old,mid):
    assert all(a.values[k][:len(old.values[k])]==old.values[k] for k in range(7))
    a.changed[mid]=old.A['body_records'][mid]['raw'];a.A['body'][mid]=old.A['body'][mid];a.A['body_records'][mid]=old.A['body_records'][mid]

def control_patch(a):
    old=ABC((STABLE/(NAMES[0]+'-before.abc')).read_bytes())
    # Restore first-load handlers to the version used successfully at 15:41.
    for mid in (8,22,23,26):restore(a,old,mid)
    # No new widget writes, label callbacks or GETs on an empty initial page.
    mid=26;base=a.A['body_records'][mid]['fields'][1];c=Code(a)
    c.local(0).ownprop('_available').jump(0x12,'done')
    c.raw(prefs.point_restore(a,base,label=True));c.label('done')
    a.modify(mid,{len(a.A['body'][mid])-1:c.done()},locals_extra=2)
    # Reuse a native bound public method instead of adding a lexical closure.
    mid=20;before=ABC((PAIR/(NAMES[0]+'-before.abc')).read_bytes());restore(a,before,mid)
    base=a.A['body_records'][mid]['fields'][1];c=Code(a).store(base)
    c.local(base).local(0).ownprop('_owner').prop(MEMBER).set('fo3RestorePair');c.local(base)
    at=next(int(line.split(':',1)[0]) for line in dis(a.A,a.A['body'][mid]) if 'callproperty attachScreen (2)' in line)
    a.modify(mid,{at:c.done()},locals_extra=1)
    # The previous closure is no longer referenced; keep its slot as a harmless
    # stub so immutable old method indexes remain stable.
    mid=46;record=a.A['body_records'][mid];code=Code(a).op(0x47).done()
    a.changed[mid]=u30(mid)+b''.join(u30(v) for v in record['fields'])+u30(len(code))+code+record['suffix']
    return dict(restored_startup_methods=[8,22,23],guarded_empty_page_method=26,unused_closure_stub=46)

def owner_patch(a):
    old=ABC((PAIR/'EnhancePlayerPanel-before.abc').read_bytes());restore(a,old,18)
    # Reuse the already-tested restore implementation as a normal public class
    # method. Its lexical scope is the same as other native instance methods.
    current=ABC((PAIR/'EnhancePlayerPanel-after.abc').read_bytes())
    patch=json.loads((PAIR/'EnhancePlayerPanel-ABC.patch.json').read_text())['18']
    code=current.A['body'][18];start=patch['mapping']['7'];original=bytes.fromhex(patch['original'])
    end=next(e for at,e,_,_ in instructions(original) if at==7);stop=patch['mapping'][str(end)]-(end-7)
    # Generate a clean one-argument method, without the public query dispatcher.
    from avm_patch import instructions as ins
    original_code=code[start:stop]
    rows=list(ins(original_code))
    # First instructions compare command to the custom string; skip that header.
    begin=next(e for at,e,op,t in rows if op==0x14)
    # Copy the block and translate getlocal2 (old data arg) to getlocal1. All
    # newly introduced registers are >=5; native firstTarget/player args unaffected.
    block=bytearray(original_code[begin:])
    for at,e,op,t in list(ins(block)):
        if op==0x62 and R(block,at+1).u30()==2:block[at+1]=1
    # The last returnvoid is the original done branch. All local branches stay
    # relative and remain internal after dropping the dispatcher header.
    method=Code(a).local(0).op(0x30).raw(bytes(block)).done()
    method_id=a.add_method(method,old.A['body_records'][18]['fields'][2],local_count=12)
    return dict(public_method_id=method_id,public_method_name=MEMBER,query_restored_exact=True)

def popup_patch(a):return {}

def add_public_trait(data,class_name,name,method):
    # Locate class trait records using the existing parser's own bounds.
    import avm_patch
    src=avm_patch.SOURCE
    src=src.replace('    def traits():\n        out = []','    def traits():\n        trait_start=r.p\n        out = []')
    src=src.replace('        return out\n','        A.setdefault("trait_records",[]).append(dict(start=trait_start,end=r.p,values=out))\n        return out\n',1)
    ns={'__name__':'trait_bounds'};exec(compile(src,'<ABC trait bounds>','exec'),ns)
    parsed=ns['parse'](data,0);cls=next(row for row in parsed['cls'] if row[0]==class_name)
    records=[row for row in parsed['trait_records'] if row['values']==cls[3]];assert len(records)==1
    row=records[0];r=R(data,row['start']);count=r.u30()
    addition=u30(name)+bytes([1])+u30(0)+u30(method)
    out=data[:row['start']]+u30(count+1)+data[r.p:row['end']]+addition+data[row['end']:]
    check=ABC(out);newcls=next(v for v in check.A['cls'] if v[0]==class_name)
    assert newcls[3][:-1]==cls[3] and newcls[3][-1]==('method',MEMBER,method)
    return out
