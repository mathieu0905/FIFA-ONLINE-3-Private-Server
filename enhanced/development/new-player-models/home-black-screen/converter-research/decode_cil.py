"""Read-only CIL disassembly of source-bound methods admitted by REA."""
from pathlib import Path
import json,struct,sys
ROOT=Path(__file__).resolve().parent
OPS=json.loads((ROOT/'cil-opcodes.json').read_text('utf-8-sig'))
def decode(report,method):
    d=Path(report['artifact']['path']).read_bytes();off=method['body']['file_offset'];flags=struct.unpack_from('<H',d,off)[0]
    header=(flags>>12)*4 if flags&3==3 else 1
    code=d[off+header:off+header+method['body']['il_size']]
    names={r['token']:str(r.get('parent_name',''))+'.'+r['name'] for r in report['refs']}
    names.update({m['token']:m['name'] for m in report.get('methods',[])})
    names.update({s['token']:repr(s['value']) for s in report['strings']})
    at=0;rows=[]
    while at<len(code):
        start=at;op=code[at];at+=1
        if op==0xfe:op=0xfe00+code[at];at+=1
        desc=OPS[str(op)];kind=desc['operand'];value=None
        if kind in ('InlineMethod','InlineField','InlineString','InlineType','InlineTok','InlineSig'):
            token='0x'+format(struct.unpack_from('<I',code,at)[0],'08x');value=names.get(token,token);at+=4
        elif kind=='InlineI':value=struct.unpack_from('<i',code,at)[0];at+=4
        elif kind=='ShortInlineI':value=struct.unpack_from('<b',code,at)[0];at+=1
        elif kind=='InlineI8':value=struct.unpack_from('<q',code,at)[0];at+=8
        elif kind=='ShortInlineR':value=struct.unpack_from('<f',code,at)[0];at+=4
        elif kind=='InlineR':value=struct.unpack_from('<d',code,at)[0];at+=8
        elif kind=='InlineVar':value=struct.unpack_from('<H',code,at)[0];at+=2
        elif kind=='ShortInlineVar':value=code[at];at+=1
        elif kind=='InlineBrTarget':value=at+4+struct.unpack_from('<i',code,at)[0];at+=4
        elif kind=='ShortInlineBrTarget':value=at+1+struct.unpack_from('<b',code,at)[0];at+=1
        elif kind=='InlineSwitch':
            n=struct.unpack_from('<I',code,at)[0];at+=4;end=at+4*n;value=[end+v for v in struct.unpack_from('<'+'i'*n,code,at)];at=end
        elif kind!='InlineNone':raise AssertionError(kind)
        rows.append((start,desc['name'],value))
    return rows
if __name__=='__main__':
    report=json.loads((ROOT/sys.argv[1]).read_text('utf8'))
    for m in report['methods']:
        if len(sys.argv)>2 and m['name'] not in sys.argv[2:]:continue
        rows=decode(report,m);print(m['name'],m['token'])
        for at,op,value in rows:print(at,op,'' if value is None else value)
