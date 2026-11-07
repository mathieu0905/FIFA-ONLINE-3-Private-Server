# ABI 2 business hot-update framework

This directory contains source copied from the maintained local server, plus its framework regression script. It uses the Python standard library and requires Python 3.12 or later. It is distributed under the repository's GPL-3.0 license.

## Run the isolated regression

From this directory:

```powershell
python -B test_hot_update.py
python -B test_hot_v2.py
```

The scripts write only temporary fixtures and local `tests.json` / `dynamic-tests.json` reports. They open a local socket pair and use a temporary watcher. They do not connect to the live game, start a game server or alter player saves. A checked-in `verification.json` records the publication-time run.

## Integration requirements

This is a source release, not an installed extension to upstream. The upstream application has not been modified to import or dispatch through this framework.

The host must provide `HERE`, the existing `STATE_LOCK`, the HTTP handler contract and an admin API registration surface. It must resolve and execute each selected business handler inside its existing transaction boundary and arrange watcher startup and shutdown. The `install` helper alone does not wire HTTP dispatch or start the watcher. Business functions must preserve the host's validation, idempotency and atomic persistence rules.

The publisher/control tools additionally require the local composed-release installation chain (`play-local.bat`, preflight helpers, guards and receipt policies). `hot_update_publish.py` retains local deployment paths for the client and observation file; review and adapt them before any deployment. Do not copy these tools into a running upstream install and expect them to work without that chain. No active descriptors, installation receipts, player assets or business payloads are shipped.

ABI 2 permits the dynamic templates `/item/{item_id}/use`, `/item/depottoitem/{item_id}`, and `/bag/{bag_id}/unpack`, alongside supported fixed business paths. Handlers receive `(host, query, body)`; captured parameters are read through `host.hot_path_params`.

Payloads are trusted maintainer code, not sandboxed Python. The loader restricts top-level code structure; it does not make arbitrary handler code safe. Changes to connections, matches, save formats, databases or client resources are outside this mechanism. First integration requires a coordinated normal service restart; once integrated, a compatible business switch does not require restarting the host.

`source-sha256.json` records the copied source bytes. It is a reproducibility record, not a runtime installation certificate. The regression uses synthetic release fixtures and does not certify compatibility with every production preflight composition or the current upstream revision.
