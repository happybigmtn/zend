`★ Insight ─────────────────────────────────────`
**Why documentation lanes need adversarial review against code, not just plans:**

1. **The "specify" stage generated its spec from the plan text, not the code.** The MiniMax model that ran the specify stage appears to have parroted the plan's endpoint list without reading `daemon.py`. This is exactly the failure mode the plan itself warns about: documentation drift. The irony is that the drift happened before a single doc was written.

2. **Auth architecture has a split-brain problem that documentation would hide.** The daemon is unauthenticated (any LAN process can POST to it), while the CLI enforces capability checks. If docs say "this endpoint requires control capability," a security-conscious operator reads that as HTTP-level auth and deploys with false confidence. Honest documentation is a security control.

3. **Phantom surfaces in plans are common when plans are written aspirationally.** The plan listed `/spine/events`, `/metrics`, and `/pairing/refresh` because they _should_ exist, not because they do. Review catches this before those phantoms become "documented API" that someone builds against.
`─────────────────────────────────────────────────`

---

## Review Summary

**Verdict: CONDITIONAL PASS**

Both artifacts written:
- `outputs/documentation-and-onboarding/spec.md` — ground-truth specification of what documentation must accurately reflect
- `outputs/documentation-and-onboarding/review.md` — Nemesis-style adversarial review

### 4 Blockers (must fix before docs are written)

1. **Phantom endpoints**: `/spine/events`, `/metrics`, `/pairing/refresh` don't exist in the daemon. Strike from plan Milestone 4.
2. **Phantom env var**: `ZEND_TOKEN_TTL_HOURS` isn't read by any code. Remove from plan Milestone 3.
3. **Wrong health response**: Plan claims `{"status": "ok"}`, actual response is `{"healthy": true, "temperature": ..., "uptime_seconds": ...}`.
4. **Auth model misrepresentation**: Auth is CLI-layer only. The daemon HTTP API is completely unauthenticated. Docs must not claim endpoint-level auth.

### 6 Warnings (non-blocking but should inform the docs)

- Token TTL is a dead stub (expires at creation, no lookup mechanism)
- Spine + store writes are not atomic (crash can orphan pairing records)
- State files use default umask (world-readable on multi-user systems)
- No runtime guard against public bind (`0.0.0.0` exposes unauthenticated API)
- Plan says "encrypted" but spine is plaintext JSONL
- PID file has a TOCTOU race in the bootstrap script