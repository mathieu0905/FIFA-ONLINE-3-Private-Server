"""EA native DB codec. All semantic fields are explicit and range checked."""
import datetime,email.utils,struct,xml.etree.ElementTree as ET
import eadb
def stars_to_code(stars):
    if type(stars) is not int or not 1<=stars<=5:raise ValueError('Skill stars must be 1..5')
    return stars-1
def player_table(db,meta):
    node=next(n for n in ET.fromstring(meta).iter('table') if n.get('name')=='players')
    fields={f.get('name'):f.attrib for f in node.iter('field')};base,names,raws=eadb.db_tables(db);index=names.index(node.get('shortname').encode())
    return base,names,raws,index,eadb.Table(raws[index]),fields
def encode(t,fields,template,semantic):
    missing=set(fields)-set(semantic)
    if missing:raise ValueError('Missing native fields: '+','.join(sorted(missing)))
    result=template
    for name,f in fields.items():
        sn=f['shortname'];ty,offset,depth=t.fields[sn];value=semantic[name]
        if f['type']=='DBOFIELDTYPE_DATE':
            if isinstance(value,str):
                date=datetime.datetime.strptime(value,'%m/%d/%Y %I:%M:%S %p').date() if name=='birthdate' else email.utils.parsedate_to_datetime(value).date()
            else:date=value
            value=date.toordinal()-577735;encoded=value-int(f['rangelow'])
        elif ty==4:encoded=struct.unpack('<I',struct.pack('<f',float(value)))[0]
        else:
            if ty!=3 or type(value) not in [int,float] or int(value)!=value:raise ValueError('Invalid integer '+name)
            low,high=int(f['rangelow']),int(f['rangehigh'])
            if not low<=value<=high:raise ValueError(f'Native {name}={value} outside {low}..{high}; convert the source semantics explicitly')
            encoded=int(value)-low
        if not 0<=encoded<2**depth:raise ValueError('Native bit width overflow: '+name)
        result=t.set(result,sn,encoded)
        actual=t.get(result,sn)
        expected=float(value) if ty==4 else encoded
        if actual!=expected:raise ValueError('Native round trip failed: '+name)
    return result
def rebuild(db,index,new_table):
    base,names,raws=eadb.db_tables(db);raws[index]=new_table.raw();header=bytearray(db[:base]);offset=0
    for i,raw in enumerate(raws):struct.pack_into('<I',header,0x1c+i*8,offset);offset+=len(raw)
    struct.pack_into('<I',header,base-4,eadb.crc(header[0x18:base-4]));struct.pack_into('<I',header,8,base+offset);struct.pack_into('<I',header,0x14,eadb.crc(header[:0x14]))
    result=bytes(header)+b''.join(raws);verify_crc(result);return result
def verify_crc(db):
    base,names,raws=eadb.db_tables(db)
    if eadb.u32(db,8)!=len(db) or eadb.u32(db,0x14)!=eadb.crc(db[:0x14]) or eadb.u32(db,base-4)!=eadb.crc(db[0x18:base-4]):raise ValueError('EA DB header CRC mismatch')
    for name,raw in zip(names,raws):
        if eadb.u32(raw,0x20)!=eadb.crc(raw[:0x20]) or eadb.u32(raw,len(raw)-4)!=eadb.crc(raw[0x24:-4]):raise ValueError('EA table CRC mismatch: '+repr(name))
