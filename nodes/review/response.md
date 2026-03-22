`★ Insight ─────────────────────────────────────`
**Decoupled state stores are a common adapter anti-pattern.** The Hermes pairing store (disk-backed JSON) and connection store (in-memory dict) never cross-reference each other. This means revoking a pairing has no effect on active connections, and connecting doesn't require a pairing. In capability-scoped adapters, the connection ceremony should always verify against the durable authority record (pairing) — otherwise the ceremony is cosmetic.

**The "defense in depth" pattern in the control endpoints is well-placed.** Even though Hermes connections lack `control` capability, the daemon also checks for the `Hermes` auth header on `/miner/start|stop|set_mode` and rejects with 403. This means a future bug that accidentally grants `control` to a Hermes token still can't reach the miner — two independent checks must both fail.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONAL PASS**

### Inline fixes applied:
- **CLI dispatch** — `main()` never routed `hermes` subcommands; all 5 handlers were dead code
- **Argparse conflict** — `--token` was `required=True` alongside `--generate-token`

### Security findings (3 passes):

| Severity | Finding | Acceptable for M1? |
|----------|---------|---------------------|
| CRITICAL | JWT signature never verified — tokens are forgeable | Yes (localhost-only, plan 006 dependency) |
| HIGH | `connect()` doesn't verify pairing record exists | **Must fix before lane closes** |
| HIGH | `/hermes/pair` is unauthenticated | Yes (matches device pairing pattern) |
| MEDIUM | `authority_scope` param accepts any string including `"control"` | **Must fix before lane closes** |
| MEDIUM | Pairing store (disk) and connection store (memory) are decoupled — revocation has no effect | Should fix |
| LOW | No input bounds on `summary_text` (empty and 100KB+ accepted) | Should fix |

### What works well:
- Capability enforcement on all three read/write paths
- Event filtering correctly excludes `user_message`
- Control endpoint defense-in-depth (Hermes header check independent of capability check)
- Idempotent pairing
- Clean separation between adapter logic and HTTP handler

### Must-fix to close lane (items 1-2):
1. `connect()` must call `get_hermes_pairing(hermes_id)` and reject if no pairing exists
2. `append_summary()` must validate `authority_scope` against `HERMES_CAPABILITIES`

### Pre-existing (not this lane):
- `MinerStatus.STOPPED` serializes as `"MinerStatus.STOPPED"` on Python 3.15 (enum `str()` behavior change)

Full review at `outputs/hermes-adapter-implementation/review.md`.