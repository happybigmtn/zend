`★ Insight ─────────────────────────────────────`
**Why documentation lanes need code-level verification:**

This review illustrates a common failure mode in plan-driven development — the documentation plan was authored from the *spec and ExecPlan documents*, not from reading the *implementation*. The spec says "encrypted event spine," so the plan says to document "encrypted event spine." The spec mentions `GET /metrics`, so the plan includes it. But the code tells a different story. Documentation authored from plans-about-plans inherits every unfulfilled aspiration as a stated fact. The fix is simple: documentation plans must be verified against `grep`, not against other plans.

The Nemesis finding about the auth model is particularly important. The plan would have users documenting per-endpoint auth requirements (`none`, `observe`, `control`) — creating a false sense of defense-in-depth. The reality is simpler and more honest: the daemon is wide open, the CLI is the enforcement layer, and the network binding is the security boundary. Honest documentation of a simple security model is always better than aspirational documentation of a complex one.
`─────────────────────────────────────────────────`

## Review Complete

**Verdict: CONDITIONAL PASS** — the lane is structurally sound but the plan has five factual errors that would produce misleading documentation.

### Blocking corrections needed (plan text only, no code):

| # | Issue | Fix |
|---|-------|-----|
| C1 | 3 phantom endpoints (`/spine/events`, `/metrics`, `/pairing/refresh`) | Remove from API reference milestone |
| C2 | Phantom env var `ZEND_TOKEN_TTL_HOURS` | Replace with `ZEND_DAEMON_URL` |
| C3 | Auth model implies daemon-level enforcement | Document honestly: CLI has checks, daemon is open, LAN binding is the boundary |

### Minor corrections:

| # | Issue | Fix |
|---|-------|-----|
| C4 | Bootstrap fails on re-run (duplicate device name) | Add state-wipe note or fix script idempotence |
| C5 | README references test suite that doesn't exist | Remove pytest line until tests are created |

### Security findings (Nemesis):

- **N1**: Daemon has zero HTTP auth — docs must say so, not imply per-endpoint auth
- **N3**: Event spine is plaintext JSONL, not encrypted — docs must not claim encryption
- **N4**: Token expiration is broken (expires at creation, never checked) — not documentable as a security feature

Artifacts written to `outputs/documentation-and-onboarding/spec.md` and `outputs/documentation-and-onboarding/review.md`.