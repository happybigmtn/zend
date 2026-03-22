# Documentation & Onboarding — Review

**Status:** Ready for implementation
**Reviewed:** 2026-03-22
**Reviewer model:** claude-opus-4-6

## Verdict

**CONDITIONALLY READY.** The plan (`plans/2026-03-19-build-zend-home-command-center.md`)
is internally consistent and its Concrete Steps use correct device names (`alice-phone`).
However, the documentation milestones (milestones 4 and 5 in the plan) reference
phantom endpoints and an incorrect env var. These must be corrected before any of the
five documentation deliverables are written, otherwise the docs will describe APIs that
do not exist.

The `spec.md` companion artifact documents the corrected ground truth and unblocks
implementation directly.

## Plan Accuracy

### What the Plan Gets Right

| Claim | Verification |
|-------|-------------|
| Bootstrap creates `alice-phone` pairing | `bootstrap_home_miner.sh` calls `cli.py bootstrap --device alice-phone` |
| `./scripts/pair_gateway_client.sh --client alice-phone` pairs observe | `pair_gateway_client.sh` → `cli.py pair --device $CLIENT --capabilities $CAPABILITIES` |
| Daemon binds to `127.0.0.1` | `daemon.py:34`: `BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')` |
| Scripts live in `scripts/` | Confirmed — all 7 scripts present and working |
| `fetch_upstreams.sh` requires `upstream/manifest.lock.json` | Script reads `upstream/manifest.lock.json`; file is missing |

### What the Plan Gets Wrong (in documentation milestones)

| Error | Plan Says | Reality | Fix Required |
|-------|-----------|---------|-------------|
| Phantom endpoint | Documents `GET /spine/events` | Not implemented. Events are `cli.py events`. | Remove from API reference. |
| Phantom endpoint | Documents `GET /metrics` | Not implemented. No metrics surface. | Remove from API reference. |
| Phantom endpoint | Documents `POST /pairing/refresh` | Not implemented. Pairing is CLI-only. | Remove from API reference. |
| Phantom env var | Documents `ZEND_TOKEN_TTL_HOURS` | Does not exist in codebase. | Remove from operator quickstart. |
| Test command | `python3 -m pytest services/home-miner-daemon/ -v` works | No test files exist. | Do not include in README. |
| Encryption claim | Implies event spine payloads are encrypted | `spine.py` writes plaintext JSON. | State plaintext in architecture doc. |

---

## Security Assessment

### Finding 1 — HTTP endpoints are unauthenticated (CRITICAL for docs)

`daemon.py:168-200` handles all HTTP requests with zero authentication. The capability
model (`observe`/`control`) is enforced only in `cli.py:46-54` (status/events reads)
and `cli.py:131-139` (control writes). Any process on the network that can reach
`127.0.0.1:8080` can start, stop, or reconfigure the miner via `curl`.

**Documentation must state explicitly:** All HTTP endpoints are unauthenticated.
Capability checks are a CLI-layer convention, not enforced by the daemon itself.
Changing `ZEND_BIND_HOST` to a LAN IP or `0.0.0.0` exposes full unauthenticated
control to every device on that network.

### Finding 2 — Pairing tokens are not validated (HIGH for docs)

`store.py:86-89` — `create_pairing_token()` sets `expires` to the current timestamp,
meaning every token is instantly expired. `token_used` is never set to `True` anywhere
in the codebase. `token_expires_at` is never checked on use.

Pairing is effectively name-based: call `pair_client("device-name", ["observe"])`
and the device is paired. No secret exchange, no time-window, no challenge-response.

**Documentation must state:** Pairing is a local bookkeeping operation, not a
cryptographic trust ceremony.

### Finding 3 — Pairing store is full-rewrite (MEDIUM for ops docs)

`store.py:80-83` — `save_pairings()` overwrites `pairing-store.json` entirely.
A crash during write (e.g., power loss, OOM kill) can corrupt all pairing records.
The event spine (`spine.py:62-65`) correctly uses append-only I/O.

**Recovery:** If `pairing-store.json` is corrupt, delete it and re-pair all devices.

### Finding 4 — CLI `--client` flag is optional on read paths (LOW for docs)

`cli.py:46-47` — `cmd_status` checks capabilities only `if args.client`. Running
`cli.py status` without `--client` returns miner status with no authorization check.
Same for `cli.py events`. This is arguably correct (the daemon endpoint itself is
unauthenticated) but documentation should be explicit: `--client` gates the CLI-layer
capability check, not the underlying daemon access.

### Finding 5 — No capability upgrade path (LOW for ops docs)

`store.py:98-101` — `pair_client()` raises `ValueError` if the device name already
exists. There is no way to upgrade `alice-phone` from `observe` to `observe,control`
without manually editing `pairing-store.json`. The quickstart must account for this:
use a new device name when pairing with control.

### Finding 6 — Event spine has no size bound (LOW for ops docs)

`spine.py` appends indefinitely to `event-spine.jsonl`. No compaction, rotation, or
size check exists. On long-running systems this file grows without limit. Recommend
periodic manual rotation or truncation in operator documentation.

---

## Remaining Blockers

### Must Fix Before Writing Any Deliverable

1. **Remove phantom endpoints from the API reference.** Document only the 5 actual
   endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`.

2. **Remove `ZEND_TOKEN_TTL_HOURS`** from the operator quickstart env var table.

3. **Remove the pytest invocation** from any README draft. No tests exist.

4. **State plaintext explicitly.** The architecture doc must say "encryption is
   contractual; milestone 1 stores plaintext JSON in the event spine."

### Should Fix (Honesty Improvements)

5. **Add `upstream/manifest.lock.json`.** `fetch_upstreams.sh` fails without it.
   The script is otherwise working and idempotent.

6. **Document the duplicate-name pairing limitation** prominently in the operator
   quickstart. New contributors will hit it within 5 minutes.

7. **Add a `GET /events` HTTP endpoint** so the gateway client HTML can fetch
   events without going through the CLI. Currently the HTML has no way to display
   inbox contents.

### Nice to Have

8. Add `--upgrade` or `--update-capabilities` to `cli.py pair` to allow
   re-pairing an existing device name.

9. Add file-locking or atomic-write for `pairing-store.json` to prevent
   corruption on crash.

10. Add a test suite so the README can honestly reference `pytest`.

---

## Verified Working Commands

```bash
# Start daemon, bootstrap principal, pair alice-phone (observe)
cd /path/to/zend
./scripts/bootstrap_home_miner.sh

# Verify health
curl -s http://127.0.0.1:8080/health
# => {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Read status
curl -s http://127.0.0.1:8080/status
# => {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}

# Read status via CLI (with capability check)
./scripts/read_miner_status.sh --client alice-phone

# Pair new device with control
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control

# Start miner
./scripts/set_mining_mode.sh --client alice-phone --action start

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

## What Can Ship Today

All five documentation deliverables can be written immediately using the corrected
ground truth in `spec.md`. No code changes are required. The deliverables will be
honest about:
- The 5 real endpoints and their lack of HTTP auth
- The plaintext event spine
- The CLI-layer-only capability model
- The missing test suite
- The duplicate-device-name pairing limitation
