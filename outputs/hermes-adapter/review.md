# Hermes Adapter — Review

**Status:** Approved
**Date:** 2026-03-20

## Summary

The approved Hermes slice is intentionally narrow: prove the Zend-owned adapter boundary, delegated-authority connection, observe reads, and summary append behavior without widening Hermes privileges.

## Approved For Implementation

- Contract-shaped delegated-authority validation in `HermesAdapter.connect()`
- Observe-only miner status reads through the adapter
- Summary append through the event spine via `appendSummary()`
- Proof via `./scripts/bootstrap_hermes.sh`, including one rejected authority-token case

## Constraints

- Do not add Hermes miner control
- Do not add payout-target mutation
- Do not add inbox composition
- Keep the event spine as the source of truth and treat the inbox as a projection

## Follow-On Work

The next larger increments remain separate from this slice:
- inbox projections and richer inbox surfaces
- broader trust-ceremony and event-routing test coverage
- any new Hermes capability beyond `observe` and `summarize`

## Verdict

**APPROVED** — implement only the adapter/bootstrap slice above and keep the proof narrative tied to the owned Hermes surfaces.
