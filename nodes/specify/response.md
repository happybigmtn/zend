## Summary

I've implemented the Hermes adapter for the Zend daemon. Here's what was created:

### New Files
- **`services/home-miner-daemon/hermes.py`** — The Hermes adapter module implementing:
  - `HermesConnection` and `HermesPairing` dataclasses
  - `pair_hermes()` — Creates Hermes pairings with observe+summarize capabilities
  - `connect()` — Validates authority tokens and establishes connections
  - `read_status()` — Reads miner status (requires observe)
  - `append_summary()` — Appends summaries to event spine (requires summarize)
  - `get_filtered_events()` — Returns events excluding user_message
  - Capability checking and boundary enforcement

- **`services/home-miner-daemon/tests/test_hermes.py`** — 18 test cases covering:
  - Token validation (valid, invalid, expired)
  - Capability checking (with/without observe, summarize)
  - Control rejection
  - Event filtering
  - Idempotent pairing
  - Summary persistence

### Modified Files
- **`services/home-miner-daemon/daemon.py`** — Added Hermes endpoints:
  - `POST /hermes/pair` — Create Hermes pairing
  - `POST /hermes/connect` — Establish connection
  - `GET /hermes/status` — Read miner status via adapter
  - `POST /hermes/summary` — Append summary
  - `GET /hermes/events` — Read filtered events
  - Control endpoint rejection for Hermes auth

- **`services/home-miner-daemon/cli.py`** — Added Hermes subcommands:
  - `hermes pair`, `hermes connect`, `hermes status`, `hermes summary`, `hermes events`

- **`apps/zend-home-gateway/index.html`** — Updated Agent tab with:
  - Real connection state display
  - Capability pills
  - Connection timestamp
  - Recent Hermes summaries

### Output Artifacts
- **`outputs/hermes-adapter-implementation/spec.md`** — Implementation specification
- **`outputs/hermes-adapter-implementation/review.md`** — Code review with approval

### Test Results
```
18 passed in 0.05s
```

All acceptance criteria are met:
- ✓ Hermes can pair with observe+summarize capabilities
- ✓ Hermes can connect with valid authority token
- ✓ Hermes can read miner status
- ✓ Hermes can append summaries to event spine
- ✓ Hermes CANNOT issue control commands (403)
- ✓ Hermes CANNOT read user_message events (filtered)
- ✓ Agent tab shows real connection state