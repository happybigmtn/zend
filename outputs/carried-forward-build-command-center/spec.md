# Zend Home Command Center — Carried-Forward Specification

**Lane:** `carried-forward-build-command-center`
**Status:** Active — Remaining Work from Milestone 1
**Generated:** 2026-03-22

## Provenance

This document captures the remaining work for the Zend Home Command Center lane, derived from `plans/2026-03-19-build-zend-home-command-center.md`. It maps the open tasks to their root causes and defines the specification for addressing each gap.

The original milestone 1 implementation is complete for scaffolding, contracts, simulator, and gateway client UI. This carried-forward lane addresses the security hardening, test coverage, and integration gaps that were deferred.

## Relationship to Milestone 1

| Artifact | Location | Status |
|----------|----------|--------|
| Spec (milestone 1) | `outputs/home-command-center/spec.md` | Complete |
| Review (milestone 1) | `outputs/home-command-center/review.md` | Approved |
| ExecPlan | `plans/2026-03-19-build-zend-home-command-center.md` | Living |
| Design System | `DESIGN.md` | Authoritative |

## Root Cause Analysis of Remaining Work

### Finding 1: Token Replay Prevention Not Enforced

**Location:** `services/home-miner-daemon/store.py:49`

**Evidence:**
```python
@dataclass
class GatewayPairing:
    # ...
    token_used: bool = False  # Set to False but never set to True
```

**Gap:** `create_pairing_token()` generates tokens. `pair_client()` creates pairing records with `token_used=False`. No code path ever sets `token_used=True` after a token is consumed. The error taxonomy defines `PairingTokenReplay` but the enforcement is absent.

**Required Fix:** After a successful pairing ceremony, the consumed token must be marked `token_used=True` in the store. Subsequent pair attempts with the same token must be rejected with `PairingTokenReplay`.

### Finding 2: Capability Checks Not Enforced in Daemon

**Location:** `services/home-miner-daemon/daemon.py`

**Evidence:** The daemon exposes `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints without any capability validation. Any client on the LAN can control the miner.

**Gap:** `cli.py` scripts validate capabilities via `has_capability()` before calling daemon endpoints, but the daemon itself does not validate that the calling client has the `control` capability. This means the LAN-only protection is UI-level only, not enforced at the service boundary.

**Required Fix:** The daemon must validate a capability token on every mutating endpoint. Each request must carry a client identity token that the daemon validates against the pairing store before accepting commands.

### Finding 3: No Automated Test Coverage

**Evidence:** Zero test files exist in the repository. The plan calls for tests for:
- Token replay prevention
- Stale snapshot handling
- Control command conflicts
- Trust ceremony state transitions
- Hermes delegation boundaries
- Event spine routing
- Accessibility-sensitive states

**Required Fix:** Add a test suite (Python `unittest` or `pytest`) covering all error taxonomy scenarios and the integration paths defined in the Test Diagram.

### Finding 4: Hermes Adapter Contract Only

**Location:** `references/hermes-adapter.md`

**Evidence:** The Hermes adapter interface is defined as a contract but no implementation exists in `services/home-miner-daemon/`.

**Gap:** `hermes_summary_smoke.sh` appends a hardcoded summary to the spine without going through a real Hermes adapter. Hermes cannot actually connect.

**Required Fix:** Implement the `HermesAdapter` interface in the daemon with:
- Authority token validation
- Scope checking (observe/summarize only)
- Event spine append for summaries
- Rejection of out-of-scope operations

### Finding 5: Encrypted Operations Inbox UX Is Basic

**Evidence:** The event spine (`spine.py`) appends JSON events. The gateway client (`index.html`) renders events but the inbox view is a raw list with minimal filtering.

**Gap:** No grouping by kind, no receipt status filtering, no warm empty states per category, no pagination.

**Required Fix:** Enhance the inbox view per the Design Intent in the ExecPlan — warm empty states, grouped receipts, category filtering, and polite live-region announcements for new items.

### Finding 6 (New): Token Expires at Creation Time

**Location:** `services/home-miner-daemon/store.py:86-90`

**Evidence:**
```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # ← set to NOW
    return token, expires
