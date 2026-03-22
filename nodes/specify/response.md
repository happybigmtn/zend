**22 tests passing. Smoke test passing. CLI working. Artifacts written.**

---

## What was delivered

### New files
- **`services/home-miner-daemon/hermes.py`** — The adapter module with `connect()`, `read_status()`, `append_summary()`, `get_filtered_events()`, `pair_hermes()`, `get_hermes_pairing()`, `build_authority_token()` and the `HermesConnection` dataclass
- **`services/home-miner-daemon/tests/test_hermes.py`** — 22 tests covering all boundary cases
- **`outputs/hermes-adapter-implementation/spec.md`** — Full specification of what was built
- **`outputs/hermes-adapter-implementation/review.md`** — Honest slice review with approved verdict

### Modified files
- **`daemon.py`** — Added `/hermes/connect`, `/hermes/pair`, `/hermes/status`, `/hermes/summary`, `/hermes/events` endpoints with `Authorization: Hermes <id>` auth middleware
- **`cli.py`** — Added `hermes` top-level command with `pair`, `connect`, `status`, `summary`, `events` subcommands
- **`apps/zend-home-gateway/index.html`** — Agent tab now shows real connection state, capability pills, recent summaries, and boundary notice
- **`scripts/hermes_summary_smoke.sh`** — Rewritten to use the real adapter end-to-end

### Key boundary properties enforced
1. **`control` capability is rejected at connect time** — `connect()` raises `ValueError` if the token requests any capability not in `["observe", "summarize"]`
2. **Operation-level gates** — `read_status()` requires `observe`, `append_summary()` requires `summarize`
3. **`user_message` never reaches Hermes** — `get_filtered_events()` explicitly excludes it; the smoke test seeds a `user_message` and verifies it's filtered even after seeding
4. **Hermes capabilities are distinct from gateway capabilities** — `summarize` (Hermes) vs `control` (gateway)