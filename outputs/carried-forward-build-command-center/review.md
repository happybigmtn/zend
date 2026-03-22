# Zend Home Command Center — Carried-Forward Review (Nemesis Pass)

**Lane:** `carried-forward-build-command-center`
**Status:** Active — Security Hardening and Test Coverage Required
**Generated:** 2026-03-22
**Reviewer:** Senior Staff Engineer (Nemesis Security + Correctness Review)

---

## Summary

The lane spec correctly identifies the three critical security gaps and two integration gaps from milestone 1. However, this review finds **two additional correctness bugs** that the spec missed, and **one root-cause misdiagnosis** in the token expiration logic. The spec's task definitions are also partially underspecified — the `consume_token()` interface references a token field that does not exist in the pairing record, and the capability validation spec does not specify how the daemon resolves client identity.

No automated tests exist. The Hermes adapter does not exist. The inbox UX is still a raw list with one static empty-state string.

---

## Correctness Assessment

### Verified: All 5 Spec Gaps Are Confirmed

| Gap | Severity | Confirmed | Evidence |
|-----|----------|-----------|----------|
| Token replay not enforced | Critical | ✓ | `token_used=False` set at creation, `consume_token()` does not exist |
| Capability not enforced at daemon | Critical | ✓ | `daemon.py:do_POST()` accepts all requests, no `X-Client-ID` check |
| Zero test coverage | High | ✓ | No `tests/` directory anywhere in repo |
| Hermes adapter not implemented | High | ✓ | `hermes_adapter.py` does not exist; `hermes_summary_smoke.sh` calls spine directly |
| Inbox UX minimal | Medium | ✓ | HTML has static `"No messages yet"` string, no event fetch, no filter pills |

### Finding A (NEW — Not in Spec): Token Expires at Creation Time

**Severity:** Critical
**Location:** `services/home-miner-daemon/store.py:86-90`

```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # ← NOW
    return token, expires
```

`pair_client()` stores this as `token_expires_at`. If `consume_token()` is implemented per the spec and checks `token_expires_at > now`, every token will be rejected as expired at creation time. The `expires` variable should be `datetime.now(timezone.utc) + timedelta(minutes=10)` or similar.

The spec does not identify this as a distinct bug. It only describes the `consume_token()` interface. The root cause — token expiration must be a *future* time — is not stated.

### Finding B (NEW — Not in Spec): Gateway Client Hardcodes All Capabilities

**Severity:** High
**Location:** `apps/zend-home-gateway/index.html:626`

```javascript
capabilities: ['observe', 'control'],  // hardcoded — never validated
```

The client does not:
1. Fetch the actual pairing record from the daemon
2. Store the granted capabilities from the pairing ceremony
3. Check its own capabilities before issuing control commands (the UI always enables the control buttons)

The mode switcher, start, and stop buttons in the UI all check `state.capabilities.includes('control')`, but `state.capabilities` is always `['observe', 'control']` — so the capability check in the UI always passes regardless of what was actually granted. Combined with Finding 2 (daemon accepts all requests), a client that was only granted `observe` can still issue `control` commands.

### Finding C (NEW — Not in Spec): Gateway Client Principal Mismatch

**Severity:** Medium
**Location:** `apps/zend-home-gateway/index.html:781`

```javascript
state.principalId = localStorage.getItem('zend_principal_id') || '550e8400-e29b-41d4-a716-446655440000';
```

The fallback UUID is a different value from what `load_or_create_principal()` would generate (a random UUID v4). This means the fallback principal ID never matches the actual daemon principal. On first load with no `localStorage`, the client shows a principal ID that will never match any event in the spine.

### Finding D (NEW — Not in Spec): Pairing Store Has No Concurrency Safety

**Severity:** Medium
**Location:** `services/home-miner-daemon/store.py:80-83`

`save_pairings()` does a plain `json.dump()` to disk with no file locking. Two concurrent pairing requests can overwrite each other's writes. For a milestone-1 simulator this is low priority, but it should be documented as a known limitation.

### Finding E (NEW — Not in Spec): `token` Field Absent from Pairing Record

**Severity:** High
**Location:** `services/home-miner-daemon/store.py:40-49`

The spec's `consume_token(token: str)` function searches for a pairing by the token string itself:

> "2. Finds the pairing with matching `token` where `token_expires_at > now`"

But the `GatewayPairing` dataclass has no `token` field. It has `token_expires_at` and `token_used`, but not the token value itself. The `pair_client()` function generates a token via `create_pairing_token()` but never stores it in the pairing record. So `consume_token()` has no field to search against.

The fix requires adding a `token: str` field to `GatewayPairing`, storing the token during `pair_client()`, and then searching by that field.

