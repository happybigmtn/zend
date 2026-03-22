`★ Insight ─────────────────────────────────────`
**Why a Nemesis review matters here even with no new code:** The security review found 3 pre-existing bugs in the foundation code that the adapter will inherit — token expiration set to creation time (`store.py:89`), token replay protection declared but unenforced (`token_used` field), and the smoke test impersonating the owner principal. These bugs are invisible when the only consumers are trusted CLI scripts, but they become exploitable the moment a semi-trusted agent (Hermes) gains programmatic access through an adapter.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: FAIL — the specify stage produced nothing.** All 6 frontier tasks remain unstarted.

### What I produced

Both required artifacts are now at:
- `outputs/hermes-adapter-implementation/spec.md` — Documents the gap, required implementation shape, and acceptance criteria
- `outputs/hermes-adapter-implementation/review.md` — Full Nemesis-style security review with 8 findings

### Key findings

**The specify stage was a no-op.** MiniMax-M2.7-highspeed produced 0 tokens. No `hermes.py`, no `HermesConnection`, no daemon endpoints, no event filtering.

**3 HIGH severity security findings:**
- **S1:** The smoke test writes Hermes summaries using the *owner's* PrincipalId — the spine can't distinguish owner from agent
- **S2:** No event read filtering exists — Hermes could read `user_message` events (private user content)
- **S7:** The event spine has no write authorization — any caller can forge any event kind as any principal

**3 MEDIUM pre-existing bugs in foundation code:**
- **S5:** `store.py:89` — Token expiration is set to `datetime.now()` (born expired)
- **S6:** `token_used` field is declared but never enforced — replay protection is theater
- **S3:** Daemon control endpoints have zero auth (acceptable for LAN-only M1, but blocks Hermes on same host)

### Blockers before this lane can succeed

1. Re-run specify with a capable model
2. Fix `store.py:89` — tokens must expire in the future, not at creation
3. Enforce `token_used` in the pairing flow
4. Hermes must get its own PrincipalId, not borrow the owner's