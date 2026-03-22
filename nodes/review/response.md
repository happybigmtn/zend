`★ Insight ─────────────────────────────────────`
**The documentation was written from the spec, not from the code.** This is the single root cause behind almost every finding. The spec's endpoint table (lines 85-91) lists endpoints that exist in the *design* but not in `daemon.py`. The spec also describes capability-scoped HTTP auth that only exists in the CLI layer. The docs faithfully reproduced the spec's vision, but nobody ran `curl` against the actual daemon to verify.

**Append-only vs overwrite is an architectural split.** The spine (`event-spine.jsonl`) is append-only and crash-tolerant by design. The pairing store (`pairing-store.json`) is full-file overwrite and crash-vulnerable. These two stores are semantically coupled (pairing events appear in both) but have different durability guarantees. A crash between the two writes creates a split-brain state with no reconciliation.

**The "auth model" is a documentation-layer fiction.** The daemon is a zero-auth HTTP server. The capability checking in `store.py` is invoked only by the CLI, which runs locally and then makes unauthenticated HTTP calls to the daemon. Any process that can reach port 8080 has full control. This isn't necessarily wrong for milestone 1 on a home LAN, but the docs must not claim otherwise.
`─────────────────────────────────────────────────`

## Summary

**Verdict: BLOCKED** — 2 missing artifacts, 7 correctness failures, 3 security concerns.

The review is at `outputs/documentation-and-onboarding/review.md`. Key findings:

1. **`docs/architecture.md` doesn't exist** — spec requires it, README links to it
2. **Two ghost HTTP endpoints** documented (`GET /spine/events`, `POST /pairing/refresh`) that return 404
3. **Quickstart is broken** — bootstrap grants `observe` only, but step 5 needs `control`
4. **Auth model is fiction** — docs describe capability-scoped HTTP auth; daemon has zero auth
5. **Gateway URLs are wrong** — daemon doesn't serve static files
6. **No tests exist** despite pytest instructions in two docs
7. **`get_events` CLI command crashes** when filtering by kind (string vs enum `.value` bug)
8. **Pairing store is not crash-safe** — full-file overwrite vs spine's append-only
9. **Bootstrap is not idempotent** — second run fails with "already paired"
10. **Token expiry is broken** — tokens expire at creation time, never checked

The docs are well-structured and cover the right topics. The fix is mechanical: verify every claim against the running daemon and correct what's wrong. The core issue is that docs were written from the spec's design table, not from observed behavior.