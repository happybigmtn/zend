---

## Review Summary

**Verdict: NOT APPROVED.** The specify stage was a silent failure — MiniMax-M2.7 produced 0 tokens and committed zero file changes. No `hermes.py` adapter exists.

### What exists (from the prior home-command-center lane)

- `references/hermes-adapter.md` — good contract definition
- `spine.py` with `HERMES_SUMMARY` event kind and `append_hermes_summary()` helper
- `hermes_summary_smoke.sh` — proves spine storage but bypasses the adapter trust path
- Daemon, store, CLI — all building blocks ready

### Critical findings (Nemesis review)

**Pass 1 — Trust Boundaries:**
1. **Daemon has zero authentication.** Capability checks happen in `cli.py` (client-side), not `daemon.py` (server-side). Any local process can control the miner.
2. **Authority tokens are dead on arrival.** `store.py:89` sets `token_expires_at = datetime.now()` — every token is expired at creation.
3. **Hermes uses the owner's principal ID.** The smoke test writes Hermes summaries under the device owner's identity, making them indistinguishable in the audit trail.

**Pass 2 — Coupled State:**
1. **Pairing store + spine are not atomic.** A crash between store write and spine append leaves inconsistent state.
2. **No idempotence on spine writes.** Retried `appendSummary` calls produce duplicate events.
3. **`CAPABILITY_REVOKED` events exist but nothing reads them.** Revocation is decorative.

### Blockers before the adapter can land

| Must-fix | Location |
|----------|----------|
| Token expiration bug | `store.py:89` |
| Output path mismatch (3 different conventions) | workflow, prompt, agent def |
| No daemon-level auth for Hermes routes | `daemon.py` |
| Owner principal used for Hermes identity | smoke test, spine writes |

### Artifacts produced

- `outputs/hermes-adapter-implementation/review.md` — full review with Nemesis passes
- `outputs/hermes-adapter-implementation/spec.md` — implementation spec (written during review since specify stage failed, to unblock the next run)

### Recommendation

Re-run the specify stage with a capable model, using the spec artifact as a starting point. Fix the four must-fix blockers, then implement the adapter module per the spec's interface and test requirements.