# Zend Home Command Center — Carried-Forward Review

**Lane:** `carried-forward-build-command-center`
**Status:** Active — Security Hardening and Test Coverage Required
**Generated:** 2026-03-22
**Reviewer:** Senior Staff Engineer (Nemesis Security + Correctness Review)

---

## Summary

The spec correctly identifies the five primary security and integration gaps from milestone 1. This review confirms all five gaps are present and adds **two correctness bugs** (Findings A and B) that the spec missed, plus a **data model incompleteness** (Finding E) that makes the specified `consume_token()` interface unimplementable without a prerequisite schema fix.

No automated tests exist. The Hermes adapter does not exist. The inbox UX is a raw list with a single static empty-state string.

---

## Gap Confirmation

### From Original Spec

| Gap | Severity | Confirmed | Location |
|-----|----------|-----------|----------|
| Token replay not enforced | Critical | ✓ | `store.py:49` — `token_used=False` set at creation, `consume_token()` absent |
| Capability not enforced at daemon | Critical | ✓ | `daemon.py:do_POST()` — no `X-Client-ID` check, no capability lookup |
| Zero test coverage | High | ✓ | No `tests/` directory anywhere in repo |
| Hermes adapter not implemented | High | ✓ | `hermes_adapter.py` does not exist |
| Inbox UX minimal | Medium | ✓ | `index.html` has static `"No messages yet"`, no filter pills, no grouping |

### New Findings

| Finding | Severity | Location |
|---------|----------|----------|
| A: Token expires at creation time (`now`) | Critical | `store.py:89` |
| B: Gateway client hardcodes capabilities | High | `index.html:626` |
| C: Gateway client principal fallback mismatch | Medium | `index.html:781` |
| D: Pairing store has no concurrency safety | Medium | `store.py:80-83` |
| E: `token` field absent from pairing record | High | `store.py:40-49` |
| F: Event spine encryption not implemented | Medium | `spine.py:62-65` |

---

## Finding A — Token Expires at Creation Time (Critical)

**Location:** `services/home-miner-daemon/store.py:86-90`

```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # ← NOW
    return token, expires
```

**Root cause:** `expires` is set to the current timestamp. Any correct `consume_token()` implementation that checks `token_expires_at > now` will reject every token as already expired at the moment of creation.

**Impact:** Finding A makes the spec's Task 1 immediately broken upon implementation — even a perfect `consume_token()` will reject 100% of tokens.

**Fix:** `expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()`

---

## Finding B — Gateway Client Hardcodes All Capabilities (High)

**Location:** `apps/zend-home-gateway/index.html:626`

```javascript
capabilities: ['observe', 'control'],  // hardcoded — never validated
```

**Root cause:** The client does not fetch its actual granted capabilities from the daemon or store them from the pairing ceremony. `state.capabilities` is always `['observe', 'control']` regardless of what was granted.

**Compounding failure:** The daemon has no auth check (Gap 2), so even if the client were limited to `observe` only, it could still issue `control` commands by calling the daemon directly. Combined with the hardcoded capabilities, the UI always renders control buttons as enabled.

**Fix:** Fetch actual capabilities from daemon or store from pairing response in `localStorage`.

---

## Finding C — Gateway Client Principal Fallback Mismatch (Medium)

**Location:** `apps/zend-home-gateway/index.html:781`

```javascript
state.principalId = localStorage.getItem('zend_principal_id') || '550e8400-e29b-41d4-a716-446655440000';
```

**Root cause:** The fallback UUID is a static value that does not match what `load_or_create_principal()` generates (a random UUID v4). On first load with no prior `localStorage`, the client displays a principal ID that will never match any event in the spine.

**Impact:** Inbox shows zero events even when events exist, because the client is querying for a different principal.

---

## Finding D — Pairing Store Has No Concurrency Safety (Medium)

**Location:** `services/home-miner-daemon/store.py:80-83`

```python
def save_pairings(pairings: dict):
    with open(PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)
```

**Root cause:** Plain `json.dump()` to disk with no file locking. Two concurrent `pair_client()` calls can overwrite each other's writes.

**Impact:** For a milestone 1 simulator this is low priority, but it should be documented as a known limitation.

---

## Finding E — `token` Field Absent from Pairing Record (High)

**Location:** `services/home-miner-daemon/store.py:40-49`

```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token_expires_at: str   # ← exists
    token_used: bool = False # ← exists
    # token: str            # ← ABSENT
```

The spec's `consume_token(token: str)` searches for a pairing by the token string:

> "Finds the pairing with matching `token` where `token_expires_at > now`"

But `GatewayPairing` has no `token` field. `pair_client()` generates a token via `create_pairing_token()` but never stores it in the pairing record. The `consume_token()` interface is unimplementable without first adding the field.

**Fix:** Add `token: str` to `GatewayPairing`, store it in `pair_client()`, then search by it.

---

## Finding F — Event Spine Encryption Not Implemented (Medium)

**Location:** `services/home-miner-daemon/spine.py:62-65`

The contract (`references/event-spine.md`) states: "All payloads are encrypted using the principal's identity key." The implementation appends raw JSON with no encryption.

This is a contract breach. Acceptable to defer with explicit acknowledgment, but it must not be silently left as-is.

---

## Nemesis Pass 1 — Trust Boundary Analysis

### Who Can Trigger Dangerous Actions?

The only dangerous action is issuing miner control commands (`start`, `stop`, `set_mode`).

