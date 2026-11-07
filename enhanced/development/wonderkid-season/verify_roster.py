"""Bind the first roster to installed native identities and complete existing RX3 assets."""
from pathlib import Path
import collections,hashlib,json,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path[:0]=[str(S/'tools/re'),'D:/fifaol3/new-player-models/bulk-repair/tooling']
import bigdir,eadb,rx3
audit=json.loads((R/'roster-resource-audit.json').read_text('utf-8'))
# Start with the more strongly themed disappointments; two successful long-term
# club playmakers remain optional reserves rather than padding the first issue.
reserves={'卡纳莱斯','穆尼亚因'}
selected=[p for p in audit['candidates'] if p['status']=='DEDICATED_HEAD_FACE_COMPLETE5' and p['name_zh'] not in reserves]
assert len(selected)==40
archive=C/'data/data_0.big';db=bigdir.read(archive,'data/db/fifa_ng_db.db')
meta=ET.fromstring(bigdir.read(archive,'data/db/fifa_ng_db-meta.xml').decode('utf-8'))
node=next(n for n in meta.iter('table') if n.get('name')=='players');fields={f.get('name'):f.attrib for f in node.iter('field')}
_,names,raws=eadb.db_tables(db);table=eadb.Table(raws[names.index(node.get('shortname').encode())]);pidkey=fields['playerid']['shortname']
native={table.get(r,pidkey):r for r in table.rows}
failures=[]
for p in selected:
    pid=p['playerid'];p['native_player_present']=pid in native
    if pid not in native:failures.append(dict(player=p['name_zh'],reason='missing native player row'));continue
    p['native_appearance']={key:table.get(native[pid],fields[key]['shortname']) for key in ('headassetid','headclasscode','headtypecode')}
    for entry in p['files']:
        path=C/'data'/entry['archive'];raw=bigdir.read(path,entry['member'])
        try:plain=rx3.unwrap(raw);sections=rx3.sections(plain)
        except Exception as error:failures.append(dict(player=p['name_zh'],member=entry['member'],reason=str(error)));continue
        entry.update(sha256=hashlib.sha256(raw).hexdigest(),rx3_sections=sum(map(len,sections.values())),rx3_structure_valid=True)
    p['source_card_spid']=next((r[0] for r in p['source_card_options'] if r[1]==0),p['source_card_options'][0][0])
report=dict(status='PASS_EXISTING_MODELS_NO_IMPORT_REQUIRED' if not failures else 'FAIL',name='神童·未竟天赋',
 roster_size=len(selected),groups=dict(collections.Counter(p['role'] for p in selected)),players=selected,failures=failures,
 required_new_model_files=0,existing_model_files_checked=sum(len(p['files']) for p in selected),
 native_players_checked=len(selected),production_written=False,native_game_verified=False,installed=False)
(R/'first-roster.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
if failures:print(json.dumps(failures,ensure_ascii=False));raise SystemExit(1)
lines=['神童·未竟天赋——首批40人方案','', '只复用正式客户端现有模型，不新增或替换模型资源。40个原生playerid存在，200个专属头/脸贴图/头发/头发贴图/远景头发文件已回读并通过RX3结构检查。尚未逐人实机验证，也未安装本赛季。','']
for role in dict.fromkeys(p['role'] for p in selected):
    people=[p for p in selected if p['role']==role];lines.append(role+'（'+str(len(people))+'人）：'+'、'.join(p['name_zh'] for p in people))
lines+=['','能力定位：假想天赋充分兑现，按原生传奇档分层；保留速度、盘带、传球、防守等个人特点，不直接复刻已有巨星巅峰卡。',
        '模型边界：复用现有年龄版本的脸型/发型，不承诺少年脸；沿用现有身材和动作模板。',
        '暂缓：戴斯勒、阿杜当前未找到可直接复用的在库赛季卡；阿德里亚诺、夸雷斯马、莫里森、哈利洛维奇等暂未确认同等完整的专属脸资源，不纳入这批零补模名单。']
(R/'首批40人方案.txt').write_text('\n'.join(lines),'utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('players','failures')},ensure_ascii=False))
print('\n'.join(lines[4:]))
