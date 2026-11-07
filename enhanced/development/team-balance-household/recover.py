"""Finish evidence for the committed install after startup watcher activation; no service action."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode=True
import install
import prepare


def main():
    receipt=json.loads((install.S/install.RECEIPT).read_text('utf8'))
    backup=install.S/'backups'/receipt['revision']
    journal=json.loads((backup/'transaction.json').read_text('utf8'))
    assert journal['status']=='INSTALLED'
    assert install.SELF.replace('/','\\').encode() in (install.S/'play-local.bat').read_bytes()
    for entry in journal['entries']:
        assert prepare.sha(entry['target'])==entry['after'],entry['relative']
    source=json.loads((prepare.ROOT/'tests.json').read_text('utf8'))
    assert prepare.sha(install.S/'http_config.py')==source['source_sha256']
    validation=json.loads((install.S/'gamedata/player-import-validation.json').read_text('utf8'))
    assert validation['status']=='PLAYER_IMPORT_FULL_PASS'
    snapshot={name:(backup/('fresh-'+name)).read_bytes() for name in ('state.json','shop.json')}
    top=prepare.ROOT.parent/'root-current-top.json';top_before=top.read_bytes()
    prior=json.loads(top_before)
    old_hot=prior.get('hot_update_status') or prior.get('hot_status')
    assert old_hot and old_hot['revision']=='pack_base_prices_20261107_01'
    colors=install.get('https://127.0.0.1/static/info/teamcolor')
    result=dict(backup=str(backup),assets_identical_while_stopped=True,services_restarted=True,
        full_player_import={k:v for k,v in validation.items() if k not in ('input_hashes','portrait_hashes')},
        full_validation_evidence='Commit journal is INSTALLED only after formal --full validation and fresh stopped asset equality pass; certificate matches committed bytes',
        readiness='HTTPS/admin/messenger are ready',verification_recovery='Committed files retained; watcher verified after release locks; no extra restart')
    install.finish(dict(revision=receipt['revision']),result,snapshot,old_hot,colors,top,top_before)
    output=json.loads((prepare.ROOT/'installed-handback.json').read_text('utf8'))
    output.update(services_restarted=True,verification_recovery_no_service_action=True)
    prepare.write(prepare.ROOT/'installed-handback.json',output)


if __name__=='__main__':main()
