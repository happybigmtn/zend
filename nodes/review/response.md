---

## Review Complete

**Verdict: Do not merge as-is. Four blockers must be fixed first.**

### The 4 blockers in priority order:

1. **B1 — Double-call on control endpoints** (`daemon.py:196-204`): `miner.start()` called twice per request — first call changes state, second call returns "already running." Every control endpoint is functionally broken.

2. **B2 — Duplicate `do_GET`** (`daemon.py:170 vs 299`): First definition is silently dead. Latent correctness trap.

3. **B3 — Tokens expire at issuance** (`hermes.py:215,229`): `token_expires_at` set to `now()` instead of `now() + 24h`. Currently masked because tokens aren't used for ongoing auth.

4. **B4 — Orphaned PrincipalId** (`hermes.py:238-249`): Hermes creates its own principal via a path that doesn't persist and doesn't match `store.py`. Breaks the shared-PrincipalId contract from the product spec.

### The critical security finding:

The authority token system is **ceremonial** — `/hermes/connect` validates it, but all subsequent operations (`/hermes/status`, `/hermes/summary`, `/hermes/events`) authenticate by bare `hermes_id` header against the pairing store. No session binding exists. This is acceptable for LAN-only M1 if explicitly documented, but must be addressed before any network exposure or plan 006.

### What the implementation gets right:

The core adapter design is sound. Capability allowlist, event filtering by positive list, payload field stripping, defense-in-depth on control blocking, idempotent pairing, and thorough unit tests (20/20 passing). The architecture correctly positions Hermes as a constrained consumer of the Zend gateway, not a peer.

Artifacts written to `outputs/hermes-adapter-implementation/review.md` and `outputs/hermes-adapter-implementation/spec.md`.