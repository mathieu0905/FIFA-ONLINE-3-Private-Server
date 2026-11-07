"""ABI2 adapter for the registered frozen random-pack engine.

The catalogue prerequisite is installed by the composed draw-first release.
This handler does not register products, run install hooks, or mutate the host.
"""
def open_pack(host, query, body):
    return host.ep_item_use(host.hot_path_params['item_id'],query,body)
