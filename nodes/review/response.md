`★ Insight ─────────────────────────────────────`
**Bootstrap audit trail asymmetry** — `cmd_bootstrap` skips `pairing_requested` and jumps straight to `pairing_granted`, while `cmd_pair` emits both. This means bootstrap-created pairings have no request audit trail in the event spine. In a capability-scoped system where the spine is the source of truth, this is a consistency gap worth tracking — bootstrap is effectively a privileged operation that bypasses the normal request-grant ceremony.

**Auth is a CLI illusion** — The daemon has zero HTTP auth. Capability checks (`observe`/`control`) exist only in `cli.py`. Any `curl` to the daemon bypasses all authorization. The documentation lane is uniquely dangerous here: if the API reference incorrectly claims endpoints are auth-protected, operators will make unsafe deployment decisions based on security properties that don't exist.
`─────────────────────────────────────────────────`

## Delivered Artifacts

- **`outputs/documentation-and-onboarding/spec.md`** — Corrected specification with verified endpoint list, env vars, CLI commands, auth model, and 7 plan accuracy issues documented.

- **`outputs/documentation-and-onboarding/review.md`** — Honest review: lane is **BLOCKED**. The specify stage was a no-op (0 tokens). All 6 frontier tasks are open. The plan contains factual errors (phantom endpoints, broken quickstart, missing env var, misleading security claims). The review includes a Nemesis-style security pass covering trust boundaries, coupled-state asymmetries, and inert token lifecycle.

### Key findings:

1. **Specify was a no-op** — MiniMax produced 0 tokens, nothing was written
2. **3 phantom endpoints** in the plan (`/spine/events`, `/metrics`, `/pairing/refresh`)
3. **Quickstart is broken** — wrong device name, insufficient capabilities
4. **Zero HTTP auth** — daemon is wide open, auth is CLI-only
5. **Token system is cosmetic** — expires_at is never checked, token_used is never updated
6. **Bootstrap skips request event** — audit trail gap vs. normal pairing

### To unblock: adopt the corrected `spec.md`, re-run specify or skip to implementation.