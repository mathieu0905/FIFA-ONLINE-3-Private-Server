"""Exercise the installed preparation pipeline with authentic Saka source files.

Writes workspace build artifacts only. No game, fixture, card or state mutation.
"""
import json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parent;S=pathlib.Path('D:/FO3ID/server');C=pathlib.Path('D:/FO3ID/32795')
catalog=json.loads(pathlib.Path('D:/FO3QA/modern_player_integration_v2/model19-v4/model_catalog24.json').read_text('utf8'));p=next(p for p in catalog['players'] if p['playerid']==246669)
skill=next(p for p in json.loads((R/'built/build.json').read_text('utf8'))['skills'] if p['playerid']==246669)
spec=dict(schema=1,players=[dict(playerid=246669,spid=13246669,name='Saka',replace_existing=True,source_rig='FIFA14_Switch',source_skill_stars=skill['stars'],files={n:dict(path=v['path'],sha256=v['sha256']) for n,v in p['acquired_model']['required_files'].items()})])
(R/'prepare-smoke-spec.json').write_text(json.dumps(spec,indent=2),encoding='utf8')
command=[sys.executable,'-B',str(S/'tools/player_import/prepare.py'),'--spec',str(R/'prepare-smoke-spec.json'),'--server',str(S),'--client',str(C),'--database',str(S/'gamedata/fifadb.sqlite'),'--data0',str(C/'data/data_0.big'),'--registry',str(S/'gamedata/custom_rosters.json'),'--imports',str(S/'gamedata/player-imports.json'),'--output',str(R/'prepare-smoke-artifacts')]
r=subprocess.run(command,capture_output=True,text=True,encoding='utf8',errors='replace',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
(R/'prepare-smoke.log').write_text(r.stdout+r.stderr,encoding='utf8')
if r.returncode:raise RuntimeError(r.stderr)
result=json.loads(r.stdout);assert result['status']=='PREPARED_FULL_PASS_NOT_INSTALLED'
(R/'prepare-smoke.json').write_text(json.dumps(dict(status='PASS',result=result,formal_written=False,state_shop_written=False,description='Installed pipeline with authentic FIFA14 Saka inputs, native upsert, mesh conversion, Lua route, archive rebuilding and full guard'),indent=2),encoding='utf8');print(json.dumps(result))
