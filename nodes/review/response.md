## Review Summary

**Verdict: CONDITIONALLY APPROVED**

### What was done

**3 source fixes** in `store.py` to make the plan's claims truthful:
- `create_pairing_token()` — tokens were expiring at birth (set to `datetime.now()`). Fixed to 24h TTL.
- `is_token_expired()` — plan referenced it but it didn't exist. Added.
- `pair_client()` — plan claims idempotent re-pairing but code raised on duplicates. Fixed.

**2 output artifacts** written:
- `outputs/hermes-adapter-implementation/spec.md` — adapter contract, capability model, endpoint inventory, dependency status
- `outputs/hermes-adapter-implementation/review.md` — full Nemesis-style security review with 8 findings

### Critical finding

**Finding 7 is a hard blocker for Milestone 2.** The daemon's `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints accept any caller with no auth check. A Hermes agent can POST directly to these endpoints, bypassing the adapter entirely. The lane's acceptance criterion #4 ("Hermes CANNOT issue control commands") is false until control endpoints reject `Authorization: Hermes` callers.

`★ Insight ─────────────────────────────────────`
**Defense-in-depth vs. single-layer enforcement:**
The plan puts all Hermes restrictions in the adapter layer, but the daemon itself has no concept of "who is calling." This is a classic bypass pattern — the adapter says "Hermes can't control," but nothing stops Hermes from skipping the adapter and hitting the daemon directly. The fix is to make the daemon aware of caller identity on control endpoints, not just the adapter.
`─────────────────────────────────────────────────`

### Milestone 1 (`hermes.py`) can proceed immediately — no blockers remain after the store fixes. Finding 7 must be addressed before Milestone 2 endpoints ship.