"""Reuse the audited callback patch and replay, narrowed to this task's new19."""
from pathlib import Path
import hashlib,subprocess,sys
R=Path(__file__).resolve().parent;O=R/'name-callback';O.mkdir(exist_ok=True)
src=Path('D:/fifaol3/season12-display')
build=(src/'build_callback.py').read_text('utf-8').replace('for season in (12,13,84):','for season in (19,):')
assert build!=(src/'build_callback.py').read_text('utf-8')
(O/'build.py').write_text(build,'utf-8')
replay=(src/'replay_callback.py').read_text('utf-8').replace("'FO3_CUSTOM_SEASON_84':'传奇时刻'","'FO3_CUSTOM_SEASON_84':'传奇时刻','FC_CUSTOM_SEASON_19':'怀旧神兽'").replace('if season in (12,13,84):','if season in (19,):')
(O/'replay.py').write_text(replay,'utf-8')
module=Path('D:/FO3ID/32795/data/ui/libs/Module.big');wanted=hashlib.sha256(module.read_bytes()).hexdigest();assert wanted=='25a5669a8b3f84e949542d07b6064cc6c0afb187a58b8a844dd598c621473d89'
subprocess.run([sys.executable,'-B',str(O/'build.py'),'--out',str(O/'callback-v1'),'--source-sha',wanted],check=True)
subprocess.run([sys.executable,'-B',str(O/'replay.py'),'--candidate',str(O/'callback-v1')],check=True)
