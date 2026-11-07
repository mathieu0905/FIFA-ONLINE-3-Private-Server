"""Optional +20 progression profile; install after http_config definitions, before serving."""

def install(hc):
    if hc.MAX_GRADE <= 10 or getattr(hc, '_enhancement20_profile_installed', False):
        return
    # +0..+10 preserve existing balance. Breakthrough levels add 2 attributes each.
    hc.GRADE_BOOST = hc.GRADE_BOOST[:11] + tuple(24 + 2 * (g - 10) for g in range(11, hc.MAX_GRADE + 1))
    rates = (0.15, 0.135, 0.12, 0.10, 0.085, 0.07, 0.055, 0.04, 0.03, 0.02)
    hc.ENHANCE_RATE = hc.ENHANCE_RATE[:10] + rates[:hc.MAX_GRADE - 10] + (0.0,)
    original_add = hc.add_player
    def add_player(team, spid, grade=1):
        g = int(grade)
        if isinstance(grade, bool) or float(grade) != g or not 0 <= g <= hc.MAX_GRADE:
            raise ValueError("player grade outside configured range")
        return original_add(team, spid, g)
    hc.add_player = add_player

    def guard_market(name):
        original = getattr(hc, name)
        def checked(*args):
            try:
                grade = int(args[1])
                valid = 1 <= grade <= hc.MAX_GRADE and float(args[1]) == grade
            except (TypeError, ValueError, OverflowError):
                valid = False
            if not valid:
                return hc._json({"result": False, "reason": "INVALID_PARAM"})
            return original(*args)
        setattr(hc, name, checked)
        hc.ROUTES[:] = [(pattern, checked if fn is original else fn) for pattern, fn in hc.ROUTES]
    guard_market('ep_transfer_purchase')
    guard_market('ep_transfer_price')
    hc._enhancement20_profile_installed = True
