`★ Insight ─────────────────────────────────────`
**Key architectural finding:** The Zend implementation has a split-brain authority model. Capability enforcement (`observe`/`control`) lives exclusively in the CLI layer (`cli.py`), while the daemon (`daemon.py`) accepts all HTTP requests unconditionally. This means the security model is only as strong as the assumption that all callers go through the CLI — any direct HTTP call bypasses it entirely. This pattern is common in early prototypes but must be fixed before the trust boundary claim has meaning.

**Coupled-state risk:** The pairing store and event spine are not transactional. A crash between "store write" and "spine append" leaves the system in an inconsistent state where a client is paired but no audit trail exists. This matters for a system whose spec says "the event spine is the source of truth."
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONAL** — the scaffolding and contracts are well-structured, but the existing review's "APPROVED — First slice is complete" is premature.

### Correctness
- PrincipalId sharing, event spine schema, simulator contract, and CLI script wrappers are **correctly implemented**
- LAN-only binding, encryption, inbox integration, and Hermes adapter are **claimed but not enforced or implemented**

### Milestone Fit
- **6 of 13** ExecPlan acceptance criteria fully met, 3 partially met, 4 not met
- Major gaps: no working inbox, no encryption, no Hermes adapter, no tests

### Security (Nemesis)
- **Critical:** Daemon has zero authentication — any local process can control the miner via direct HTTP, bypassing the CLI's capability model
- **Critical:** Event spine stores plaintext JSON while the contract specifies encryption
- **High:** `ZEND_BIND_HOST` env var allows binding to `0.0.0.0` with no validation, defeating the LAN-only guarantee
- **Medium:** Pairing tokens are created but never validated (born-expired bug at `store.py:89`); replay attacks are structurally possible
- **Medium:** No transaction boundary between pairing store and spine — crash between them creates inconsistent state
- **Low:** Daemon restart resets miner state to STOPPED while spine retains history of START, creating a divergence

### Artifacts Delivered
- `outputs/carried-forward-build-command-center/review.md` — this review
- `outputs/carried-forward-build-command-center/spec.md` — copied from specify stage output