1. **Any process on the same machine** — daemon binds `127.0.0.1:8080`, so only local processes can reach it. Accepted as the LAN-only design.
2. **Any device on the LAN** — if `ZEND_BIND_HOST` is set to a LAN interface, any device on the network can issue control commands with no auth. The daemon does not validate any credentials.
3. **Any browser tab on the client device** — the gateway client HTML has no auth token. Any web page opened on the same device can issue `fetch('http://127.0.0.1:8080/miner/start')`.

### Authority Assumption Gap

The CLI checks `has_capability()` by device name, but the device name is user-supplied input (`--client alice-phone`). Any process can claim to be `alice-phone` and pass the `has_capability()` check, because the check only looks up the pairing store, not a cryptographic proof of identity.

The spec's fix (requiring `X-Client-ID` header) addresses this partially but introduces a new problem: the `X-Client-ID` is just a UUID. Any client that knows the pairing ID can impersonate it. The milestone 1 mitigation is LAN isolation — this should be explicitly documented.

### Privilege Escalation Path

```
Unauthenticated HTTP POST → daemon.do_POST() → MinerSimulator.start()
```

No capability check. No client identity. No proof of possession. The `control` capability in the pairing JSON is never consulted by the daemon.

---

## Nemesis Pass 2 — State Consistency Analysis

### State Surfaces

| State Surface | Stored In | Read By | Mutated By |
|---|---|---|---|
| Principal | `state/principal.json` | CLI, spine events | `load_or_create_principal()` |
| Pairing records | `state/pairing-store.json` | CLI `has_capability()`, `get_pairing_by_device()` | `pair_client()` |
| Event spine | `state/event-spine.jsonl` | CLI `get_events()`, inbox | All `append_*()` functions |
| Miner simulator | In-memory | Daemon `/status` | Daemon `/miner/*` |
| Client state | Browser `localStorage` + JS `state` | UI rendering | User actions, polling |

### Consistency Violations

**Issue 1: Pairing store and daemon are decoupled.**
The CLI checks `has_capability(args.client, 'control')` before calling the daemon. If the CLI is bypassed (any HTTP client), the daemon accepts the command. The pairing store holds authoritative permissions, but the daemon ignores them.

**Issue 2: Bootstrap and pair have inconsistent event sequences.**
`cmd_bootstrap()` appends only `pairing_granted`. `cmd_pair()` appends both `pairing_requested` and `pairing_granted`. A `pairing_granted` event in the spine may not have a preceding `pairing_requested`.

**Issue 3: Token expiration is broken at creation.**
`create_pairing_token()` sets `expires = now`. Any correct expiration check rejects the token immediately.

**Issue 4: Token is never stored.**
`pair_client()` generates a token but never saves it in the pairing record. `consume_token()` cannot search for a token that isn't stored.

### Replayability

- **Token replay:** not enforced (confirmed)
- **Command replay:** `MinerSimulator.start()` and `stop()` are idempotent (returns `already_running`/`already_stopped`). `set_mode()` always succeeds. No idempotency key required.
- **Event append replay:** `_save_event()` appends to JSONL unconditionally. Replaying the same append produces a duplicate event. No deduplication.

---

## Security Invariants Violation Status

| Invariant | Status | Notes |
|---|---|---|
| No off-device mining control | **VIOLATED** | Any LAN client can POST to `/miner/*` with no credential |
| Capability least-privilege | **VIOLATED** | Observe-only clients get full UI control buttons enabled |
| Token one-time use | **VIOLATED** | No enforcement; `consume_token()` missing |
| Event spine append-only | ✓ | No delete/modify code paths found |
| LAN-only enforcement | Partial | Binds `127.0.0.1` by default, but explicit `ZEND_BIND_HOST` exposes with no additional auth |

---

## Recommendations

### Required Before This Lane Closes

1. **Task 0 (Critical — prerequisite):** Add `token` field to `GatewayPairing`. Fix `create_pairing_token()` to return a future expiration. These are prerequisite to every other task.
2. **Task 1 (Critical):** Implement `consume_token()`. Modify `pair_client()` to call it before creating a pairing.
3. **Task 2 (Critical):** Add server-side capability validation to daemon. Use pairing `id` as the `X-Client-ID` credential. Document that milestone 1 relies on LAN isolation for credential confidentiality.
4. **Task 2b (High):** Gateway client must fetch actual capabilities, not hardcode them.
5. **Task 2c (High):** Fix `cmd_bootstrap()` to append `pairing_requested` before `pairing_granted`.
6. **Task 3 (High):** Add automated tests concurrent with Tasks 1 and 2, not after.

### Acceptable to Defer

- Event spine encryption (contract breach acknowledged as deferred)
- Concurrency safety on pairing store (simulator only, low blast radius)
- Hermes adapter (correctly deferred per spec)
- Inbox UX enhancement (correctly deferred per spec)

---

## Do Not Close This Lane Until

- [ ] `consume_token()` exists and correctly rejects replayed tokens
- [ ] `consume_token()` uses a `token` field that is stored in `GatewayPairing`
- [ ] Token expiration is a future time (not `now`)
- [ ] `pair_client()` calls `consume_token()` before creating the pairing
- [ ] Daemon rejects unauthenticated control commands with `401` or `403`
- [ ] Daemon rejects control commands from clients lacking `control` capability with `403`
- [ ] Gateway client fetches actual capabilities from daemon or stores them from pairing ceremony
- [ ] `cmd_bootstrap()` appends both `pairing_requested` and `pairing_granted`
- [ ] Test suite exists covering all error taxonomy scenarios
- [ ] `python -m py_compile` passes on all changed files
