"""Compose a new exact-file top layer without changing any historical receipt."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

server = Path(r'D:\FO3ID\server')
backup = server / 'backups/enhancement-settings-20261106-194738'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

parent_path = server / 'patches/exp-selection-installed.json'
parent_receipt = server / 'patches/exp-selection-receipt.json'
parent = read(parent_path)
assert read(parent_receipt)['manifest_sha256'] == sha(parent_path)
changed = {'http_config.py':'http_config.py', 'admin.py':'admin.py', 'admin/index.html':'index.html'}
roots = {'server':server, 'client':Path(parent['client'])}
for row in parent['guards']:
    target = roots[row['root']] / row['relative']
    if row['root'] == 'server' and row['relative'] in changed:
        assert sha(backup / changed[row['relative']]) == row['sha256'], row['relative']
    else:
        assert sha(target) == row['sha256'], str(target)
for policy in parent.get('composition',{}).get('receipt_policies',[]):
    receipt = read(roots[policy['root']] / policy['relative'])
    assert {k:v for k,v in receipt.items() if k!='native_status'} == policy['installation_fields']

launcher = server / 'play-local.bat'
shutil.copy2(launcher, backup / 'play-local.bat')
launcher_raw = launcher.read_bytes()
old_call = b'patches\\exp_selection_preflight.py'
assert launcher_raw.count(old_call) == 1
new_launcher = launcher_raw.replace(old_call, b'patches\\enhancement_settings_preflight.py')
preflight = (server / 'patches/exp_selection_preflight.py').read_text(encoding='utf-8')
preflight = preflight.replace('exp-selection', 'enhancement-settings').replace('exp_selection', 'enhancement_settings').replace('EXP_SELECTION', 'ENHANCEMENT_SETTINGS')
preflight = preflight.replace("('server','experience_levels.py')", "('server','experience_levels.py'),('server','enhancement_settings.py'),('server','admin.py'),('server','admin/index.html'),('server','http_config.py')")
new_preflight = server / 'patches/enhancement_settings_preflight.py'
assert not new_preflight.exists()
new_preflight.write_text(preflight, encoding='utf-8')
launcher.write_bytes(new_launcher)
guards = copy.deepcopy(parent['guards'])
update_paths = set(changed) | {'play-local.bat'}
for row in guards:
    if row['root'] == 'server' and row['relative'] in update_paths:
        row['parent_sha256'] = row['sha256']
        row['sha256'] = sha(server / row['relative'])
for relative in ('enhancement_settings.py', 'patches/enhancement_settings_preflight.py',
                 'patches/exp-selection-installed.json', 'patches/exp-selection-receipt.json'):
    assert not any(r['root']=='server' and r['relative']==relative for r in guards)
    guards.append({'root':'server','relative':relative,'sha256':sha(server / relative)})
composition = copy.deepcopy(parent.get('composition',{}))
composition.setdefault('ancestry',[]).append({'layer':'enhancement-settings','base_revision':parent['revision'],
                                           'runtime_status':'PENDING_USER_RESTART','native_status':'NOT_VERIFIED'})
manifest = {'schema':1,'revision':'enhancement-settings-20261106-194738','client':parent['client'],
            'guards':guards,'composition':composition,'state_shop_replaced':False,
            'mutable_configuration':'gamedata/enhancement_rates.json',
            'runtime_status':'PENDING_USER_RESTART','native_status':'NOT_VERIFIED'}
manifest_path = server / 'patches/enhancement-settings-installed.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
receipt_path = server / 'patches/enhancement-settings-receipt.json'
receipt_path.write_text(json.dumps({'status':'INSTALLED_ENHANCEMENT_SETTINGS','revision':manifest['revision'],
    'manifest_sha256':sha(manifest_path),'state_shop_replaced':False,'backup':str(backup)},indent=2),encoding='utf-8')
spec = importlib.util.spec_from_file_location('new_top_preflight',new_preflight)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.preflight()
result['runtime_status'] = 'PENDING_USER_RESTART'
result['files_changed'] = {p:sha(server/p) for p in sorted(update_paths|{'enhancement_settings.py',
    'patches/enhancement_settings_preflight.py','patches/enhancement-settings-installed.json','patches/enhancement-settings-receipt.json'})}
Path(__file__).with_name('installation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
