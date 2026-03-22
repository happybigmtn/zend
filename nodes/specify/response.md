## Summary

All 6 required tasks completed. Both durable artifacts written.

### What was built

**`services/home-miner-daemon/hermes.py`** — The adapter module (356 lines) with:
- `connect(authority_token)` — JSON token validation, expiration check, capability allowlist enforcement
- `connect_from_pairing(hermes_id)` — pairing-record-based connect (30-day token)
- `pair_hermes(hermes_id, device_name)` — idempotent pairing with `observe` + `summarize`
- `read_status(connection)` — observe-gated miner snapshot
- `append_summary(connection, text, scope)` — summarize-gated spine append
- `get_filtered_events(connection, limit)` — `user_message` excluded, only `hermes_summary` / `miner_alert` / `control_receipt`

**`services/home-miner-daemon/daemon.py`** — Hermes endpoints added:
- `POST /hermes/pair`, `POST /hermes/connect`, `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events`
- `/miner/*` always returns 403 for Hermes (capability boundary enforcement)

**`services/home-miner-daemon/cli.py`** — Hermes subcommands:
- `hermes pair`, `hermes connect`, `hermes status`, `hermes summary`, `hermes events`

**`services/home-miner-daemon/tests/test_hermes.py`** — 23 unit tests (all pass)

### Proof

```
# 15/15 HTTP endpoint tests pass
# 23/23 unit tests pass
# user_message is filtered from Hermes event reads
# control paths always 403 for Hermes
# control capability always rejected in token validation
```