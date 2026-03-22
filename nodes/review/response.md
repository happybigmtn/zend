`★ Insight ─────────────────────────────────────`
**Why documentation lanes need security reviews**: This review surfaced that the codebase's reference contracts (event-spine.md, inbox-contract.md, hermes-adapter.md) describe a system with encryption, capability enforcement, and structured observability — none of which are implemented. If docs were written by naively reading the contracts, they'd describe a system that doesn't exist. The Nemesis review pattern (first-principles trust challenge + coupled-state audit) catches exactly this class of problem: aspirational contracts masquerading as implementation.

**The pairing token anti-pattern**: `create_pairing_token()` generates a token with `expires = datetime.now()` — the token is expired at birth. Combined with `token_used` never being checked, the entire token lifecycle is dead code. This is a common milestone-1 risk: stub fields that get documented as real security mechanisms.
`─────────────────────────────────────────────────`

## Review Complete

Both artifacts produced:
- `outputs/documentation-and-onboarding/spec.md` — placeholder recording the specify stage failure
- `outputs/documentation-and-onboarding/review.md` — full review

**Top-line findings:**

1. **Lane is BLOCKED** — specify stage (MiniMax-M2.7-highspeed) produced 0 tokens. No spec, no docs, zero frontier tasks attempted. The pipeline's success check is broken (exit code 0 ≠ output exists).

2. **README is actively wrong** — says "no implementation code" when a working daemon, CLI, UI, and 7 shell scripts exist.

3. **Nemesis Pass 1 (trust/authority):**
   - HTTP API has zero authentication — capability enforcement is CLI-side cosmetic only
   - Pairing tokens expire at creation, are never validated, never consumed
   - Any local process has full miner control via `curl`

4. **Nemesis Pass 2 (coupled-state):**
   - Spine/store dual-write is non-atomic — crash between writes violates "spine is source of truth"
   - Daemon in-memory state has no reconciliation with spine on restart
   - Gateway UI hardcodes `['observe', 'control']` — ignores actual device capabilities
   - No CORS headers — UI `fetch()` will fail from any non-same-origin context

5. **Contract/implementation drift is severe:** Encryption (not implemented), observability (not implemented), error taxonomy (not implemented), Hermes adapter (not implemented). Docs must distinguish contracts from reality.

6. **Path forward:** Re-run specify with a capable model, then write docs that are honest about milestone-1 limitations rather than echoing aspirational contracts.