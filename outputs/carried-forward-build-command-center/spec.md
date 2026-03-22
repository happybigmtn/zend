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

**Location:** `services/home-miner-daemon/daemon.py:186-198`

**Evidence:** The daemon exposes `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints without any capability validation. Any client that can reach the port (local or LAN depending on `ZEND_BIND_HOST`) can control the miner.

**Gap:** `cli.py` scripts validate capabilities via `has_capability()` before calling daemon endpoints, but the daemon itself does not validate that the calling client has the `control` capability. The `has_capability()` lookup is by device name (user-supplied input), so even the CLI check provides no cryptographic proof of identity.

**Required Fix:** The daemon must validate a client credential on every mutating endpoint. Each request must carry a pairing ID (`X-Client-ID` header) that the daemon looks up in the pairing store and checks against the `control` capability before accepting commands.

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

**Location:** `references/hermes-adapter.md` (contract exists); `services/home-miner-daemon/hermes_adapter.py` (does not exist)

**Evidence:** The Hermes adapter interface is defined as a contract but no implementation exists in `services/home-miner-daemon/`. `hermes_summary_smoke.sh` appends a hardcoded summary to the spine without going through a real Hermes adapter.

**Required Fix:** Implement the `HermesAdapter` interface in the daemon with:
- Authority token validation
- Scope checking (observe/summarize only)
- Event spine append for summaries
- Rejection of out-of-scope operations

### Finding 5: Encrypted Operations Inbox UX Is Basic

**Evidence:** The event spine (`spine.py`) appends JSON events. The gateway client (`index.html`) renders events but the inbox view is a raw list with minimal filtering — no grouping by kind, no receipt status filtering, no warm empty states per category, no pagination.

**Required Fix:** Enhance the inbox view per the Design Intent in the ExecPlan — warm empty states, grouped receipts, category filtering, and polite live-region announcements for new items.

### Finding 6: Token Expires at Creation Time

**Location:** `services/home-miner-daemon/store.py:86-90`

**Evidence:**
```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # ← set to NOW
    return token, expires
