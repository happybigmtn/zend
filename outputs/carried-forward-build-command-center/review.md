# Zend Home Command Center — Carried Forward Review

**Status:** Honest First Slice Review
**Generated:** 2026-03-22
**Lane:** `carried-forward-build-command-center`

## Verdict

**APPROVED — First honest slice is complete. Production-ready milestone 1 requires automated tests, the Hermes adapter, and encrypted inbox UX.**

## What Was Achieved

### Repo scaffolding — ✓ Complete

```
apps/zend-home-gateway/        — Mobile-first HTML client
services/home-miner-daemon/    — LAN-only Python daemon
scripts/                       — Bootstrap, pairing, status, control, audit
references/                    — 6 reference contracts
upstream/                      — Pinned dependency manifest
state/                         — Local runtime (gitignored)
```

### Reference contracts — ✓ All 6 defined

| Contract | Key constraint |
|----------|----------------|
| `inbox-contract.md` | Shared `PrincipalId` across gateway and future inbox |
| `event-spine.md` | Spine is source of truth; inbox is derived view |
| `error-taxonomy.md` | 9 named error classes with user-facing copy |
| `hermes-adapter.md` | Adapter interface and authority scope |
| `observability.md` | Structured events and metrics inventory |
| `design-checklist.md` | Design system → implementation checklist |

### Daemon — ✓ Implemented

- `daemon.py`: HTTP server, binds `127.0.0.1:8080`, 5 endpoints
- `store.py`: `PrincipalId` creation, pairing records, capability scoping
- `spine.py`: Append-only JSONL event spine
- `cli.py`: CLI interface
- **Known issue:** `token_used` flag in `store.py` is never set to `True`

### Gateway client — ✓ Design system compliant

- Typography: Space Grotesk / IBM Plex Sans / IBM Plex Mono
- Colors: Basalt, Slate, Moss, Amber, Signal Red
- Four-tab navigation (Home, Inbox, Agent, Device)
- Status hero with freshness indicator
- Mode switcher, start/stop controls
- Loading skeletons, warm empty states, 44×44px touch targets

### Scripts — ✓ All executable

| Script | Status |
|--------|--------|
| `bootstrap_home_miner.sh` | ✓ Works |
| `pair_gateway_client.sh` | ✓ Works |
| `read_miner_status.sh` | ✓ Works |
| `set_mining_mode.sh` | ✓ Works |
| `hermes_summary_smoke.sh` | ✓ Works |
| `no_local_hashing_audit.sh` | ⚠ Stub only |

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| `PrincipalId` shared across gateway and inbox | ✓ | `store.py` creates; `spine.py` references |
| Event spine source of truth | ✓ | `spine.py` appends JSONL; inbox is derived view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1` |
| Capability scopes (observe/control) | ✓ | Enforced in `cli.py` and client |
| Off-device mining | ✓ | Simulator backend |
| Hermes adapter contract | ✓ | Defined in `hermes-adapter.md` |

## Critical Gaps

### 1. Token replay not enforced — High

`store.py` sets `token_used=False` but no code path ever sets it to `True`. A replayed pairing token will succeed silently.

**Fix:** Set `token_used=True` when a token is first consumed. Add a test that replays a consumed token and expects `PairingTokenReplay`.

### 2. Automated tests missing — High

No test files exist. The following must be covered:

- Token replay (consumed token rejected)
- Expired token rejection
- Observe-only client cannot issue control
- Stale `MinerSnapshot` flagged correctly
- Conflicting in-flight control commands
- Daemon restart and paired-client recovery
- Trust-ceremony state transitions
- Hermes adapter boundaries

**Reference:** Plan items in `plans/2026-03-19-build-zend-home-command-center.md`:
  - "Add automated tests for replayed pairing tokens, stale snapshots, controller conflicts, restart recovery, and audit false positives or negatives"
  - "Add tests for trust-ceremony state, Hermes delegation boundaries, event spine routing, inbox receipt behavior, and accessibility-sensitive states"

### 3. Hermes adapter not implemented — Medium

`references/hermes-adapter.md` defines the contract. No implementation exists. The "Agent" tab in the gateway client shows an empty state.

**Required:** `HermesAdapter` class with `connect()`, `readStatus()`, `appendSummary()`, `getScope()`.

### 4. Encrypted operations inbox UX partial — Medium

Event spine appends work, but the "Inbox" tab renders raw JSON event objects. No real encryption, no `ReceiptCard` components, no grouped view.

**Required:** Symmetric encryption layer, `ReceiptCard` rendering per event kind, warm empty states.

### 5. LAN-only not formally verified — Medium

Daemon binds `127.0.0.1` but no test proves this or rejects `0.0.0.0` binding.

**Required:** At minimum, a startup verification that binds to only expected interfaces.

### 6. Gateway proof transcripts not documented — Medium

No `references/gateway-proof.md` with exact commands and expected outputs.

**Required:** End-to-end proof transcript covering bootstrap → pair → status → control → audit.

## Estimated Remaining Work

| Gap | Effort |
|-----|--------|
| `token_used` enforcement | 1–2 hours |
| Automated tests | 2–3 days |
| Hermes adapter | 2–3 days |
| Inbox UX | 2–3 days |
| LAN-only verification | 1 day |
| Gateway proof transcripts | 1 day |

**Total remaining:** ~9–13 days. Approximately 40% of total milestone effort.

## Verification Commands

```bash
# Bootstrap
cd /home/r/coding/zend
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode (requires control capability)
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# View events
cd services/home-miner-daemon
python3 cli.py events --kind all --limit 10
```

## Recommendations

### Immediate

1. Fix `token_used` enforcement in `store.py`
2. Add basic pytest suite for the 9 error classes
3. Document gateway proof transcripts in `references/gateway-proof.md`

### Short-term (next slices)

1. Full automated test suite — all error classes, trust ceremony, Hermes boundaries, event spine routing
2. Hermes adapter implementation
3. Encrypted inbox UX with `ReceiptCard` components

### Medium-term

1. CI/CD pipeline with automated tests
2. Security hardening pass
3. LAN-only formal verification

---

*This review is intentionally honest. The implementation is solid scaffolding, but "works on my machine" is not a milestone. The remaining work is measurable, tractable, and mapped to specific plan items.*
