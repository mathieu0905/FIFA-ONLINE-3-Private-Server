def ep_itemnames(query, body):
    """GET /static/db/ITEMNAMES {itemid: {ind, kor}}: the reward panels' (and Upgrade's) item names."""
    ids = [EP_ITEM, ES_ITEM, *PACKS, *ITEMS, *PACKAGES, *MONTHLY]
    return _json({str(i): {"ind": item_def(i)["name"], "kor": item_def(i)["name"]} for i in ids})
