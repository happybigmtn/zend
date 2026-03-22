`★ Insight ─────────────────────────────────────`
Three architectural lessons from this review:

1. **Capability enforcement must live at the data layer, not the CLI layer.** The existing codebase enforces `observe`/`control` only in `cli.py` command handlers. The HTTP endpoints in `daemon.py` are wide open. This is a classic "security at the wrong layer" — any new consumer (like Hermes) that talks HTTP bypasses all capability checks. The fix is to push authentication into the daemon handler itself.

2. **Delegated principals vs. shared principals.** The current design has one principal (the owner). Hermes writing events under the owner's principal makes the audit trail meaningless — you can't distinguish "the owner did this" from "Hermes did this." The adapter needs its own principal, which is a design decision the contracts hinted at but never made explicit.

3. **Token lifecycle bugs compound.** The `create_pairing_token()` function generates tokens that expire at `now()` and the `token_used` flag is never flipped. These two bugs together mean: tokens are simultaneously expired AND replayable. Either bug alone might be caught by a different check, but together they create a state where no token is ever valid AND no token is ever consumed.
`─────────────────────────────────────────────────`

---

## Review Summary

**Verdict: NOT APPROVED — the lane produced zero implementation.**

The specify stage was a no-op (MiniMax-M2.7-highspeed, 0 tokens). No `hermes.py` exists. 0 of 6 frontier tasks were addressed.

### What I delivered

- **`outputs/hermes-adapter-implementation/review.md`** — full Nemesis-style 2-pass security review
- **`outputs/hermes-adapter-implementation/spec.md`** — corrective spec capturing what must be built

### Critical findings (12 total, 2 Critical/High):

| Severity | Count | Highlights |
|----------|-------|------------|
| Critical | 1 | P1-2: Authority token contract entirely unimplemented |
| High | 4 | P1-1: No Hermes/owner trust boundary; P1-3: Daemon unauthenticated; P2-1: Tokens born expired; P2-2: Replay prevention broken |
| Medium | 5 | Privacy leak on `user_message`, no miner control gating, no file locking, missing `summarize` capability, no connection lifecycle |
| Low | 2 | Shell injection in smoke test, no idempotency on summary append |

### Pre-existing bugs in home-miner-daemon (not caused by this lane but blockers for adapter):

1. **`store.py:89`** — `create_pairing_token()` sets expiration to `now()`, making every token instantly expired
2. **`store.py`** — `token_used` field is never flipped to `True`
3. **`store.py` + `spine.py`** — no file locking for concurrent access via `ThreadedHTTPServer`

### Recommended next step

Re-run the lane with a capable model. The spec artifact I wrote captures the full requirements, interfaces, security constraints, and acceptance criteria needed to implement the adapter.