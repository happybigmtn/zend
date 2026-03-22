`★ Insight ─────────────────────────────────────`
**Why this review matters for the project:**
1. The specify stage was a no-op (0 tokens), meaning the plan was never validated against the actual codebase before reaching review. This is exactly the kind of drift that documentation lanes are supposed to prevent — and the review caught it.
2. The most dangerous finding is N1.1: the plan would have documentation claim HTTP-layer auth that doesn't exist. An operator reading "requires control capability" next to `POST /miner/start` would believe the endpoint is protected. It isn't — any LAN device can start/stop the miner via direct HTTP. Honest documentation of the security posture is more valuable than aspirational documentation.
3. The `spine.py` kind filter bug (N2.2) is a good example of why "verify documentation accuracy by following it on a clean machine" (Milestone 6 in the plan) is the most important milestone — it would have caught this crash immediately.
`─────────────────────────────────────────────────`

## Review Complete

**Verdict: BLOCKED** — 7 factual errors in the plan must be corrected before implementation.

### Critical findings:

1. **3 phantom endpoints** (`/spine/events`, `/metrics`, `/pairing/refresh`) don't exist in code — the API reference would document 404s
2. **Quickstart is broken** — bootstrap grants `observe` only, but the example runs a `control` command that fails with "unauthorized"
3. **Zero test files exist** — the plan claims a `pytest` command that discovers nothing
4. **Health response is wrong** — plan says `{"status": "ok"}`, actual is `{"healthy": true, "temperature": 45.0, ...}`
5. **HTTP auth is overstated** — all endpoints are unauthenticated at the HTTP layer; capability checks exist only in CLI

### Nemesis security findings:

- **N1.1**: Docs would create false auth assurance for operators
- **N1.2**: Token TTL is a dead placeholder (expires at creation)
- **N2.1**: Store + spine writes are not atomic
- **N2.2**: `spine.py get_events()` kind filter crashes with string input (code bug)

### Artifacts written:

- `outputs/documentation-and-onboarding/spec.md` — verified codebase surface with corrections list
- `outputs/documentation-and-onboarding/review.md` — full Nemesis review with verdicts

All corrections are editorial. No architectural changes needed. The lane can unblock with < 1 hour of plan fixes.