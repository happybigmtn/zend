# Hermes Adapter Implementation — Lane Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-23
**Reviewer:** Codex (polish stage)
**Spec file:** `outputs/hermes-adapter-implementation/spec.md`

---

## Spec Quality Assessment

### Strengths

1. **Correctly scoped.** The slice is narrow and defensible: it establishes the Hermes trust boundary without trying to also wire up the inbox, the UI, or remote access. This matches the lane's stated frontier tasks exactly.

2. **Grounded in existing code.** The spec references actual existing surfaces:
   - `miner.get_snapshot()` (daemon.py)
   - `EventKind.HERMES_SUMMARY` and `append_hermes_summary()` (spine.py)
   - `load_pairings()` / `save_pairings()` / `pair_client()` (store.py)
   This makes it implementable without guesswork about what already exists.

3. **Token model is sound.** The authority token is a signed, expirable, cap-scoped credential with a clear lifecycle: pair → connect → issue signed token → validate on each request. This matches how real delegated authority works.

4. **Event filtering is explicit.** The spec names the exact `EventKind` values that are blocked (`user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`) and explains why each is blocked. This prevents the common "we forgot to filter X" bug.

5. **Capability independence is correct.** The spec correctly notes that Hermes capabilities (`observe`, `summarize`) are independent from gateway device capabilities. This is architecturally important and easy to get wrong.

6. **Store changes are specified precisely.** Rather than saying "extend store.py", the spec includes the exact new functions and dataclasses needed. This prevents the ambiguity that leads to implementation drift.

7. **Error codes are enumerated.** `HERMES_UNAUTHORIZED`, `HERMES_TOKEN_INVALID`, `HERMES_TOKEN_EXPIRED`, `HERMES_NOT_PAIRED` are specific enough to be actionable and do not collide with other daemon error codes.

8. **Acceptance criteria are testable.** Each criterion maps to a specific named test. This is the right granularity — not so fine that the table is unreadable, not so coarse that "works" is unfalsifiable.

### Concerns / Recommended Fixes Before Implementation

1. **The `Authorization: Hermes` header is underspecified for requests.** The spec shows the header on the client side but does not specify exactly how the daemon extracts and uses the `hermes_id` from it vs. how the authority token is passed (currently shown as `X-Authority-Token`). These two mechanisms need to be unified: either the token IS the auth credential (header carries the full base64 token) or the header carries the hermes_id and a separate header carries the token. Recommend: `Authorization: Hermes <base64-authority-token>` — the daemon parses the token, extracts `hermes_id` from it, and validates in one step. This is simpler and avoids a second lookup.

2. **`_sign_token` / HMAC key is not specified.** The token validation calls `_sign_token(token)` but the spec never names the HMAC secret or how it is derived. This must be: the daemon has a `DAEMON_SECRET` environment variable (or a file on disk) used as the HMAC-SHA256 key. Without this, the signature scheme cannot be implemented consistently.

3. **Token expiration is set at connect time but the spec does not say for how long.** Recommend adding a `HERMES_TOKEN_TTL_SECONDS = 3600` constant (1 hour) so the implementor does not have to guess.

4. **The `connect()` function signature shows `authority_token: str` as input, but the pairing flow issues a new token on connect.** This means `connect()` is called with the pairing token (UUID), not the authority token. The naming in the spec is slightly confusing: `POST /hermes/connect` takes `pairing_token` and returns `authority_token`. Recommend clarifying the two-token model (pairing token vs. authority token) in the `connect()` docstring.

5. **`store_hermes_authority_token` is listed but there is no eviction policy.** Long-running Hermes agents will accumulate tokens in the store. Recommend: store a single active token per `hermes_id` (overwrite on each connect), and prune expired tokens on startup.

