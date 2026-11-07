"""Finish native integration and seal only the exact task-owned file delta."""
from pathlib import Path
import hashlib,importlib.util,json,re
S=Path('D:/FO3ID/server');P=S/'player_editor'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')

path=P/'player_database.py';text=path.read_text('utf-8')
start=text.index('    def publish(self, p):');end=text.index('    def build(self, draft, out):',start)
text=text[:start]+'''    def publish(self, p):
        import subprocess
        with self.lock:
            if self.building:
                raise ValueError('请等待当前构建或应用任务完成')
            job = str(p.get('id', ''))
            if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}', job):
                raise ValueError('非法构建编号')
            path = self.work / 'jobs' / (job + '.json')
            record = read(path)
            if record.get('status') not in ('built', 'apply_failed') or record.get('manifest_sha256') != p.get('manifest_sha256'):
                raise ValueError('构建状态或校验值不匹配')
            candidate = self.work / 'builds' / job
            if sha(candidate / 'manifest.json') != record['manifest_sha256']:
                raise ValueError('构建清单已变化')
            record.update(status='applying', candidate=str(candidate))
            record.pop('error', None)
            write(path, record)
            try:
                with (self.work / 'publish.log').open('ab') as log:
                    subprocess.Popen([sys.executable, '-B', str(HERE / 'run_publish.py'), str(path)],
                                     cwd=self.server, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except Exception:
                record['status'] = 'apply_failed'
                write(path, record)
                raise
            self.building = True
            return record

'''+text[end:]
text=text.replace("        with closing(self.connect()) as c:\n            seasons =", "        self.building = any(j['status'] in ('building', 'applying') for j in jobs)\n        d = self.draft()\n        changed = False\n        for j in jobs:\n            if j['status'] == 'installed':\n                for entry in read(Path(j['candidate']) / 'manifest.json')['changes']:\n                    if d['cards'].get(str(entry['spid'])) == entry:\n                        d['cards'].pop(str(entry['spid']))\n                        changed = True\n        if changed:\n            d['revision'] += 1\n            write(self.work / 'draft.json', d)\n        with closing(self.connect()) as c:\n            seasons =")
path.write_text(text,'utf-8')
path=P/'index.html';text=path.read_text('utf-8')
text=re.sub(r'<header>.*?</header>','',text,flags=re.S)
text=text.replace("fetch('/api/'+name", "fetch('/api/database_'+name")
text=text.replace("let state,selected", "const seasonName=n=>state?.season_labels?.[Number(n)]||String(n)+' · 未命名赛季（原始库）';\nlet state,selected")
text=text.replace('<td>${r.season}</td>','<td>${esc(seasonName(r.season))}</td>')
text=text.replace('赛季 ${Math.floor(row.spid/1000000)}','赛季 ${seasonName(Math.floor(row.spid/1000000))}')
text=text.replace('<option>${s}</option>','<option value="${s}">${esc(seasonName(s))}</option>')
text=text.replace('${c.spid} / ${Math.floor(c.spid/1000000)}','${c.spid} / ${esc(seasonName(Math.floor(c.spid/1000000)))}')
path.write_text(text,'utf-8')
path=S/'play-local.bat';data=path.read_bytes();assert b'patches\\market_background_preflight.py' in data
path.write_bytes(data.replace(b'patches\\market_background_preflight.py',b'patches\\player_editor_preflight.py'))
# Compose the unchanged prior metadata; replaced physical files are checked by exact parent hashes.
parent=load(S/'patches/market_background_preflight.py','integrated_parent');c,v=parent._compose(S,Path('D:/FO3ID/32795'));guards=v.table(c['guards'])
child=load(S/'patches/player_editor_preflight.py','integrated_child')
rows=[]
backup=S/'backups/player-editor-8088-20261106'
backups={'admin.py':'admin.py','admin/index.html':'index.html','play-local.bat':'play-local.bat'}
for root,rel in sorted(child.ALLOWED):
    key=(root,rel.casefold());expected=guards.get(key,{}).get('sha256')
    if rel in backups and sha(backup/backups[rel])!=expected:raise RuntimeError('Parallel change detected: '+rel)
    rows.append(dict(root=root,relative=rel,parent_sha256=expected,sha256=sha(S/rel)))
m=dict(release_id='player-editor-8088-20261106',phase='NATIVE_8088_PLAYER_EDITOR',client_root='D:/FO3ID/32795',state_shop_replaced=False,
       parent_files={n:sha(S/n) for n in (child.PARENT,'patches/market-background-release-manifest.json','patches/market-background-release-installed.json')},files=rows)
write(S/child.MANIFEST,m)
write(S/child.RECEIPT,dict(status='INSTALLED_8088_PLAYER_EDITOR',release_id=m['release_id'],manifest_sha256=sha(S/child.MANIFEST),backup=str(backup),state_shop_replaced=False))
print(json.dumps(child.preflight(S,'D:/FO3ID/32795'),ensure_ascii=True))
