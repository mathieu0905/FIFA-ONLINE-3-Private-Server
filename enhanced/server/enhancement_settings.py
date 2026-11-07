"""Persistent equal-material enhancement ceilings; never reads or writes manager assets."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


def install(hc):
    if getattr(hc, '_enhancement_settings_installed', False):
        return
    path = Path(hc.HERE) / 'gamedata' / 'enhancement_rates.json'
    defaults = tuple(hc.ENHANCE_RATE)
    grades = tuple(str(g) for g in range(1, hc.MAX_GRADE))
    default_percent = {g: round(defaults[int(g)] * 100, 10) for g in grades}

    def validate(rates):
        if not isinstance(rates, dict) or set(rates) != set(grades):
            raise ValueError('请完整填写 +1 至 +' + str(hc.MAX_GRADE - 1) + ' 的成功率')
        for value in rates.values():
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 90:
                raise ValueError('成功率必须是 0 到 90 之间的有限数字')
        return {g: rates[g] for g in grades}

    def disk():
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def revision(raw):
        return hashlib.sha256(raw if raw is not None else json.dumps(default_percent, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def decode(raw):
        if raw is None:
            return dict(default_percent)
        cfg = json.loads(raw)
        if cfg.get('version') != 1 or cfg.get('max_grade') != hc.MAX_GRADE:
            raise ValueError('强化概率配置版本或等级上限不匹配')
        return validate(cfg.get('rates'))

    def apply(rates):
        hc.ENHANCE_RATE = (defaults[0],) + tuple(
            defaults[int(g)] if rates[g] == default_percent[g] else rates[g] / 100
            for g in grades) + (defaults[-1],)

    initial = disk()
    active_rates = decode(initial)
    if initial is not None:
        apply(active_rates)
    active_revision = revision(initial)

    def get_settings(params=None):
        with hc.STATE_LOCK:
            return {'max_grade': hc.MAX_GRADE, 'revision': active_revision,
                    'rates': dict(active_rates), 'defaults': dict(default_percent), 'semantics': 'equal_material_ceiling', 'maximum': 90}

    def set_settings(params):
        nonlocal active_revision, active_rates
        rates = validate(params.get('rates'))
        with hc.STATE_LOCK:
            if params.get('revision') != active_revision or revision(disk()) != active_revision:
                raise ValueError('概率已被其他页面修改，请重新加载后再保存')
            raw = json.dumps({'version': 1, 'max_grade': hc.MAX_GRADE, 'rates': rates},
                             ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(raw)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            apply(rates)
            active_rates = rates
            active_revision = revision(raw)
            return get_settings()

    hc.enhancement_settings_get = get_settings
    hc.enhancement_settings_set = set_settings
    hc._enhancement_settings_installed = True


def register_admin(hc, admin):
    admin.READ_ONLY.add('enhancement')
    admin.API['enhancement'] = hc.enhancement_settings_get
    admin.API['enhancement_set'] = hc.enhancement_settings_set
