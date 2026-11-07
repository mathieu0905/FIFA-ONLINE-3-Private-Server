"""Portable standard-library inference for the anchor-calibrated GPU model."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import sqlite3
import struct
from features import encode, source_price, local_price, keeper_gate, role_scores, ability_floor


class AnchorValueModel:
    def __init__(self, path=None, expected_sha256=None):
        self.path = Path(path or Path(__file__).parent / 'selected-model.json.gz')
        self.sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if expected_sha256 and self.sha256 != expected_sha256:
            raise ValueError('Anchor model digest differs')
        with gzip.open(self.path, 'rt', encoding='utf8') as file:
            self.model = json.load(file)
        if self.model['schema'] != 2 or self.model['type'] != 'monotone_max_experts':
            raise ValueError('Unsupported calibrated model')
        self.config = self.model['config']
        assert set(self.model['experts']) == {'OUT', 'GK'}
        for expert in self.model['experts'].values():
            if not expert['trees'] or len(expert['features']) != len(expert['constraints']) or any(v != 1 for v in expert['constraints']):
                raise ValueError('Missing positive expert constraints')
            if not math.isfinite(expert['baseline']):
                raise ValueError('Invalid expert baseline')
            for tree in expert['trees']:
                size = len(tree['left_children'])
                if any(len(tree[k]) != size for k in ['right_children','split_indices','split_conditions','split_type']):
                    raise ValueError('Incomplete tree')
                if any(tree['split_type']):
                    raise ValueError('Unexpected nonnumeric tree')
                for i, child in enumerate(tree['left_children']):
                    if child != -1 and not (i < child < size and i < tree['right_children'][i] < size and 0 <= tree['split_indices'][i] < len(expert['features'])):
                        raise ValueError('Invalid tree link or feature')
                    if not math.isfinite(tree['split_conditions'][i]):
                        raise ValueError('Invalid tree number')

    def expert_logs(self, raw):
        logs = {}
        float32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
        for family, expert in self.model['experts'].items():
            values = [float32(v) for v in encode(raw, self.config, family)]
            value = expert['baseline']
            for tree in expert['trees']:
                node = 0
                while tree['left_children'][node] != -1:
                    field = tree['split_indices'][node]
                    threshold = float32(tree['split_conditions'][node])
                    node = tree['left_children'][node] if values[field] < threshold else tree['right_children'][node]
                value += tree['split_conditions'][node]
            logs[family] = value
        return logs

    def log_predict(self, raw):
        logs = self.expert_logs(raw)
        return math.log(source_price(logs['OUT'], logs['GK'], raw, self.config))

    def predict(self, raw):
        logs = self.expert_logs(raw)
        return local_price(logs['OUT'], logs['GK'], raw, self.config)

    def explain(self, raw):
        logs = self.expert_logs(raw)
        gate = keeper_gate(raw, self.config)
        potentials = dict(outfield=math.exp(min(50, logs['OUT'])), keeper=math.exp(min(50, logs['GK'])) * gate)
        return dict(model=self.config['revision'], model_sha256=self.sha256,
                    fair_price_ep=local_price(logs['OUT'], logs['GK'], raw, self.config),
                    source_price_estimate=max(potentials.values()), source_potentials=potentials,
                    active_expert=max(potentials, key=potentials.get), keeper_gate=gate,
                    native_role_potentials=role_scores(raw, self.config), low_price_guard_ep=ability_floor(raw, self.config),
                    identity_season_position_body_labels_used=False, grade_market_premium_applied=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spid', type=int, required=True)
    parser.add_argument('--database', type=Path, default=Path('D:/FO3ID/server/gamedata/fifadb.sqlite'))
    args = parser.parse_args()
    with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM players WHERE spid=?', (args.spid,)).fetchone()
        if row is None:
            parser.error('Unknown SPID')
    print(json.dumps(AnchorValueModel().explain(dict(row)), ensure_ascii=False, indent=2))