### Finding F (NEW — Not in Spec): Contract-Says Encryption Not Implemented

**Severity:** Medium
**Location:** `services/home-miner-daemon/spine.py:62-65`

The event spine contract (`references/event-spine.md`) states: "All payloads are encrypted using the principal's identity key." The implementation appends raw JSON. No encryption is present. This is a contract breach that should be acknowledged, even if deferred.

---

## Nemesis Pass 1 — First-Principles Trust Boundary Challenge

### Who Can Trigger Dangerous Actions?

The only dangerous action is issuing miner control commands (`start`, `stop`, `set_mode`). These can be triggered by:

1. **Any process on the same machine** — daemon binds `127.0.0.1:8080`, so only local processes can reach it. Accepted as the LAN-only design.
2. **Any device on the LAN** — if `ZEND_BIND_HOST` is set to a LAN interface (the documented production config), any device on the network can issue control commands with no auth. The daemon does not validate any credentials.
3. **Any browser tab on the client device** — the gateway client HTML has no auth token. Any web page opened on the same device can issue `fetch('http://127.0.0.1:8080/miner/start')`.

### Authority Assumptions

The review correctly identifies that CLI scripts validate `has_capability()` before calling the daemon, but the daemon does not. However, the review misses a deeper problem: the `has_capability()` function looks up a device by **device name**, and the device name is user-supplied input (`--client alice-phone`). There is no proof that the calling process actually *is* `alice-phone`. Any process can claim to be `alice-phone` and pass the `has_capability()` check, because the check only looks at the pairing store, not a cryptographic proof of identity.

The fix (requiring `X-Client-ID` header) partially addresses this but introduces a new problem: how does the daemon verify that the `X-Client-ID` header is authentic? The spec does not address token format or signature verification. A `X-Client-ID: alice-phone` header can be set by any client.

### Privilege Escalation Path

```
Unauthenticated HTTP POST → daemon.do_POST() → MinerSimulator.start()
```

No capability check. No client identity. No proof of possession. The `control` capability stored in the pairing JSON is never consulted by the daemon. This is a direct privilege escalation from "anyone who can reach the port" to "full miner control."

### Secret Handling

- **Pairing token**: UUID v4, generated but never stored in the pairing record (Finding E). Token is returned by `pair_client()` but nothing ever validates it.
- **Authority token (Hermes)**: Referenced in `references/hermes-adapter.md` but never implemented.
- **Principal identity key**: Referenced in contract as the encryption key but never generated or used.

---

## Nemesis Pass 2 — Coupled-State Review

### State Surfaces and Their Couplings

| State Surface | Where Stored | Read By | Mutated By |
|---|---|---|---|
| Principal | `state/principal.json` | CLI, spine events | `load_or_create_principal()` |
| Pairing records | `state/pairing-store.json` | CLI `has_capability()`, `get_pairing_by_device()` | `pair_client()` |
| Event spine | `state/event-spine.jsonl` | CLI `get_events()`, inbox | All `append_*()` functions |
| Miner simulator | In-memory | Daemon `/status` | Daemon `/miner/*` |
| Client state | Browser `localStorage` + JS `state` object | UI rendering | User actions, polling |

### Mutation Consistency Issues

**Issue 1: `control` capability is read from pairing store but never enforced at daemon.**
The CLI checks `has_capability(args.client, 'control')` before calling the daemon. If the CLI is bypassed (any HTTP client), the daemon accepts the command. The pairing store and daemon are decoupled — the store holds authoritative permissions, but the daemon ignores them.

**Issue 2: Event spine and pairing store are not consistent.**
`pair_client()` appends a `pairing_granted` event to the spine, but the `pairing_requested` event is not appended (only called from `cmd_pair` in `cli.py`, and only for the second call path; `cmd_bootstrap` only appends `pairing_granted`). This means the event spine can have a `pairing_granted` without a preceding `pairing_requested`.

**Issue 3: CLI `cmd_pair` appends both `pairing_requested` and `pairing_granted`. CLI `cmd_bootstrap` only appends `pairing_granted`.**
This is inconsistent — bootstrap skips the `pairing_requested` event. Either the bootstrap path is missing the event, or the spec incorrectly requires both.

**Issue 4: No idempotence on pairing.**
Calling `pair_client()` twice with the same device name raises `ValueError`, but the error is caught and printed as JSON. If the CLI is called programmatically, the caller must handle this. More importantly, calling `pair_client()` with different device names from the same physical device creates multiple pairing records — one per name. There is no device identity proof.

### Replayability

- **Token replay**: not enforced (confirmed)
- **Command replay**: `MinerSimulator.start()` and `stop()` are idempotent by design (returns `already_running`/`already_stopped`). `set_mode()` always succeeds even if already in that mode. No idempotency key is required.
- **Event append replay**: `_save_event()` appends to JSONL unconditionally. Replaying the same append produces a duplicate event in the spine. No deduplication.

