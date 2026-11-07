from pathlib import Path
import json,hashlib,re
S=Path('D:/FO3ID/server');OUT=Path(__file__).parent/'pending-selection';OUT.mkdir(exist_ok=True)
source=S/'player_editor/index.html';text=source.read_text('utf-8')
text=text.replace('</style>', '''
.layout{align-items:start}.results-table{max-height:440px;overflow:auto}.results-table th{position:sticky;top:0;background:#1d2a36;z-index:1}
#results tr[data-player]{cursor:pointer}#results tr[aria-selected=true]{background:#384724;outline:1px solid #f2c200;outline-offset:-1px}
.player-name{padding:0;border:0;background:none;text-align:left;color:#f2c200;white-space:normal}.player-name:hover{text-decoration:underline}
#playerPanel{scroll-margin-top:65px}#playerPanel:focus{outline:2px solid #f2c200;outline-offset:2px}
@media(max-width:1000px){.results-table{max-height:330px}}
</style>''')
text=text.replace('<div class="table"><table><thead><tr><th>球员／SPID', '<p class="muted">点击球员姓名或整行即可选择并编辑。</p><div class="table results-table"><table><thead><tr><th>球员／SPID')
text=text.replace('<section class="card"><h2 id="playerTitle">', '<section class="card" id="playerPanel" tabindex="-1"><h2 id="playerTitle">')
text=text.replace('r.rows.map(r=>`<tr><td>${esc(r.name)}<br>', 'r.rows.map(r=>`<tr data-player="${r.spid}" tabindex="0" aria-selected="${selected?.row.spid===r.spid}"><td><button type="button" class="player-name" data-open="${r.spid}">${esc(r.name)}</button><br>')
text=text.replace('>编辑</button></td></tr>', '>选择并编辑</button></td></tr>')
text=text.replace("async function openPlayer(spid){selected=await api('detail?spid='+spid);renderEditor()}", """async function openPlayer(spid){
  message('正在读取球员资料…');
  const detail=await api('detail?spid='+spid);
  selected=detail;renderEditor();
  document.querySelectorAll('#results tr[data-player]').forEach(row=>row.setAttribute('aria-selected',String(Number(row.dataset.player)===selected.row.spid)));
  const panel=$('#playerPanel');panel.focus({preventScroll:true});panel.scrollIntoView({block:'start',behavior:'auto'});
  message(`已选择 ${selected.name} · ${seasonName(Math.floor(selected.row.spid/1000000))}，可修改下方属性。`);
}""")
text=text.replace("$('#results').onclick=e=>{if(e.target.dataset.open)action(()=>openPlayer(e.target.dataset.open))};", """function chooseResult(e){const row=e.target.closest('tr[data-player]');if(row)action(()=>openPlayer(row.dataset.player))}
$('#results').onclick=chooseResult;
$('#results').onkeydown=e=>{if(e.target.matches('tr[data-player]')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();chooseResult(e)}};""")
text=text.replace('if(busy)return;busy=true;', "if(busy){message('正在处理上一次操作，请稍候再选择。');return}busy=true;")
text=text.replace('message(e.message,true)', "message(e.message==='Failed to fetch'?'游戏服务暂时无法连接，可能正在更新。服务恢复后请重新搜索或选择球员。':e.message,true)")
(OUT/'index.html').write_text(text,'utf-8')
source_py=S/'player_editor/player_database.py';py=source_py.read_text('utf-8')
start=py.index("        self.publish_readiness = '尚未检查'");end=py.index('    def _season_names(self):',start)
py=py[:start]+'''        self.publish_readiness = '正在校验当前版本…'
        self._readiness_checking = False
        self._readiness_next = 0
        self._readiness_signature = None
        self._refresh_readiness()

    def _version_signature(self):
        files = [self.server / 'play-local.bat'] + sorted((self.server / 'patches').glob('*preflight.py'))
        files += sorted((self.server / 'patches').glob('*manifest.json'))
        files += sorted((self.server / 'patches').glob('*installed.json'))
        return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)

    def _refresh_readiness(self):
        signature = self._version_signature()
        try:
            module(HERE / 'publish_database.py', 'database_readiness').baseline(self.server, self.client)
            result = '版本检查通过，应用时将再次校验'
        except Exception as e:
            result = '当前版本禁止正式应用：' + str(e)
        with self.lock:
            self.publish_readiness = result
            self._readiness_signature = signature
            self._readiness_next = time.monotonic() + 60
            self._readiness_checking = False

    def _schedule_readiness(self):
        if not self._readiness_checking and (time.monotonic() >= self._readiness_next or self._version_signature() != self._readiness_signature):
            self._readiness_checking = True
            self.publish_readiness = '版本有更新，正在重新校验…'
            threading.Thread(target=self._refresh_readiness, daemon=True, name='database-version-check').start()

'''+py[end:]
py=py.replace('    def status(self, p=None):\n', '    def status(self, p=None):\n        self._schedule_readiness()\n')
(OUT/'player_database.py').write_text(py,'utf-8')
meta={str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,source_py)}
(OUT/'source-hashes.json').write_text(json.dumps(meta,indent=2),'utf-8')
(OUT/'check.js').write_text(text.split('<script>')[1].split('</script>')[0],'utf-8')
print(OUT)
