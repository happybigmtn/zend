## Artifacts Produced

**`outputs/carried-forward-build-command-center/spec.md`** — 9,256 bytes
- Root cause analysis of 5 remaining work items
- Token replay prevention: defined in `error-taxonomy.md` but **not enforced** in `store.py` (`token_used=False` set at creation, never consumed)
- Capability enforcement: CLI scripts validate but **daemon does not** — any LAN client can bypass and control miner directly via HTTP
- Task specifications for 5 remaining items with acceptance criteria

**`outputs/carried-forward-build-command-center/review.md`** — 9,011 bytes
- Milestone 1 scaffolding, contracts, and gateway client rated **complete and sound**
- Three gap categories: CRITICAL (capability enforcement, token replay), HIGH (test coverage, Hermes adapter), MEDIUM (inbox UX)
- Risk assessment table with mitigation paths
- Verification commands to prove fixes work
- **Approval conditional** on security fixes landing before any product claim

`★ Insight ─────────────────────────────────────`
**Key architectural insight:** The daemon has a **defense-in-depth violation**. The CLI validates `control` capability before calling the daemon, but the daemon itself has zero auth — making the CLI's check purely cosmetic. A `curl` command can control the miner from any device on the LAN. Security boundaries must live at the service boundary, not the client wrapper.

**Second insight:** The token replay gap is a **contract/implementation mismatch**. `PairingTokenReplay` exists in the error taxonomy (engineers documented it), but the enforcement code was never written. This is a common pattern in early-stage systems — the spec anticipates failure modes the implementation hasn't caught up to yet.
`─────────────────────────────────────────────────`