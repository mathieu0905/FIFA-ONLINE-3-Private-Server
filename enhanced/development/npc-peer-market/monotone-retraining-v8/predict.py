"""Portable inference for the newly trained model. No GPU/ML runtime required."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import sqlite3
import struct
from features import encode, ability_floor, local_price, role_rating


class MonotoneValueModel:
    def __init__(self, path=None, expected_sha256=None):
        self.path = Path(path or Path(__file__).parent / 'selected-model.json.gz')
        self.sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if expected_sha256 is not None and self.sha256 != expected_sha256:
            raise ValueError('Trained model hash mismatch')
        with gzip.open(self.path, 'rt', encoding='utf8') as f:
            self.model = json.load(f)
        if self.model['schema'] != 1 or self.model['type'] != 'monotone_role_xgboost':
            raise ValueError('Unsupported trained model')
        self.config = self.model['config']
        for family, model in self.model['families'].items():
            if not model['trees'] or len(model['features']) != len(model['monotone_constraints']):
                raise ValueError('Incomplete trained family: ' + family)
            if not math.isfinite(model['baseline']):
                raise ValueError('Invalid model baseline')
            for tree in model['trees']:
                count = len(tree['left_children'])
                if any(len(tree[k]) != count for k in ('right_children', 'split_indices', 'split_conditions', 'split_type')):
                    raise ValueError('Malformed numeric tree')
                if any(tree['split_type']):
                    raise ValueError('Unexpected categorical tree: encoder uses explicit one-hot features')
                for i, left in enumerate(tree['left_children']):
                    right = tree['right_children'][i]
                    if left != -1 and not (i < left < count and i < right < count):
                        raise ValueError('Cyclic or out-of-bounds tree')
                    if left != -1 and not 0 <= tree['split_indices'][i] < len(model['features']):
                        raise ValueError('Invalid split column')
                    if not math.isfinite(tree['split_conditions'][i]):
                        raise ValueError('Nonfinite numeric tree')

    def log_predict(self, raw):
        family, values = encode(raw, self.config)
        # Booster features and split thresholds are float32; explicitly retain
        # their boundary semantics in this standard-library inference path.
        values = [struct.unpack('<f', struct.pack('<f', v))[0] for v in values]
        model = self.model['families'][family]
        output = model['baseline']
        for tree in model['trees']:
            node = 0
            while tree['left_children'][node] != -1:
                value = values[tree['split_indices'][node]]
                threshold = struct.unpack('<f', struct.pack('<f', tree['split_conditions'][node]))[0]
                node = tree['left_children'][node] if value < threshold else tree['right_children'][node]
            output += tree['split_conditions'][node]
        return output

    def predict(self, raw):
        return local_price(self.log_predict(raw), raw, self.config)

    def explain(self, raw):
        log = self.log_predict(raw)
        return dict(model=self.config['revision'], model_sha256=self.sha256,
                    family=encode(raw, self.config)[0], native_role_rating=role_rating(raw, self.config),
                    source_price_estimate=math.exp(min(50, log)), source_price_divisor=self.config['source_price_divisor'],
                    low_denomination_guard_ep=ability_floor(raw, self.config),
                    fair_price_ep=local_price(log, raw, self.config),
                    identity_season_animation_trait_ids_used=False,
                    grade_and_market_premium_applied=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spid', type=int, required=True)
    args = parser.parse_args()
    with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM players WHERE spid=?', (args.spid,)).fetchone()
        if row is None:
            parser.error('Unknown native SPID')
    print(json.dumps(MonotoneValueModel().explain(dict(row)), ensure_ascii=False, indent=2))
