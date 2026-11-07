"""Read-only live verification and append-only engineering handback."""
from pathlib import Path
import datetime,json,re,ssl,subprocess,sys,urllib.request
sys.dont_write_bytecode=True
import build,install,test_history
S=build.SERVER;C=build.CLIENT;R=build.HERE

def main():
    with install.locks(S):
        handback=json.loads((R/'installed-handback.json').read_text('utf8'))
        play=(S/'play-local.bat').read_bytes()
        active='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
        proof=build.load(S/active,'history_actual_top_final').preflight(S,C)
        # Only use our pre-install database comparison while our exact resource
        # revision remains current. A later legitimate roster release is retained.
        if build.sha(S/'gamedata/fifadb.sqlite')!=handback['hashes'][str(S/'gamedata/fifadb.sqlite')]:
            raise RuntimeError('Later DB revision present: retain it and verify against its own receipt, not this old baseline')
        journal=json.loads((Path(handback['backup'])/'transaction.json').read_text('utf8'))
        oldrow=next(e for e in journal['entries'] if e['relative']=='gamedata/fifadb.sqlite')
        database_proof=build.verify_tables(S/'gamedata/fifadb.sqlite',Path(oldrow['backup']))
        behaviour=test_history.run(S/'gamedata/fifadb.sqlite')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
        def get(path):
            with opener.open('https://127.0.0.1'+path,timeout=25) as r:return json.load(r)
        locale=get('/info/server/locale');assert locale.get('language')=='chi'
        messenger=get('/info/my/services/messenger/2');assert messenger.get('port')==28002
        colors=get('/static/info/teamcolor');assert isinstance(colors.get('teamColors'),list) and colors['teamColors']
        readiness=build.load(S/'wait_services.py','history_ready_final');readiness.ready()
        c=__import__('sqlite3').connect('file:'+(S/'gamedata/fifadb.sqlite').as_posix()+'?mode=ro',uri=True)
        coverage=dict(players=c.execute('select count(distinct playerid) from playerhistory').fetchone()[0],
                      rows=c.execute('select count(*) from playerhistory').fetchone()[0])
        c.close()
        report=json.loads((R/'build/coverage-report.json').read_text('utf8'))
        assert coverage==dict(players=report['players_after'],rows=report['history_rows_after'])
        result=dict(status='FORMAL_DATABASE_RESOURCE_AND_SERVICE_CHECKS_PASS_NATIVE_PENDING',actual_top=active,
            preflight=proof,database=database_proof,behaviour=behaviour,coverage=coverage,
            live_readonly_endpoints=['/info/server/locale','/info/my/services/messenger/2','/static/info/teamcolor'],
            team_color_definitions=len(colors['teamColors']),assets_identical_while_stopped=handback['assets_identical_while_stopped'],
            state_shop_written=False,native_status='PENDING',gui_used=False)
        build.write(R/'formal-verification.json',result)
        docs=S/'docs/工程经验与修改边界.txt';before=docs.read_bytes();marker='FO3-俱乐部履历-20261106'
        if marker not in before.decode('utf-8-sig'):
            backup=Path(handback['backup'])/'engineering-before.txt'
            if backup.exists():raise RuntimeError('Engineering backup already exists; inspect before retrying')
            backup.write_bytes(before)
            entry=('\r\n\r\n'+marker+'：球员历史俱乐部户口增量\r\n'
                '现象与确认：旧playerhistory仅1040人/5258行，队套生产逻辑本已支持当前俱乐部并历史俱乐部；缺失与过时履历导致漏算。\r\n'
                '正式修复：2026-11-06采集Nexon FC Online官方公开PlayerInfo职业履历（年份/租借），与现有EA playerid精确匹配；19834个重合ID中7775份有效履历。只更新playerhistory至8121人/47149行，7586人变化，新增31265组球员-俱乐部资格；其它所有表双向EXCEPT一致。原有户口集合全保留、同队同开始年的结束年/租借状态采用官方记录，重复效力阶段分别保留。\r\n'
                '球队映射边界：俱乐部下拉表用官方EA teamid；米兰131681→47、国米131682→44、拉齐奥115841→46、亚特兰大115845→39经多个独立球员/加入年份核对，排除同年多次转会歧义。无法精确匹配的队名和客户端缺少名称资源的新俱乐部（含迈阿密国际）单独列coverage-report，未猜测导入，不能声称所有生涯已完整。\r\n'
                '验证：SQLite integrity、其它表不变、旧户口保留、双端解密回读、271项BIG目录有序及270个非目标压缩payload一致；8项生产队套函数回归（跨赛季共享履历、重复效力、租借、4名前曼联触发及同人多卡去重）；6项小型临时I/O事务/锁/回滚/后续合法修改保留/真实新门槛篡改拒绝。Windows PowerShell 5.1子进程使用原生PSModulePath，确认Get-CimInstance/Get-Process/Stop-Process可用。\r\n'
                '安装状态：从实际round_buy_preflight最新父层组合，1432 guards PASS，继承全部既有guards和receipt policies，未修改历史hash/receipt；正式服务已恢复，真实本次停服state/shop快照前后完全一致。只读HTTPS locale/messenger/teamcolor、8088和28002服务检查通过。未操作GUI、未强制关游戏；详情tooltip及比赛实际加成仍待原生验证，native=PENDING。\r\n'
                '备份：'+handback['backup']+'。证据D:/fifaol3/club-history/{build/coverage-report.json,build/player-changes.json,build/layout-report.json,history-test-results.json,install-test-results.json,formal-verification.json,installed-handback.json}；复验test_history.py、test_install.py及正式patches/club_history_preflight.py。\r\n')
            if docs.read_bytes()!=before:raise RuntimeError('Concurrent engineering entry; retry without discarding it')
            install.atomic(before+entry.encode('utf8'),docs)
        handback['formal_verification']=str(R/'formal-verification.json')
        handback['engineering_record']=str(docs)
        handback['locks_released_on_exit']=True
        build.write(R/'installed-handback.json',handback)
        # The handback is file-based because the original coordinator chat has
        # been archived. This does not unarchive or resume that paused task.
        build.write(R/'handoff-current.json',dict(status='COMPLETE_WRITER_RELEASED_AFTER_THIS_CHECK',actual_top=active,
            composition_api='compose_manifest(server=None, client=None)',hashes=handback['hashes'],
            backup=handback['backup'],formal_verification=result,writer_scope_complete=True,
            subsequent_database_publishers='Rebuild on the current formal database and retain all playerhistory rows; do not overwrite with the old DB build.',
            original_coordinator_archived=True,root_goal_resumed=False))
        print(json.dumps(dict(status=result['status'],coverage=coverage,guards=proof['files'],state_shop_written=False)))

if __name__=='__main__':main()
