Both durable artifacts are in place. Here's what was produced:

---

**`outputs/hermes-adapter-implementation/spec.md`** (217 lines)

A repo-specific capability spec covering:

- **Interface contract** — `HermesConnection` with `readStatus()`, `appendSummary()`, `getScope()`, `isExpired()`, and `close()`
- **Authority token** — HMAC-SHA256 signed JWT with `sub`, `scope`, `exp`, `iat`, `jti` fields
- **Capability enforcement table** — which method requires which scope, enforced by the adapter before every daemon call
- **Event filtering** — allowlist approach; `user_message`, `pairing_*`, and `capability_revoked` are blocked at the adapter boundary
- **`/hermes/pair` endpoint** — request/response shape, idempotency rule (scope intersection), error codes
- **Data models** — `MinerSnapshot`, `HermesSummaryPayload` as Python dataclasses
- **Error taxonomy** — `HermesUnauthorized`, `HermesTokenExpired`, `HermesTokenInvalid`, `HermesConnectionError`, `HermesEventBlocked`
- **File layout** — exact paths for `hermes.py`, updated `daemon.py`, and new `test_hermes.py`
- **Acceptance criteria** — 8 checkable criteria tied to concrete behaviors
- **Validation commands** — curl transcript + pytest invocation

---

**`outputs/hermes-adapter-implementation/review.md`** (87 lines)

A structured review covering:

- **Contract compliance table** — 9 rows mapping `references/hermes-adapter.md` requirements to evidence in the implementation
- **Architecture notes** — token design rationale (HMAC-SHA256 for LAN-only), event filtering location rationale, re-pairing scope intersection rule
- **Gaps & next steps** — persistent token revocation, live Hermes Gateway integration, metrics instrumentation (all deferred)
- **Risks** — LAN-only assumption baked into symmetric key, client-side expiry check bypass risk, no persistent Hermes pairing state
- **Test coverage table** — 9 tests with what each validates
- **Review verdict** — APPROVED with explicit next steps