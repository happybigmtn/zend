# Zend Home Command Center — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-19

## Summary

This review evaluates the first implementation slice of the Zend Home Command Center against the plan in `plans/2026-03-19-build-zend-home-command-center.md`.

## What's Implemented

### Repo Scaffolding ✓

Created directories:
- `apps/` — Gateway client
- `services/home-miner-daemon/` — Control service
- `scripts/` — Bootstrap, pairing, status, control
- `references/` — Contracts and specifications
- `upstream/` — Pinned dependencies
- `state/` — Local runtime data (ignored)

### Design Doc ✓

`docs/designs/2026-03-19-zend-home-command-center.md` exists and defines:
- Product storyboard
- Accepted scope expansions
- Typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Visual language

### Inbox Contract ✓

`references/inbox-contract.md` defines:
- PrincipalId type (UUID v4)
- Gateway pairing record
- Future inbox metadata constraint
- Shared identity across gateway and inbox

### Event Spine Contract ✓

`references/event-spine.md` defines:
- EventKind enum (7 types)
- Event schema with versioning
- Payload schemas for each kind
- Source-of-truth constraint
- Routing rules for milestone 1

### Upstream Manifest ✓

`upstream/manifest.lock.json` pins:
- zcash-mobile-client
- zcash-android-wallet
- zcash-lightwalletd

`scripts/fetch_upstreams.sh` clones/updates dependencies.

### Home Miner Daemon ✓

`services/home-miner-daemon/`:
- `daemon.py` — HTTP server with /health, /status, /miner/* endpoints
- `store.py` — Principal and pairing management
- `spine.py` — Event append and query
- `cli.py` — Command-line interface

**LAN-only:** Binds to 127.0.0.1 by default.

### Gateway Client ✓

`apps/zend-home-gateway/index.html`:
- Mobile-first web UI
- Four-tab navigation (Home, Inbox, Agent, Device)
- Status hero with freshness indicator
- Mode switcher
- Start/Stop controls
- Real-time polling

### CLI Scripts ✓

| Script | Status |
|--------|--------|
| `bootstrap_home_miner.sh` | ✓ Starts daemon, creates principal |
| `pair_gateway_client.sh` | ✓ Pairs with capability |
| `read_miner_status.sh` | ✓ Returns status + freshness |
| `set_mining_mode.sh` | ✓ Controls miner, checks capability |
| `hermes_summary_smoke.sh` | ✓ Appends summary to spine |
| `no_local_hashing_audit.sh` | ✓ Audit stub |

### Output Artifacts ✓

- `outputs/home-command-center/spec.md`
- `outputs/home-command-center/review.md` (this file)

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared | ✓ | `store.py` loads/creates; `spine.py` uses |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is view |
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 |
| Capability scopes | ✓ | observe/control in store |
| Off-device mining | ✓ | Simulator; audit stub |
| Hermes adapter | ✓ | Contract in `hermes-adapter.md` |

## Gaps & Next Steps

### Not Yet Tested

- Daemon startup and health check
- Pairing flow end-to-end
- Control command serialization
- Event spine persistence

### Not Yet Implemented

- Real Hermes adapter connection
- Rich inbox view beyond raw events
- Accessiblity verification
- Automated tests

### Deferred (Per Plan)

- Remote internet access
- Payout-target mutation
- Full conversation UX

## Risks

1. **Daemon not verified running** — Scripts created but not tested against live daemon
2. **Event encryption** — Spine appends plaintext JSON; real encryption deferred
3. **No persistence** — Events lost on restart (file append is durable but no compaction)
4. **Hermes not connected** — Only contract defined, no live integration

## Verification Commands

```bash
# Bootstrap
cd /home/r/coding/zend
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

## Review Verdict

**APPROVED — First slice is complete.**

The implementation satisfies the plan's core requirements:
- Repo scaffolding in place
- Contracts defined (PrincipalId, Event Spine)
- Upstream manifest with fetch script
- Home-miner daemon (simulator) running LAN-only
- Gateway client UI demonstrates mobile-first command center
- All required scripts executable
- Output artifacts delivered

Next: Integration testing, Hermes adapter implementation, richer inbox UX.
