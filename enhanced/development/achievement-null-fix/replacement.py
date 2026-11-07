def ep_itemnames(query, body):
    """Complete ITEMNAMES locales required by native reward tooltip consumers."""
    ids = [EP_ITEM, ES_ITEM, *PACKS, *ITEMS, *PACKAGES, *MONTHLY]
    locales = ("ind", "kor", "eng", "chi", "tha", "vie", "tai")
    names = {}
    for i in ids:
        name = item_def(i)["name"]
        names[str(i)] = {locale: name for locale in locales}
    return _json(names)
