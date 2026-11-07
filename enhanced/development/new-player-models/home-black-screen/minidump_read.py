"""Small read-only reader for Memory64/MemoryList, module and x86 thread streams."""
import bisect,json,mmap,pathlib,struct,sys
class Dump:
    def __init__(self,path):
        self.path=pathlib.Path(path);self.file=self.path.open('rb');self.data=mmap.mmap(self.file.fileno(),0,access=mmap.ACCESS_READ)
        magic,version,count,directory=struct.unpack_from('<4I',self.data,0);assert magic==0x504d444d
        self.streams={}
        for i in range(count):
            kind,size,rva=struct.unpack_from('<III',self.data,directory+i*12);self.streams[kind]=(rva,size)
        self.ranges=[]
        if 9 in self.streams:
            rva,size=self.streams[9];number,base=struct.unpack_from('<QQ',self.data,rva);at=base
            for i in range(number):
                address,length=struct.unpack_from('<QQ',self.data,rva+16+i*16);self.ranges.append((address,address+length,at));at+=length
        elif 5 in self.streams:
            rva,size=self.streams[5];number=struct.unpack_from('<I',self.data,rva)[0]
            for i in range(number):
                address,length,at=struct.unpack_from('<QII',self.data,rva+4+i*16);self.ranges.append((address,address+length,at))
        self.ranges.sort();self.starts=[r[0] for r in self.ranges]
    def read(self,address,size):
        out=[]
        while size:
            i=bisect.bisect_right(self.starts,address)-1
            if i<0 or address>=self.ranges[i][1]:raise KeyError(hex(address))
            start,end,at=self.ranges[i];n=min(size,end-address);out.append(self.data[at+address-start:at+address-start+n]);address+=n;size-=n
        return b''.join(out)
    def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]
    def modules(self):
        rva,size=self.streams[4];number=struct.unpack_from('<I',self.data,rva)[0];rows=[]
        for i in range(number):
            at=rva+4+i*108;base,length,checksum,stamp,name=struct.unpack_from('<QIIII',self.data,at);n=struct.unpack_from('<I',self.data,name)[0]
            rows.append(dict(base=base,size=length,name=self.data[name+4:name+4+n].decode('utf-16-le')))
        return rows
    def threads(self):
        rva,size=self.streams[3];number=struct.unpack_from('<I',self.data,rva)[0];rows=[]
        for i in range(number):
            at=rva+4+i*48;tid=struct.unpack_from('<I',self.data,at)[0];size,context=struct.unpack_from('<II',self.data,at+40)
            row=dict(id=tid,context_bytes=size)
            if size>=204:
                flags=struct.unpack_from('<I',self.data,context)[0];row['flags']=hex(flags)
                if flags&0x10000:
                    row.update(ebp=struct.unpack_from('<I',self.data,context+180)[0],eip=struct.unpack_from('<I',self.data,context+184)[0],esp=struct.unpack_from('<I',self.data,context+196)[0])
            rows.append(row)
        return rows
if __name__=='__main__':
    d=Dump(sys.argv[1]);print(json.dumps(dict(ranges=len(d.ranges),modules=d.modules()[:3],threads=d.threads()[:10],resolver_code=d.read(0xbb4820,16).hex()),indent=2))