```

**Gap:** `token_expires_at` is set to the current time. Any correct `consume_token()` implementation that checks `token_expires_at > now` will reject every token as already expired at creation time. The `expires` value must be a future time (e.g., `datetime.now(timezone.utc) + timedelta(minutes=10)`).

### Finding 7 (New): `token` Field Absent from Pairing Record

**Location:** `services/home-miner-daemon/store.py:40-49`

**Gap:** The `GatewayPairing` dataclass has `token_expires_at` and `token_used` fields but no `token` field. The `pair_client()` function generates a token via `create_pairing_token()` but never stores it in the pairing record. Therefore, `consume_token(token)` has no field to search against — the interface is unimplementable without first adding the token to the record.

**Required Fix:** Add `token: str` field to `GatewayPairing`. Store the generated token in `pair_client()`. Then `consume_token()` can search pairings by token value.

### Finding 8 (New): Gateway Client Hardcodes All Capabilities

**Location:** `apps/zend-home-gateway/index.html:626`

**Evidence:**
```javascript
capabilities: ['observe', 'control'],  // hardcoded — never validated against daemon
```

**Gap:** The client does not fetch its actual granted capabilities from the daemon. It always claims `['observe', 'control']`. Combined with the daemon having no auth check (Finding 2), this means an observe-only client gets full UI control access. The client must fetch the pairing record from the daemon or store the granted capabilities from the bootstrap/pairing ceremony.

### Finding 9 (New): Bootstrap Skips `pairing_requested` Event

**Location:** `services/home-miner-daemon/cli.py:73-95` vs `cli.py:98-128`

**Gap:** `cmd_bootstrap()` only appends `pairing_granted`. `cmd_pair()` appends both `pairing_requested` and `pairing_granted`. This means the event spine can have a `pairing_granted` without a preceding `pairing_requested`. The event sequence must be consistent across both paths.

### Finding 10 (New): Event Spine Encryption Not Implemented

**Location:** `services/home-miner-daemon/spine.py:62-65`

**Gap:** The contract (`references/event-spine.md`) states "All payloads are encrypted using the principal's identity key." The implementation appends raw JSON with no encryption. This is a contract breach — either acknowledge as deferred or implement encryption.

## Open Task Specification

### Task 0 (Prerequisite): Add Token Field and Fix Expiration

**File:** `services/home-miner-daemon/store.py`

Before `consume_token()` can be implemented, two prerequisite fixes are needed:

1. Add `token: str` field to `GatewayPairing` dataclass
2. Fix `create_pairing_token()` to return a future expiration time:
   ```python
   from datetime import timedelta
   expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
   ```
3. Store the token in `pair_client()`: `token=token` when constructing `GatewayPairing`

### Task 1: Enforce Token Replay Prevention

**File:** `services/home-miner-daemon/store.py`
**Prerequisite:** Task 0 (token field + expiration fix)

Add a `consume_token(token: str)` function that:
1. Loads all pairing records
2. Finds the pairing with matching `token` field where `token_expires_at > now`
3. If found and `token_used == False`: sets `token_used = True`, saves, returns success
4. If found and `token_used == True`: raises `PairingTokenReplay`
5. If not found or expired: raises `PairingTokenExpired`

Modify `pair_client()` to call `consume_token()` before creating the new pairing.

**Test:**
- Pair with valid token → success
- Pair with same token again → `PairingTokenReplay`
- Pair with expired token → `PairingTokenExpired`

### Task 2: Enforce Capability Checks in Daemon

**Files:** `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/store.py`

Add a `validate_client_token(client_id: str, required_capability: str)` function:
1. Loads pairing by client ID (use the pairing `id` field as the credential)
2. Checks if `required_capability` is in `capabilities`
3. Returns `True` if authorized, raises `GatewayUnauthorized` if not

Modify `do_POST` handlers for `/miner/start`, `/miner/stop`, `/miner/set_mode` to accept a `X-Client-ID` header (the pairing `id` UUID) and validate `control` capability before delegating to the miner simulator.

**Test:**
- POST without `X-Client-ID` header → 401 `GatewayUnauthorized`
- POST with valid pairing ID lacking `control` → 403 `GatewayUnauthorized`
- POST with valid pairing ID with `control` → 200 success

### Task 2b: Gateway Client Fetches Actual Capabilities

**File:** `apps/zend-home-gateway/index.html`

After pairing, the client must store the actual granted capabilities. Options:
1. Fetch from daemon via a new `/pairing/:id` endpoint
2. Store the pairing record from the CLI/pairing ceremony response in `localStorage`
3. At minimum, do not hardcode `capabilities: ['observe', 'control']` — derive from the pairing response

### Task 2c: Fix Bootstrap to Append `pairing_requested` Event

**File:** `services/home-miner-daemon/cli.py`

`cmd_bootstrap()` currently only appends `pairing_granted`. Add `spine.append_pairing_requested()` before `spine.append_pairing_granted()` to match the event sequence from `cmd_pair()`.

### Task 3: Add Automated Test Suite

**Location:** `services/home-miner-daemon/tests/` (new)

Test file structure:
```
tests/
  __init__.py
  test_store.py       # Pairing, token replay, capabilities
  test_daemon.py      # HTTP endpoints, capability enforcement
  test_spine.py       # Event append, routing, staleness
  test_hermes.py       # Adapter scope checking
  test_error_taxonomy.py  # All named error classes
