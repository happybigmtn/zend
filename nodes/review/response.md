`★ Insight ─────────────────────────────────────`
**Documentation honesty is a security property.** When docs claim tests exist that don't, or show code that was never written, contributors build false confidence. The token replay snippet in architecture.md was particularly dangerous — a future developer could read it and assume replay attacks are handled, then skip implementing the check because "it's already there." Nemesis reviews exist to catch exactly these drift-from-reality problems before they compound.

**Coupled-state ordering matters even in simple systems.** The store-before-spine write order in `cmd_pair()` means a crash can leave a functioning pairing with no audit trail. In milestone 1 this is low-risk, but the pattern is worth noting because event sourcing systems often treat the event as the authority — here the store is the authority and the spine is secondary, which is a design choice that should be explicit.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONAL PASS** — 3 falsehoods found and fixed, 1 code bug fixed.

### Fixes Applied

| File | What Changed |
|------|-------------|
| `spine.py:87` | Fixed `kind.value` crash when CLI passes a plain string to `get_events()` — the documented `--kind` filter was non-functional |
| `docs/architecture.md` | Removed fabricated token replay prevention code snippet; replaced with honest description of current state |
| `docs/contributor-guide.md` | Removed fabricated test suite coverage claims; replaced with "no tests yet" |
| `README.md` | Added note that test suite doesn't exist yet |

### Key Findings

1. **No test suite exists** — the highest-severity gap. Docs now honestly state this, but the contributor workflow has no automated safety net.
2. **HTTP endpoints are completely unauthenticated** — correctly documented as a milestone 1 decision, but any LAN peer can control the miner by curling directly.
3. **Token replay prevention field (`token_used`) stored but never enforced** — duplicate device name rejection provides basic protection.
4. **Bootstrap skips `pairing_requested` event** — creates a spine audit gap where pairings appear as granted without being requested.
5. **Store-before-spine write order** — a crash between `pair_client()` and `spine.append_*()` leaves a working pairing with no audit trail.

### Remaining Blockers

- **High:** No test suite (code lane, not docs lane)
- **Medium:** "Verify docs on a clean machine" plan task not completed
- **Low:** CORS limitation undocumented for LAN HTML client access
- **Low:** Plan lists 3 endpoints that don't exist in code (plan maintenance)