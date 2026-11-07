"""Fetch only caption-matched real photos; no image synthesis or identity substitution."""
from pathlib import Path
from urllib.parse import quote,urlsplit,urlunsplit
import concurrent.futures,hashlib,io,json,sys,urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'upstream-review/deps'))
from PIL import Image
R=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 found=json.loads((R/'discovered.json').read_text('utf8'));cards=json.loads((R.parent/'china-future/input/cards.json').read_text('utf8'))
 extra={
  '向余望':(1515510,'yuwang-xiang','Yuwang Xiang; Chongqing Tonglianglong; 2003-12-18'),
  '李新翔':(1933818,'li-xinxiang','Xinxiang Li; Shanghai Port; 2005 birth year; source UTC date one day earlier'),
  '杨皓宇':(1801199,'yang-haoyu','Haoyu Yang; Shanghai Shenhua; 2006 birth year; not same-name 2000 player'),
  '吾米提江·玉苏普':(1483286,'umidjan-yusup','Yusup Umidjan; Shanghai Port; 2004-02-28'),
  '汪士钦':(1515499,'shiqin-wang','Shiqin Wang; Zhejiang; 2003-06-24')}
 for c in cards:
  if c['name_zh'] in extra:
   pid,slug,caption=extra[c['name_zh']]
   found[str(c['fo3_spid'])]=dict(name=c['name_zh'],playerid=c['base_playerid'],spid=c['fo3_spid'],page_url=f'https://www.sofascore.com/football/player/{slug}/{pid}',image_url=f'https://img.sofascore.com/api/v1/player/{pid}/image',caption=caption,identity_validation='Named profile, club, role and age matched; no biometric identification')
 assert len(found)==32
 (R/'originals').mkdir(exist_ok=True);(R/'portraits').mkdir(exist_ok=True)
 def fetch(row):
  original=row['image_url'];parts=urlsplit(original)
  url=urlunsplit(('https',parts.netloc,quote(parts.path,safe='/%'),parts.query,parts.fragment))
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as f:data=f.read()
   image=Image.open(io.BytesIO(data));image.load();assert 16<=image.width<=4000 and 16<=image.height<=4000
   original_file=R/'originals'/(str(row['spid'])+'.'+image.format.lower());original_file.write_bytes(data)
   out=R/'portraits'/f'p{row["spid"]}.png'
   if image.format=='PNG':out.write_bytes(data);conversion='none; original PNG bytes'
   else:
    # File-format conversion preserves every decoded pixel. No crop, resize,
    # retouch, face edit, synthetic detail or background replacement.
    image.convert('RGBA').save(out);conversion='lossless JPEG-to-PNG container conversion; original decoded pixels preserved'
   final=Image.open(out).convert('RGBA');assert list(final.getdata())==list(image.convert('RGBA').getdata())
   return dict(row,resolved_image_url=url,source_sha256=sha(data),portrait_sha256=sha(out.read_bytes()),width=image.width,height=image.height,source_format=image.format,format_conversion=conversion,pixel_identity_preserved=True,status='VERIFIED_NAMED_SOURCE_PHOTO')
  except Exception as e:return dict(row,status='FAILED',error=repr(e))
 result=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(fetch,found.values()))
 (R/'source-manifest.json').write_text(json.dumps(dict(schema=1,players=result),ensure_ascii=False,indent=2),'utf8')
 good=[r for r in result if r['status']!='FAILED'];assert len({r['portrait_sha256'] for r in good})==len(good),'Duplicate/default portrait requires investigation'
 print(json.dumps(dict(verified=len(good),failed=[dict(name=r['name'],error=r['error']) for r in result if r['status']=='FAILED'],sizes=[(r['name'],r['width'],r['height']) for r in good]),ensure_ascii=True))
if __name__=='__main__':main()
