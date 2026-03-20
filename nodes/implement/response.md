`★ Insight ─────────────────────────────────────`
The Hermes Adapter follows the **adapter pattern** — a thin shim that translates between Hermes Gateway's expectations and Zend's native gateway contract. This keeps Zend's core gateway logic decoupled from Hermes, allowing either to evolve independently. The `HermesCapability` type union (`'observe' | 'summarize'`) enforces capability-scoping at the type level, preventing runtime confusion about what Hermes is allowed to do.
`─────────────────────────────────────────────────`

## Implementation Complete

**Preflight gate:** `./scripts/bootstrap_hermes.sh` — PASSED

### Created Artifacts

| Artifact | Purpose |
|----------|---------|
| `outputs/hermes-adapter/agent-adapter.md` | Full TypeScript contract for HermesAdapter interface |
| `outputs/hermes-adapter/review.md` | Review validating contract against requirements |
| `outputs/hermes-adapter/implementation.md` | Curated implementation summary |
| `outputs/hermes-adapter/verification.md` | Curated verification evidence |
| `outputs/hermes-adapter/integration.md` | Curated integration points |
| `scripts/bootstrap_hermes.sh` | Preflight verification script |

### Slice Scope

This slice delivers the **contract-only** implementation for milestone 1.1:
- `HermesAdapter` interface with 4 methods: `connect`, `readStatus`, `appendSummary`, `getScope`
- `HermesCapability` type: `'observe' | 'summarize'`
- Authority token structure for pairing flow
- Event spine access rules (read: `hermes_summary`, `miner_alert`, `control_receipt`; write: `hermes_summary`)
- Milestone 1 boundaries enforced (no control commands, no payout mutation, no inbox composition)

### Not Included (Deferred to Future Slices)
- Live Hermes gateway connection implementation
- Authority token validation
- Control capability (milestone 1.2)
- Inbox message access (milestone 1.2)