```

**Gap:** `token_expires_at` is set to the current time. Any correct `consume_token()` implementation that checks `token_expires_at > now` will reject every token as already expired at creation time. The `expires` value must be a future time (e.g., `datetime.now(timezone.utc) + timedelta(minutes=10)`).

**Required Fix:** Change `expires = datetime.now(timezone.utc).isoformat()` to `expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()`.

### Finding 7: `token` Field Absent from Pairing Record

**Location:** `services/home-miner-daemon/store.py:40-49`

**Gap:** The `GatewayPairing` dataclass has `token_expires_at` and `token_used` fields but no `token` field. `pair_client()` generates a token via `create_pairing_token()` but never stores it in the pairing record. Therefore, `consume_token(token)` has no field to search against — the interface is unimplementable without first adding the token to the record.

**Required Fix:** Add `token: str` field to `GatewayPairing`. Store the generated token in `pair_client()`. Then `consume_token()` can search pairings by token value.

### Finding 8: Gateway Client Hardcodes All Capabilities

**Location:** `apps/zend-home-gateway/index.html:626`

**Evidence:**
```javascript
capabilities: ['observe', 'control'],  // hardcoded — never validated against daemon
```

**Gap:** The client does not fetch its actual granted capabilities from the daemon. It always claims `['observe', 'control']`. The UI always enables control buttons regardless of what was actually granted during pairing.

**Required Fix:** The client must fetch its actual granted capabilities from the daemon via a new endpoint or store them from the pairing ceremony response in `localStorage`.

### Finding 9: Bootstrap Skips `pairing_requested` Event

**Location:** `services/home-miner-daemon/cli.py:73-95` vs `cli.py:98-128`

**Gap:** `cmd_bootstrap()` only appends `pairing_granted`. `cmd_pair()` appends both `pairing_requested` and `pairing_granted`. The event sequence must be consistent across both paths.

**Required Fix:** `cmd_bootstrap()` must append `pairing_requested` before `pairing_granted`, matching the sequence from `cmd_pair()`.

### Finding 10: Event Spine Encryption Not Implemented

**Location:** `services/home-miner-daemon/spine.py:62-65`

**Gap:** The contract (`references/event-spine.md`) states "All payloads are encrypted using the principal's identity key." The implementation appends raw JSON with no encryption. This is a contract breach.

**Required Fix:** Either implement encryption or formally acknowledge as deferred with rationale.

## Open Task Specification

### Task 0 (Prerequisite): Fix Token Schema and Expiration

**Files:** `services/home-miner-daemon/store.py`

Three prerequisite fixes must land before any other task:

1. **Add `token` field to `GatewayPairing` dataclass:**
   ```python
   @dataclass
   class GatewayPairing:
       id: str
       principal_id: str
       device_name: str
       capabilities: list
       paired_at: str
       token: str              # ← ADD THIS FIELD
       token_expires_at: str
       token_used: bool = False
   ```

2. **Fix `create_pairing_token()` to return a future expiration:**
   ```python
   from datetime import timedelta
   expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
   ```

3. **Store the token in `pair_client()`:**
   After `token, expires = create_pairing_token()`, add `token=token` to the `GatewayPairing` constructor.

### Task 1: Enforce Token Replay Prevention

**File:** `services/home-miner-daemon/store.py`
**Prerequisite:** Task 0 (token field + expiration fix)

Add a `consume_token(token: str)` function:
1. Loads all pairing records
2. Finds the pairing with matching `token` field where `token_expires_at > now`
3. If found and `token_used == False`: sets `token_used = True`, saves, returns success
4. If found and `token_used == True`: raises `PairingTokenReplay`
5. If not found or expired: raises `PairingTokenExpired`

Modify `pair_client()` to call `consume_token()` before creating the new pairing.

**Test cases:**
- Pair with valid token → success
- Pair with same token again → `PairingTokenReplay`
- Pair with expired token → `PairingTokenExpired`

### Task 2: Enforce Capability Checks in Daemon

**Files:** `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/store.py`

Add a `validate_client_token(client_id: str, required_capability: str)` function:
1. Loads pairing by `client_id` (the pairing `id` UUID, passed as `X-Client-ID` header)
2. Checks if `required_capability` is in the pairing's `capabilities` list
3. Returns `True` if authorized; raises `GatewayUnauthorized` if not found or capability absent

Modify `do_POST` handlers for `/miner/start`, `/miner/stop`, `/miner/set_mode` to:
- Accept `X-Client-ID` header (the pairing `id` UUID)
- Call `validate_client_token(client_id, 'control')` before delegating to `MinerSimulator`
- Return `401` for missing header, `403` for insufficient capability

**Note on credential format:** The simplest credential for milestone 1 is the pairing `id` UUID stored in `pairing-store.json`. This is not a secret — it relies on LAN isolation for protection. The daemon binds `127.0.0.1` by default; LAN exposure requires explicit `ZEND_BIND_HOST` configuration.

**Test cases:**
- POST without `X-Client-ID` header → 401 `GatewayUnauthorized`
- POST with valid pairing ID lacking `control` → 403 `GatewayUnauthorized`
- POST with valid pairing ID with `control` → 200 success

### Task 2b: Gateway Client Fetches Actual Capabilities

**File:** `apps/zend-home-gateway/index.html`

After pairing, the client must store the actual granted capabilities. Recommended approach:
1. Add a `GET /pairing/:id` endpoint to the daemon that returns the pairing record
2. After pairing, the client stores `capabilities` from the response in `localStorage`
3. At startup, restore `capabilities` from `localStorage` instead of hardcoding

### Task 2c: Fix Bootstrap to Append `pairing_requested` Event

**File:** `services/home-miner-daemon/cli.py`

In `cmd_bootstrap()`, add `spine.append_pairing_requested()` before `spine.append_pairing_granted()` to match the event sequence from `cmd_pair()`.

### Task 3: Add Automated Test Suite

**Location:** `services/home-miner-daemon/tests/` (new directory)

Test file structure:
```
tests/
  __init__.py
  test_store.py       # Pairing, token replay, capabilities
  test_daemon.py      # HTTP endpoints, capability enforcement
  test_spine.py       # Event append, routing, staleness
  test_hermes.py      # Adapter scope checking
  test_error_taxonomy.py  # All named error classes
```

Each test follows BDD structure (`#given`, `#when`, `#then`). Use `python -m unittest discover`. No external test dependencies.

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
- Event spine encryption (contract breach, acknowledged as deferred)
- Concurrency safety on pairing store (simulator only, low priority)

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