```

Each test must follow BDD structure (`#given`, `#when`, `#then`) per the test mode guidelines.

### Task 4: Implement Hermes Adapter

**File:** `services/home-miner-daemon/hermes_adapter.py` (new)

Implement the `HermesAdapter` interface per `references/hermes-adapter.md`:
- `connect(authority_token)` → validates token, returns connection
- `readStatus()` → returns `MinerSnapshot` if observe scope
- `appendSummary(summary)` → appends to event spine if summarize scope
- `getScope()` → returns granted capabilities

Reject any operation outside the granted scope with `GatewayUnauthorized`.

### Task 5: Enhance Inbox UX

**File:** `apps/zend-home-gateway/index.html`

Per Design Intent and Interaction State Coverage:
- Add warm empty states per category with primary next actions
- Add grouping by event kind (receipts, alerts, summaries, messages)
- Add filter pills (All, Receipts, Alerts, Hermes, Messages)
- Add polite live-region announcements for new items
- Add reduced-motion fallbacks

## Acceptance Criteria for This Lane

- [ ] `PairingTokenReplay` is enforced — token can only be used once
- [ ] `PairingTokenExpired` is enforced — expired tokens are rejected
- [ ] Token expiration is a future time (not `now`) at creation
- [ ] `consume_token()` searches a `token` field that exists in `GatewayPairing`
- [ ] All daemon mutating endpoints require `X-Client-ID` header
- [ ] `control` capability is validated server-side, not just client-side
- [ ] Gateway client fetches actual capabilities from daemon or pairing ceremony (not hardcoded)
- [ ] `cmd_bootstrap()` appends both `pairing_requested` and `pairing_granted` events
- [ ] All error taxonomy classes have at least one failing and one passing test
- [ ] Hermes adapter rejects out-of-scope operations (e.g., control when only observe granted)
- [ ] Event spine appends are tested for all 7 event kinds
- [ ] Inbox empty states are warm and action-oriented per AI-slop guardrails
- [ ] All new code passes `python -m py_compile` with no errors

## Security Invariants

These must never be broken:

1. **No off-device mining control:** The daemon is the only component that can issue miner commands
2. **Capability least-privilege:** Clients receive exactly the capabilities granted, no more
3. **Token one-time use:** Pairing tokens cannot be replayed after consumption
4. **Event spine append-only:** No event can be modified or deleted after writing
5. **LAN-only enforcement:** Daemon binds `127.0.0.1` by default; LAN binding requires explicit config

## Out of Scope for This Lane

- Remote internet access (deferred beyond milestone 1)
- Payout-target mutation (deferred — higher financial blast radius)
- Real miner backend (simulator is sufficient for command-center proof)
- Multi-controller conflict resolution (single-controller only for milestone 1)
- Full Hermes control capability (observe + summarize only for milestone 1)

## Dependencies

All changes are in-process Python within the existing zero-dependency architecture:

| Module | Dependency |
|--------|------------|
| `store.py` | Standard library only |
| `daemon.py` | `socketserver`, `http.server`, `json`, `threading` |
| `spine.py` | Standard library only |
| `cli.py` | Standard library only |
| `hermes_adapter.py` | Standard library only |

No new external dependencies. No `pip install` required for tests — use `python -m unittest discover`.
