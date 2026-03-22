18 tests pass. I've now read all implementation files, the spec, the reference contract, the design doc, the plan, and the upstream modules. Here's the nemesis-style review.

---

# Hermes Adapter — Security Review

## Pass 1: First-Principles Challenge

### CRITICAL: Authority tokens have NO cryptographic integrity

`hermes.py:159-218` — `connect()` accepts a JSON blob as the authority token. There is no signature, HMAC, or any cryptographic binding. The "validation" only checks:
1. JSON structure is valid
2. Fields are present
3. Expiration hasn't passed
4. Capabilities are in the allowlist
5. A pairing record exists with matching `principal_id`

**Attack:** Any process on the LAN that learns a `hermes_id` and `principal_id` (both returned in plaintext by `/hermes/pair`) can forge a valid authority token:

```python
forged = json.dumps({
    "hermes_id": "hermes-001",
    "principal_id": "<known>",
    "capabilities": ["observe", "summarize"],
    "expires_at": "2099-01-01T00:00:00+00:00"
})
```

The `expires_at` is attacker-controlled. The pairing record's `token_expires_at` is never checked during `connect()` — only the token's own claim is trusted.

**Severity:** High for milestone 1 (LAN-only reduces blast radius). Blocker for any network-exposed future.

### CRITICAL: Miner control endpoints have zero authentication

