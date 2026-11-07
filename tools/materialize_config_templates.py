"""Generate fresh-install config files; never overwrite an existing directory.

This only prepares text configurations. It does not install game resources,
publish a business payload, start services, or migrate a player's saves.
"""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import secrets


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')).hexdigest()


def materialize(value):
    if isinstance(value, dict):
        result = {k: materialize(v) for k, v in value.items()}
        if result != value and 'hash' in result:
            result['hash'] = digest({k: v for k, v in result.items() if k != 'hash'})
        return result
    if isinstance(value, list):
        return [materialize(v) for v in value]
    return secrets.token_hex(32) if value == '__GENERATE_LOCALLY__' else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', type=Path, default=Path(__file__).resolve().parents[1] / 'enhanced/config-templates')
    parser.add_argument('--output', type=Path, required=True, help='A new directory, never an existing gamedata directory')
    args = parser.parse_args()
    templates, output = args.templates.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(templates):
        parser.error('Output must be a new directory outside the templates')
    configs = {}
    for source in templates.glob('*.json*'):
        if not (source.name.endswith('.json') or source.name.endswith('.json.gz')):
            continue
        if source.name.removesuffix('.gz') in ('state.json', 'shop.json', 'player-import-validation.json'):
            raise ValueError('Private data or live installation certificate found in templates')
        name = 'shop.json' if source.name == 'shop.catalogue.json' else source.name
        if source.name.endswith('.json.gz'):
            # Frozen NPC price/valuation inputs contain no live market DB or
            # player inventory. Keep their exact bytes for their content proofs.
            json.loads(gzip.decompress(source.read_bytes()))
            configs[name] = source.read_bytes()
        else:
            configs[name] = materialize(json.loads(source.read_text('utf8')))
    output.mkdir(parents=True)
    for name, value in configs.items():
        if isinstance(value, bytes):
            (output / name).write_bytes(value)
        else:
            (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
    print(f'Prepared {len(configs)} fresh-install text configurations; no services or saves modified.')


if __name__ == '__main__':
    main()
