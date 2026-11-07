"""Prevent engine-only season-0 templates from entering user-owned card inventories."""
import functools
from contextlib import closing


def install(hc):
    if getattr(hc, '_season_card_guard_installed', False):
        return
    import admin

    # Keep every language key set aligned. The server admin's Chinese view is the
    # primary user-facing target; other views receive the explicit English fallback.
    message = 'Engine templates are not season cards. Select a valid season-card SPID.'
    for lang, table in admin.I18N.items():
        table['e_engine_template'] = ('这是引擎模板，不是可用赛季卡，请选择带赛季的球员卡 SPID。'
                                      if lang == 'zh' else message)

    def season_spid(value):
        spid = admin.as_int(value, 1, 10 ** 9, 'spid')
        if spid < 1_000_000:
            raise admin.AdminError('e_engine_template')
        return spid

    def search(params):
        q = str(params.get('q') or '').strip()
        if len(q) < 2:
            return {'rows': []}
        with closing(hc._db()) as connection:
            rows = connection.execute(f'''SELECT p.spid, COALESCE(n.full_eng, n.full, n.short),
                       {hc.POSOVR}, p.preferredposition1
                FROM players p JOIN nameseng n ON n.playerid=p.playerid
                WHERE p.spid >= 1000000 AND
                    (n.full LIKE ?1 OR n.short LIKE ?1 OR n.full_eng LIKE ?1 OR n.short_eng LIKE ?1)
                ORDER BY 3 DESC LIMIT 60''', (f'%{q}%',)).fetchall()
        return {'rows': [{'spid': s, 'name': name, 'season': s // 1000000,
                          'ovr': ovr, 'pos': admin.POS_NAMES[pos] if 0 <= pos < 28 else '?',
                          'market': hc.on_market(s), 'price': hc.card_price(s)}
                         for s, name, ovr, pos in rows]}

    for name in ('player_add', 'bag_send'):
        original = admin.API[name]

        def guarded(params, _original=original):
            if params.get('spid'):
                season_spid(params['spid'])
            return _original(params)

        admin.API[name] = functools.wraps(original)(guarded)
    admin.search = search
    admin.API['search'] = search
    # This build has no editable-SPID endpoint. Any later endpoint must use
    # this validator rather than accepting a names-table hit as a season card.
    hc.validate_season_card_spid = season_spid
    hc._season_card_guard_installed = True
