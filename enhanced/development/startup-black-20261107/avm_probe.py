from pathlib import Path
import sys,subprocess,json
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'ucl25-import'))
import display
SDK=R.parent/'enhancement-avm-check/lib/redtamarin'
def run(args,name):
    p=subprocess.run([str(x) for x in args],cwd=R,capture_output=True,text=True,errors='replace',creationflags=subprocess.CREATE_NO_WINDOW,timeout=40)
    log=p.stdout+p.stderr;(R/name).write_text(log,'utf8');return p.returncode,log
a=display.ABC((R/'PlayerListUtil.abc').read_bytes())
names={(ns,n) for i,n in enumerate(a.A['mn']) if (ns:=a.A['mnns'][i]) and ':' not in ns and n[:1].isupper() and n!='PlayerListUtil'}
rows=[]
for ns,n in sorted(names):
    extra=''
    if n=='Localization':
        extra='public static function getLocalizedString(v:Object):String{return String(v);} public static function getLocalizedStringWithArgs(v:Object,...args):String{return String(v)+":"+args.join(":");} public static function PLAYERSHORTNAME(v:Object,cb:Function,d:Object):void{cb("Name");}'
    rows.append('package '+ns+' {public dynamic class '+n+' extends Object { public function '+n+'(...args){super();} '+extra+' }}')
(R/'season-stubs.as').write_text('\n'.join(rows),'utf8')
base=['java','-jar',SDK/'support/asc.jar','-AS3','-import',SDK/'lib/redtamarin.abc']
code,log=run(base+[R/'season-stubs.as'],'season-stubs.log');assert code==0,log
harness='''import fok.utils.PlayerListUtil;
for each(var season:int in [18,19,84,856,13]) {
 trace("SEASON "+season+"="+PlayerListUtil.getSeasonString(season));
 PlayerListUtil.generatePlayerNameWithSeason(season*1000000+252371,function(v:Object):void {trace("NAME "+v);},null);
}
trace("EXACT_PRODUCTION_SEASON_METHODS_PASS");'''
(R/'season-probe.as').write_text(harness,'utf8')
code,log=run(base+['-import',R/'season-stubs.abc','-import',R/'PlayerListUtil.abc',R/'season-probe.as'],'season-probe-compile.log');assert code==0,log
code,log=run([SDK/'bin/redshell_dd.exe',R/'season-stubs.abc',R/'PlayerListUtil.abc',R/'season-probe.abc'],'season-probe.log')
print(code,log)
