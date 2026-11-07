def market_supply_activate(host, query, body):
    import copy
    import json
    import time
    from market_supply_settings import validate
    request=json.loads(body or b'{}')
    settings=validate(request.get('settings'))
    keys={quality+'_'+str(grade) for quality in ('low','mid','high','elite') for grade in range(11,21)}
    if set(settings['rare_overrides'])!=keys or any(rule['period_seconds']!=300 or rule['slots']!=5 for rule in settings['rare_overrides'].values()):
        raise ValueError('Minute activation requires exactly five independent one-minute slots per five-minute batch in every rare tier')
    engine=host.market_engine
    control=engine.supply_settings
    raw=(json.dumps(settings,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf8')
    target=control.digest(raw)
    with host.STATE_LOCK:
        current=control.get()
        state=host._state()
        if not engine.has_active(state):raise ValueError('No active manager; market activation deferred')
        market=state.get('market_simulation')
        if not market:raise ValueError('Market has not initialized')
        if current['active_revision']==target and market.get('supply_activation_revision')==target:
            return host._json(dict(result=True,replayed=True,revision=target))
        if request.get('revision')!=current['revision']:raise ValueError('Configuration changed; reload before activation')
        old_settings=copy.deepcopy(current['settings'])
        saved=control.set(dict(revision=current['revision'],settings=settings))
        try:
            stamp=time.time()
            legacy=market.setdefault('legacy_supply',[])
            moved=0
            for tier in engine.supply_plan():
                previous=market['rare_books'].get(tier['key'])
                if previous:
                    for row in previous['rows']:
                        archived=copy.deepcopy(row)
                        # Visible quotes and consumed history retain their exact values.
                        # Unquoted future opportunities are cancelled by the new policy.
                        if archived.get('price') is None:archived['count']=0
                        legacy.append(archived)
                        moved+=1
                period=tier['period']
                boundary=int(stamp//period)*period
                # Existing stock is moved above before the existing generator runs.
                # An expired empty batch lets it create this five-minute interval
                # under a new epoch; no classes, worker or global hooks are changed.
                market['rare_books'][tier['key']]=dict(epoch=(previous or {}).get('epoch',0),start=boundary-period,
                    period=period,slots=tier['slots'],chance=tier['chance'],pool_size=tier['pool_size'],rows=[])
            engine.rare_stock(state,stamp)
            market['supply_activation_revision']=saved['active_revision']
            host._save(state)
        except Exception:
            # Save may have committed before returning an I/O error. Its receipt
            # decides whether to retain the new configuration; never replay state.
            committed=host._state().get('market_simulation',{}).get('supply_activation_revision')==saved['active_revision']
            if committed:return host._json(dict(result=True,replayed=False,committed=True,revision=saved['active_revision']))
            control.set(dict(revision=saved['revision'],settings=old_settings))
            raise
        return host._json(dict(result=True,replayed=False,revision=saved['active_revision'],check_seconds=60,
            batch_seconds=300,preserved_rows=moved,policy='one independent opportunity per minute and tier; no weekly wait'))