6. **The `daemon.py` modifications section is implicit.** The spec describes the HTTP endpoints but does not say how `GatewayHandler` should be extended (new methods? new mixin?). Recommend a short paragraph noting that `GatewayHandler.do_GET` and `GatewayHandler.do_POST` dispatch to hermes sub-paths, or that a `HermesHandler` class is added alongside `GatewayHandler`.

---

## Implementation Readiness

The spec is **ready for implementation** with the following clarifications to be resolved during coding (not blocking spec approval):

| Issue | Resolution |
|-------|------------|
| Auth header format | `Authorization: Hermes <base64-authority-token>` — parse token, extract `hermes_id`, validate |
| HMAC secret | `DAEMON_SECRET` env var or `$STATE_DIR/daemon.secret`; derive key with SHA256 |
| Token TTL | `HERMES_TOKEN_TTL_SECONDS = 3600` constant in `hermes.py` |
| Two-token naming | Clarify: `pairing_token` (UUID, used at connect) → `authority_token` (signed JWT-like, used per request) |
| Token storage | Single active token per `hermes_id`, overwrite on reconnect |
| Daemon handler | Add `HermesHandler` class or extend `GatewayHandler` dispatch |

---

## What the Next Stage Must Deliver

The implementation stage (`001` lane, or equivalent) must produce:

1. **`services/home-miner-daemon/hermes.py`** with:
   - `HermesAuthorityToken` dataclass
   - `HermesConnection` dataclass
   - `HermesNotPairedError`, `TokenExpiredError`, `TokenInvalidError` exceptions
   - `generate_authority_token()` — creates signed token on connect
   - `validate_authority_token()` — validates signature + expiration + capabilities + pairing status
   - `connect(pairing_token, hermes_id)` — validates pairing, returns `HermesConnection` with signed authority token
   - `read_status(connection)` — checks observe cap, returns `miner.get_snapshot()`
   - `append_summary(connection, summary_text, authority_scope)` — checks summarize cap, calls `spine.append_hermes_summary()`
   - `get_filtered_events(connection, limit)` — returns spine events minus blocked kinds

2. **`services/home-miner-daemon/store.py`** additions:
   - `HermesPairing` dataclass
   - `HERMES_PAIRING_FILE` path constant
   - `load_hermes_pairings()`, `save_hermes_pairings()`
   - `create_hermes_pairing()`, `get_hermes_pairing()`, `is_hermes_paired()`
   - `get_hermes_authority_token()`, `store_hermes_authority_token()`

3. **`services/home-miner-daemon/daemon.py`** additions:
   - `HermesHandler` class (or extended dispatch in `GatewayHandler`)
   - `POST /hermes/pair` — creates pairing, returns token
   - `POST /hermes/connect` — validates pairing token, issues authority token
   - `GET /hermes/status` — Hermes auth required
   - `POST /hermes/summary` — Hermes auth required
   - `GET /hermes/events` — Hermes auth required

4. **`services/home-miner-daemon/tests/test_hermes.py`** — all 11 tests listed in the spec

---

## Security Notes

- The authority token HMAC secret must not be guessable or replayable. An attacker who obtains a valid token can impersonate Hermes until expiry. Token delivery (during `POST /hermes/connect`) should ideally happen over a private channel (LAN, not Internet).
- The `hermes_id` in the token must match the `hermes_id` in the pairing store. A token issued to `hermes-001` must not be usable by `hermes-002`.
- The event filtering is an enforcement boundary, not just a UI filter. A misconfigured `get_filtered_events` that accidentally returns `user_message` events would expose private communications to Hermes.
- Control commands (`/miner/start`, `/miner/stop`) are not Hermes endpoints and should not be reachable via Hermes auth at all. If `HermesHandler` is a separate class, it should not proxy to `MinerSimulator` control methods.

---

## Verdict

**Spec status: ACCEPTED** — ready for implementation with the minor clarifications noted above.

The spec correctly captures the architecture, the trust boundary, the token lifecycle, the event filtering policy, and the acceptance criteria. The concerns raised are implementation details that do not block the spec but must be resolved during coding.
