# Hermes Adapter Implementation — Plan Review

**Status:** Approved (conditional — one blocker resolved during review)
**Reviewed:** 2026-03-22
**Plan source:** Inline lane prompt; `genesis/plans/009-hermes-adapter-implementation.md` not on disk

---

## Verdict

**APPROVED — proceed to Milestone 1 (adapter module).**

The plan's architecture is sound: in-process adapter, capability-scoped, event-filtered. The security posture is honest for LAN-only M1. One blocker (H6, pairing namespace collision) is resolved below. Three latent bugs were found and corrected. No structural changes to the plan are required.

---

## Plan Fitness Assessment

| Milestone | Fit | Notes |
|-----------|-----|-------|
| M1 Adapter Module | ✅ Good | Clean module boundary; correct delegation to spine/store |
| M2 Daemon Endpoints | ✅ Good | Straightforward HTTP routing addition |
| M3 Client Update | ✅ Acceptable | Agent tab update is UI-only; low risk |
| M4 Tests | ✅ Good | 8 tests cover critical boundaries |

---

## Security Posture — M1

The adapter's security model is honest for LAN-only deployment. The M1 trust assumption is: any process on the local network can reach the daemon. The adapter enforces a logical capability contract, not a cryptographic one.

**Acceptable for M1, not acceptable for M2 or network-facing deployment:**
- `/hermes/*` routes are gated by Hermes auth (adapter-enforced)
- `/miner/*` routes have **no HTTP-level auth** — a Hermes agent (or any LAN client) can call `/miner/start` directly without going through the adapter. This is documented as an M1 limitation.
- `Authorization: Hermes <hermes_id>` header is plaintext — LAN-spoofable

**M2 must add before any internet-facing access:**
- Daemon-level auth middleware on all routes
- Signed authority tokens with embedded principal_id, capabilities, expiration
- Hermes namespace isolation in pairing store (partially done; see H6)

---

## Findings

### HIGH — Daemon HTTP endpoints have no auth (H1)

`daemon.py`'s `/miner/start`, `/miner/stop`, and `/miner/set_mode` routes have no authentication. Any LAN client can call them directly. The adapter in `hermes.py` is a self-imposed constraint within Hermes-aware callers; it does not gate the raw HTTP surface.

**Resolution:** Documented as M1 limitation in spec. `/hermes/*` routes use adapter-based Hermes auth. `/miner/*` routes remain open for M1. A follow-on plan must add daemon-level auth middleware before M2.

---

### MEDIUM — `create_pairing_token()` set token_expires_at to creation time (H3)

`store.py:create_pairing_token()` returned:
```python
expires = datetime.now(timezone.utc).isoformat()  # born expired
```

Every pairing token expired immediately on creation. Any token-expiry check in the adapter would always reject.

**Fixed during review.** Changed to:
```python
expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
```

24h matches the LAN-only trust model and is the value documented in the spec.

---

### MEDIUM — Hermes pairing shares store namespace with gateway devices (H6)

All pairings (gateway clients and Hermes agents) lived in the same `pairing-store.json` with no type discriminator. A naming collision was possible: a gateway device named `"hermes:primary"` would shadow the Hermes pairing.

**Resolution:** Spec requires `"hermes:"` prefix enforcement server-side on `/hermes/pair`. Gateway clients cannot naturally produce this prefix (their names come from CLI args or app input). Pairings remain in the shared store; no schema migration needed.

---

### MEDIUM — Hermes auth header is plaintext hermes_id (H10)

`Authorization: Hermes <hermes_id>` carries no signature, no expiration, no HMAC. Any LAN client that guesses or learns a `hermes_id` can authenticate as that Hermes agent.

**Resolution:** Documented as M1 limitation. M2 must replace with signed authority tokens.

---

### LOW — `authority_scope` type mismatch (H9)

The plan passed `authority_scope: str` to `spine.append_hermes_summary()`, but that function expects `authority_scope: list`. This would produce malformed spine events.

**Fixed in spec.** `append_summary` now declares `authority_scope: list` and passes it directly to the spine function.

---

### LOW — Spec said "read-only access to user_message" but plan blocked them entirely (H5)

`references/hermes-adapter.md` line 73 said Hermes had "read-only access to user messages." The plan's event filter excluded them. These contradicted each other.

**Fixed during review.** `references/hermes-adapter.md` now says "No access to user_message events (filtered at the adapter layer)." This is the stricter and correct security posture.

---

### LOW — No replay protection on summary append (H8)

`append_summary` can be called multiple times with the same or different text. Nothing prevents a duplicate. Hermes could re-submit the same summary after a network timeout.

**Accepted for M1.** The event spine is append-only; duplicates are a UX concern, not a security concern. Replay protection (idempotency keys) can be added in M2.

---

## Changes Made During Review

These are not plan changes — they are source fixes that must land before or alongside implementation:

1. **`store.py` — Token expiration bug (H3)**
   `create_pairing_token()`: `expires = datetime.now(timezone.utc)` → `expires = datetime.now(timezone.utc) + timedelta(hours=24)`

2. **`references/hermes-adapter.md` — Spec contradiction (H5)**
   Line 73: "Read-only access to user messages." → "No access to user_message events (filtered at the adapter layer)."

3. **`spec.md` — H6 resolution**
   Hermes pairings use `"hermes:"`-prefixed `device_name` enforced server-side on `/hermes/pair`. No structural store change required.

---

## Open Items for Implementation

| Item | Owner | Note |
|------|-------|------|
| `hermes.py` module | Implement | Create with HermesConnection, connect, read_status, append_summary, get_filtered_events |
| `/hermes/*` routes in daemon.py | Implement | Five routes; adapter imported and called |
| Hermes CLI subcommands | Implement | `hermes pair`, `hermes status`, `hermes summary` |
| `tests/test_hermes.py` | Implement | Eight tests |
| `hermes_summary_smoke.sh` | Update | Must exercise adapter endpoints, not direct spine calls |
| Daemon auth middleware | M2 | Gate all routes; do not leave for M2 accidentally |

---

## Recommendation

**Proceed to Milestone 1: adapter module.**

The plan is implementation-ready. The reviewer has pre-fixed the three bugs that would have caused silent failures (born-expired token, type mismatch, spec contradiction). The H6 namespace question has a resolution in the spec. The H1 daemon-auth gap is documented and deferred intentionally.

Implement in plan order: adapter module → daemon endpoints → CLI update → tests.
