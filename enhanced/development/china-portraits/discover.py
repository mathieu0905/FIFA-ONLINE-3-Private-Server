from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin
import json
R=Path(__file__).resolve().parent
class Images(HTMLParser):
 def __init__(self):super().__init__();self.images=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='img' and a.get('src'):self.images.append(a)
cards=json.loads((R.parent/'china-future/input/cards.json').read_text('utf8'))
pages=[('cfa','https://www.thecfa.cn/nzu17/index.html'),('nzga','https://www.thecfa.cn/nzga/index.html'),('nzu20','https://www.thecfa.cn/nzu20/index.html'),('nzgjd','https://www.thecfa.cn/nzgjd/index.html'),('ly','https://www.xiaojiangfc.com/players/lv-mengyang/index.html'),('lh','https://www.xiaojiangfc.com/players/li-haoyan/index.html')]
found={}
def norm(x):return x.replace('·','').replace(' ','').replace('买买提','').replace('玉苏普','')
for key,url in pages:
 if not (R/(key+'.html')).exists():continue
 p=Images();p.feed((R/(key+'.html')).read_text('utf8'))
 for card in cards:
  for img in p.images:
   if img.get('alt') and norm(img['alt'])==norm(card['name_zh']):
    found.setdefault(str(card['fo3_spid']),dict(name=card['name_zh'],playerid=card['base_playerid'],spid=card['fo3_spid'],page_url=url,image_url=urljoin(url,img['src']),caption=img['alt'],page_file=key+'.html'))
(R/'discovered.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(dict(found=len(found),missing=[c['name_zh'] for c in cards if str(c['fo3_spid']) not in found],sources=[dict(name=v['name'],image_url=v['image_url']) for v in found.values()]),ensure_ascii=True))
