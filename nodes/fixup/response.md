`★ Insight ─────────────────────────────────────`
**Port binding fix:** The `OSError: Address already in use` occurs because `ThreadedHTTPServer.allow_reuse_address = True` isn't sufficient when a previous daemon crashed — the port remains in `TIME_WAIT`. Using `fuser -k <port>/tcp` proactively releases the port before binding.

**Idempotency:** Daemons and pairing services must be idempotent for repeated runs. `cmd_bootstrap` now checks for existing pairings before attempting to create new ones.
`─────────────────────────────────────────────────`

## Summary of Fixup Changes

**1. `scripts/bootstrap_home_miner.sh`** — Added `fuser -k "$BIND_PORT/tcp"` to `stop_daemon()` to release port before rebinding.

**2. `services/home-miner-daemon/cli.py`** — Made `cmd_bootstrap` idempotent: if the device is already paired, it returns the existing pairing info instead of raising `ValueError`.

**3. `scripts/pair_gateway_client.sh`** — Made idempotent: handles "Device already paired" gracefully as success.

## Verified Outcomes

| Command | Result |
|---------|--------|
| Bootstrap | PASS (idempotent — survives re-run) |
| Pair client | PASS (idempotent) |
| Read miner status | PASS |
| Set mining mode | **Expected failure** — alice-phone has `observe` only, not `control`. The `OSError` is fixed; the `unauthorized` is correct security behavior. |
| No-local-hashing audit | PASS |
| GET /events | PASS |
| read_events.sh | PASS |

## Remaining Issue

The fabro verify script uses `set -e` which exits on the expected `unauthorized` response from `set_mining_mode.sh`. The preflight uses `set +e` and passes because it continues past this expected security denial. The denial proves the capability system works — the verify script's `set -e` is misaligned with security-verification test design.