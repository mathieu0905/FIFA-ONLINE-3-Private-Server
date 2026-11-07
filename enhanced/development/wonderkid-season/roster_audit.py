"""Read-only candidate list: use installed FO3 identities and existing appearance files."""
from pathlib import Path
import collections,json,re,sqlite3,sys,unicodedata
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S/'tools/re'));import bigdir
CANDIDATES=[
('帕托','Alexandre Pato','前锋'),('博扬','Bojan Krkic','前锋'),('巴洛特利','Mario Balotelli','前锋'),('阿德里亚诺','Adriano Leite','前锋'),
('卡萨诺','Antonio Cassano','前锋'),('朱塞佩·罗西','Giuseppe Rossi','前锋'),('约维蒂奇','Stevan Jovetic','前锋'),('夸雷斯马','Ricardo Quaresma','边锋'),
('萨维奥拉','Javier Saviola','前锋'),('罗比尼奥','Robson de Souza','边锋'),('尼尔马','Nilmar Honorato','前锋'),('凯里森','Keirrison','前锋'),
('赫塞','Jese Rodriguez','边锋'),('德乌洛费乌','Gerard Deulofeu','边锋'),('博扬·科尔基奇','Bojan Krkic','前锋'),('亚努扎伊','Adnan Januzaj','边锋'),
('马夏尔','Anthony Martial','前锋'),('拉扎尔·马尔科维奇','Lazar Markovic','边锋'),('苏莱曼尼','Miralem Sulejmani','边锋'),('佐兰·托西奇','Zoran Tosic','边锋'),
('阿费莱','Ibrahim Afellay','边锋'),('库恩卡','Isaac Cuenca','边锋'),('杰弗伦','Jeffren Suarez','边锋'),('乔瓦尼·多斯桑托斯','Giovani dos Santos','前腰'),
('贝拉','Carlos Vela','前锋'),('内里·卡斯蒂略','Nery Castillo','前锋'),('卡洛斯·菲耶罗','Carlos Fierro','前锋'),('卢卡斯·皮亚松','Lucas Piazon','前腰'),
('甘索','Ganso','前腰'),('古尔库夫','Yoann Gourcuff','前腰'),('本·阿尔法','Hatem Ben Arfa','前腰'),('梅内','Jeremy Menez','边锋'),
('纳斯里','Samir Nasri','前腰'),('威尔希尔','Jack Wilshere','中场'),('迪亚比','Abou Diaby','中场'),('安德森','Anderson Luis de Abreu','中场'),
('拉威尔·莫里森','Ravel Morrison','前腰'),('哈利洛维奇','Alen Halilovic','前腰'),('卡库塔','Gael Kakuta','前腰'),('马林','Marko Marin','前腰'),
('德拉克斯勒','Julian Draxler','前腰'),('霍尔特比','Lewis Holtby','中场'),('卡纳莱斯','Sergio Canales','前腰'),('穆尼亚因','Iker Muniain','前腰'),
('奥利弗·托雷斯','Oliver Torres','中场'),('扎戈耶夫','Alan Dzagoev','前腰'),('尼尼斯','Sotiris Ninis','前腰'),('利亚伊奇','Adem Ljajic','前腰'),
('雷纳托·桑谢斯','Renato Sanches','中场'),('约什·麦凯克伦','Josh McEachran','中场'),('迈克尔·约翰逊','Michael Johnson','中场'),('戴斯勒','Sebastian Deisler','中场'),
('弗雷迪·阿杜','Freddy Adu','前腰'),('菲尔·琼斯','Phil Jones','后卫'),('迈卡·理查兹','Micah Richards','后卫'),('桑顿','Davide Santon','后卫'),
('巴德施图贝尔','Holger Badstuber','后卫'),('拉诺基亚','Andrea Ranocchia','后卫'),('帕帕多普洛斯','Kyriakos Papadopoulos','后卫'),('萨科','Mamadou Sakho','后卫'),
('扬加-姆比瓦','Mapou Yanga Mbiwa','后卫'),('多利亚','Matheus Doria','后卫'),('罗德维尔','Jack Rodwell','后腰'),('拉斐尔','Rafael Pereira da Silva','后卫'),
('法比奥','Fabio Pereira da Silva','后卫'),('吉布斯','Kieran Gibbs','后卫'),('蒙托亚','Martin Montoya','后卫'),('阿森霍','Sergio Asenjo','门将'),
('阿德勒','Rene Adler','门将'),('佩林','Mattia Perin','门将'),('巴特兰','Jack Butland','门将')]
def norm(s):return re.sub(r'[^a-z0-9 ]',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def main():
    R.mkdir(exist_ok=True)
    catalog={}
    for n in (3,4,6):
        p=C/f'data/data_{n}.big';catalog[n]={name:(offset,size) for name,offset,size,_ in bigdir.entries(p)}
    with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        names={int(row[0]):[str(x or '') for x in row[1:]] for row in db.execute('select playerid,full,full_eng,short,short_eng from nameseng')}
        present={p for p, in db.execute('select distinct playerid from players where spid>=1000000')}
        rows=[];seen=set()
        for zh,en,role in CANDIDATES:
            tokens=norm(en).split();matches=[pid for pid,labels in names.items() if pid in present and any(all(t in norm(label).split() for t in tokens) for label in labels)]
            pins={'阿德里亚诺':106019,'扬加-姆比瓦':181560}
            if zh in pins:matches=[pins[zh]] if pins[zh] in present else []
            if len(matches)!=1:
                rows.append(dict(name_zh=zh,name_en=en,role=role,status='NO_UNIQUE_DATABASE_ID',matches=matches));continue
            pid=matches[0]
            if pid in seen:continue
            seen.add(pid)
            expected=[(3,f'data/sceneassets/faces/face_{pid}_0_0_0_0_0_0_0_0_textures.rx3'),(4,f'data/sceneassets/heads/head_{pid}_0.rx3'),
                      (4,f'data/sceneassets/hair/hair_{pid}_0_0.rx3'),(4,f'data/sceneassets/hair/hair_{pid}_0_textures.rx3'),(6,f'data/sceneassets/hairlod/hairlod_{pid}_0_0.rx3')]
            files=[dict(archive=f'data_{i}.big',member=name,size=catalog[i][name][1]) for i,name in expected if name in catalog[i]]
            head=expected[1][1] in catalog[4];face=expected[0][1] in catalog[3]
            options=db.execute('select spid,headclasscode,headtypecode,hashighqualityhead,hairtypecode from players where playerid=? and spid>=1000000 order by hashighqualityhead desc,spid desc',(pid,)).fetchall()
            rows.append(dict(name_zh=zh,name_en=en,role=role,playerid=pid,db_labels=names[pid],
                status='DEDICATED_HEAD_FACE_COMPLETE5' if len(files)==5 else 'DEDICATED_HEAD_FACE_PARTIAL_HAIR' if head and face else 'EXISTING_CARD_GENERIC_FACE_ONLY',
                files=files,source_card_options=options[:6]))
    report=dict(status='READ_ONLY_INSTALLED_RESOURCE_INVENTORY',candidates=rows,counts=dict(collections.Counter(r['status'] for r in rows)),
                no_production_writes=True,no_resource_imports=True,native_verified=False)
    (R/'roster-resource-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    for state in report['counts']:
        print(state,[(r['name_zh'],r.get('playerid')) for r in rows if r['status']==state])
    print('COUNTS',json.dumps(report['counts']))
if __name__=='__main__':main()
