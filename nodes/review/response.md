`★ Insight ─────────────────────────────────────`
**Why C1 + C2 matter together:** Individually, each finding is a medium-severity auth weakness. Together they form a **complete bypass chain**: C1 means any caller can retrieve a token by re-pairing, and C2 means you don't even need the token after connection — just the hermes_id. The defense-in-depth on the capability boundary (adapter checks + daemon header checks on control endpoints) is well-done, but it's protecting a door whose lock is already broken at the authentication layer.

**The whitelist vs blacklist choice** for event filtering (`hermes.py:278-279`) is a strong security decision. Blacklisting `USER_MESSAGE` would mean any new event kind added to the spine is automatically visible to Hermes. The whitelist approach means new event kinds are blocked by default and must be explicitly granted. This is the correct pattern for a least-privilege adapter.
`─────────────────────────────────────────────────`

---

## Summary

**CONDITIONAL APPROVAL.** The capability scoping logic is correct and well-layered. Milestone 1 functional requirements are met. Two critical findings need remediation:

| Severity | Count | Key Items |
|---|---|---|
| **Critical** | 2 | C1: idempotent pairing leaks token. C2: post-connect auth doesn't require token |
| **High** | 3 | Unauthenticated pairing, broken expiration field, import ordering |
| **Medium** | 6 | No revocation, no rate limits, no connection expiry, principal attribution, error leakage, non-atomic writes |
| **Low** | 6 | Filter heuristic, contract divergence, state fragmentation, file permissions, CORS, audit gap |

**Before merge:** Fix C1, C2, and H3 (import ordering — trivial). The high findings (H1, H2) are acceptable for localhost-only MVP if documented as known limitations.

**Before next milestone:** Add `tests/test_hermes.py`, implement Hermes revocation (M1), and decide on the token model (lookup vs encoded per reference contract).

The review document has been written to `outputs/hermes-adapter-implementation/review.md`.