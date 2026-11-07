from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;N=R.parent/'item-icons/native-style'
ns={'__file__':str(N/'build.py')}
exec(compile((N/'build.py').read_text('utf8').split('\nitems={}')[0],str(N/'build.py'),'exec'),ns)
out=R/'icons';out.mkdir(exist_ok=True);items={}
for row in json.loads((R/'icon-rows.json').read_text('utf8')):
 im,p,theme,badge,mode=ns['build'](row);key='FO3N_'+str(row['id'])+'_V3';dest=out/(key+'.png');im.save(dest)
 items[str(row['id'])]=dict(itemid=row['id'],icon=key,filename=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),size=[170,120],name=row['definition']['name'],theme=theme,source_path=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_type='Existing native-style artwork reused',grade_values=row['grades'],grade_badge=badge,grade_mode=mode)
(R/'icon-updates.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(icons=len(items))))