### State Transitions Affecting Safety

| Transition | Protected? | Evidence |
|---|---|---|
| Unpaired → Paired controller | Partially | CLI checks `has_capability()` before calling daemon |
| Observer → Controller | No | No upgrade flow exists; CLI would need `pair_client()` again |
| Any LAN client → Miner control | **No** | Daemon has zero auth |
| Token consumption | **No** | `consume_token()` doesn't exist |
| Token expiration | **Broken** | `token_expires_at = now` at creation |

---

## Milestone Fit Assessment

### What the Spec Gets Right

- The five gaps are real and correctly prioritized (2 critical, 2 high, 1 medium)
- The acceptance criteria are concrete and verifiable
- The security invariants correctly name the LAN-only enforcement and token one-time-use properties
- The risk table correctly identifies LAN client bypass as the highest-impact risk

### What the Spec Misses

1. **Finding A**: Token expiration is set to `now`, not a future time — every token will be immediately rejected by any correct `consume_token()` implementation
2. **Finding B**: Gateway client hardcodes capabilities — the UI always claims `['observe', 'control']`
3. **Finding E**: The `consume_token()` interface references a `token` field that does not exist in `GatewayPairing`
4. **Finding F**: Event spine encryption is in the contract but absent in the code

### Spec Task Quality

| Task | Quality Issue |
|---|---|
| Task 1: Token replay | Interface references nonexistent field; expiration time bug not addressed |
| Task 2: Capability checks | Does not specify token format for `X-Client-ID` or signature verification |
| Task 3: Test suite | Correct |
| Task 4: Hermes adapter | Correct |
| Task 5: Inbox UX | Correct |

### Remaining Blockers (Before Honest Claim)

1. **Daemon accepts unauthenticated control commands** — any LAN client can control the miner
2. **Token replay prevention is unimplemented** — and the token expiration is set to now, making any implementation immediately broken
3. **`consume_token()` interface references a field that doesn't exist** — must add `token` to `GatewayPairing` first
4. **Zero test coverage** — no automated verification of any security boundary

---

## Security Invariants Violation Check

| Invariant | Status | Notes |
|---|---|---|
| No off-device mining control | **VIOLATED** | Any LAN client can POST to `/miner/*` |
| Capability least-privilege | **VIOLATED** | Observe-only clients get full UI control |
| Token one-time use | **VIOLATED** | No enforcement; `consume_token()` missing |
| Event spine append-only | ✓ | No delete/modify code paths found |
| LAN-only enforcement | Partial | Binds `127.0.0.1` by default, but explicit `ZEND_BIND_HOST` config can expose to LAN with no additional auth |

---

## Recommendations

### Required Fixes Before This Lane Can Close

1. **Task 1 (Critical):** Add `token` field to `GatewayPairing`. Fix `create_pairing_token()` to return a future expiration. Implement `consume_token()` with that field. Modify `pair_client()` to call `consume_token()`.
2. **Task 2 (Critical):** Add server-side capability validation to daemon. Define the `X-Client-ID` token format — simplest path is to use the pairing ID (which is a UUID stored in the pairing JSON) as the credential, look it up in the pairing store, and check the capability list.
3. **Task 2b (High — not in spec):** Fix `cmd_pair` to also append `pairing_requested` event (matching `cmd_bootstrap`'s behavior) or fix `cmd_bootstrap` to append `pairing_requested`.
4. **Task 3 (High):** Add automated tests concurrent with Tasks 1 and 2, not after.
5. **Task 2c (High — not in spec):** Gateway client must fetch its actual granted capabilities from the daemon rather than hardcoding them.

### Optional (Acceptable to Defer)

- Event spine encryption (out of scope for milestone 1 per spec)
- Concurrency safety on pairing store (simulator only)
- Hermes adapter (correctly deferred per spec)
- Inbox UX enhancement (correctly deferred per spec)

### Do Not Close This Lane Until

- [ ] Daemon rejects unauthenticated control commands with `GATEWAY_UNAUTHORIZED`
- [ ] `consume_token()` exists and correctly rejects replayed tokens
- [ ] `consume_token()` uses a `token` field that is actually stored in `GatewayPairing`
- [ ] Token expiration is a future time (not `now`)
- [ ] `pair_client()` calls `consume_token()` before creating the pairing
- [ ] Gateway client fetches actual capabilities from the daemon, not hardcoded
- [ ] All daemon mutating endpoints require `X-Client-ID` and validate the associated pairing record
- [ ] Test suite exists and covers all error taxonomy scenarios