`daemon.py:232-244` — The `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints perform no authorization check whatsoever. The Hermes adapter's `validate_control_attempt()` (which always returns `False`) is never called by any HTTP handler. The control boundary exists only inside the adapter module's function signatures, not at the daemon's HTTP boundary.

**Impact:** The entire premise of "Hermes cannot issue control commands" is enforced only in the adapter's Python functions, not at the API boundary. Any HTTP client — including a Hermes agent — can `POST /miner/start` directly, bypassing the adapter entirely.

The CLI's `cmd_hermes_test_control` would **correctly** flag this as a security issue if run against a stopped miner.

### HIGH: `/hermes/pair` endpoint has no authentication

`daemon.py:287-307` — Anyone on the LAN can call `POST /hermes/pair` with an arbitrary `hermes_id`. The response includes a fully-formed authority token. There is no operator approval, no challenge, no confirmation step.

Combined with the unsigned token issue above: any LAN client can self-pair, self-issue a token, and gain observe+summarize access in a single request.

### MEDIUM: Hermes auth scheme is knowledge-of-ID only

`daemon.py:173-192` — After connecting, subsequent requests authenticate with `Authorization: Hermes <hermes_id>`. Knowing the `hermes_id` string (which is returned by the pair endpoint and chosen by the caller) is sufficient to impersonate a connected Hermes agent.

No session token, no nonce, no bearer token. The `hermes_id` is both the identifier and the credential.

---

## Pass 2: Coupled-State Review

### Token duality — two independent token systems, neither complete

`hermes.py:105-148` creates a `HermesPairing` with a UUID `token` and `token_expires_at`.
`hermes.py:348-366` creates an `AuthorityToken` (JSON blob) with its own `issued_at` and `expires_at`.

These are **completely separate tokens**. The UUID in the pairing record is stored but never verified. The authority token's expiration is self-asserted and independent of the pairing's `token_expires_at`. There is no mechanism to:
- Revoke an issued authority token
- Track which authority tokens exist for a pairing
- Invalidate a connection when a pairing is modified

### Idempotent re-pair issues new token

`daemon.py:297-298` — On idempotent re-pair (same `hermes_id`), `pair_hermes()` returns the existing pairing unchanged, but the endpoint still calls `generate_authority_token()`, issuing a fresh authority token with a new `expires_at`. The old token also remains valid. There is no token rotation or invalidation.

### In-memory connection state is detached from persistent pairing state

`daemon.py:161` — `_hermes_connections` is a class-level dict. Once a connection is established:
- Deleting/modifying the pairing record doesn't invalidate the connection
- Restarting the daemon clears all connections (no persistence)
- The connection object carries its own `capabilities` list, copied at connect time

### Thread safety on shared mutable state

`daemon.py:161` — `_hermes_connections` is a class variable mutated from `_do_hermes_post` (connect) and read from `_require_hermes_connection`. `ThreadedHTTPServer` creates a new handler instance per request, but class variables are shared. No lock protects this dict.

`hermes.py:91-102` — `_load_hermes_pairings()` / `_save_hermes_pairings()` do full read-modify-write on a JSON file with no file locking. Concurrent pairing requests could lose data.

### No size bound on summary text

`hermes.py:254-297` — `append_summary()` accepts `summary_text` of arbitrary length. A Hermes agent could write arbitrarily large payloads to the append-only event spine, filling disk. No truncation, no size check.

### Event over-fetch heuristic may under-deliver

`hermes.py:315` — `get_filtered_events()` fetches `limit * 3` events to compensate for filtering. If the spine is dominated by `user_message` events, the 3x factor may be insufficient and the returned list will be shorter than `limit`. Not a security issue, but a correctness deviation from the spec's contract.

---

## Milestone Fit Assessment

The implementation correctly maps the reference contract's interface (`references/hermes-adapter.md`). The capability model (observe + summarize, no control), event filtering (block user_message), and adapter boundaries are all structurally present. Tests cover the adapter functions thoroughly.

**However**, the security boundary is skin-deep: it exists at the Python function level but not at the HTTP/protocol level. For a milestone 1 LAN-only simulator this is an acceptable known gap **only if documented as such**. If this were to be deployed or extended, the unsigned tokens and unprotected control endpoints would be the first two things an attacker exploits.

---

## Findings Summary

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| 1 | CRITICAL | Authority tokens are unsigned JSON — any LAN client can forge tokens with arbitrary expiration | `hermes.py:159-218` |
| 2 | CRITICAL | `/miner/start`, `/stop`, `/set_mode` have zero auth — Hermes control boundary not enforced at HTTP layer | `daemon.py:232-244` |
| 3 | HIGH | `/hermes/pair` requires no authentication — self-service pairing with token in response | `daemon.py:287-307` |
| 4 | MEDIUM | Auth scheme is knowledge-of-ID — `hermes_id` is both identifier and credential | `daemon.py:173-192` |
| 5 | MEDIUM | Two independent token systems, neither revocable | `hermes.py:105-148`, `hermes.py:348-366` |
| 6 | MEDIUM | Thread-unsafe mutation of `_hermes_connections` and pairing file | `daemon.py:161`, `hermes.py:91-102` |
| 7 | LOW | No size bound on `summary_text` — disk exhaustion via spine | `hermes.py:254-297` |
| 8 | LOW | Event over-fetch heuristic can under-deliver results | `hermes.py:315` |

## Remaining Blockers

1. **Document the unsigned-token gap** as a known milestone 1 limitation. The current review.md says "PASS — Security" which is misleading.
2. **The control endpoint auth gap (#2) should be fixed even for milestone 1** — the entire Hermes narrative depends on "Hermes cannot control the miner," but right now any HTTP client can. At minimum, add a note to the spec that control endpoints are unprotected and the adapter boundary is informational only.
3. The `cmd_hermes_test_control` CLI command will correctly detect issue #2 if run against a real daemon. This is good — it's an honest test. But it means the "all tests pass" claim in the review is only true for unit tests, not integration tests.

`★ Insight ─────────────────────────────────────`
The core architectural tension here is **enforcement depth**. The adapter enforces capabilities at the function-call level, but the daemon's HTTP endpoints sit in front of the adapter and don't participate in the enforcement. This is a common pattern in milestone-1 code: the domain logic is correct, but the transport layer doesn't enforce the domain's invariants. The fix isn't necessarily adding full auth to every endpoint right now — it's making the gap visible so nobody ships this boundary as-is.

The unsigned token design is the second classic pattern: using a structured data format (JSON) as a "token" without any integrity guarantee. In a LAN-only simulator this is tolerable, but the code should comment that the token format is a placeholder. Without that annotation, a future contributor might assume the token validation in `connect()` is actually providing authentication.
`─────────────────────────────────────────────────`