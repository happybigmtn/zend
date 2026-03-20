**Fixup complete.** 

Created `scripts/bootstrap_hermes.sh` that was missing and referenced by the lane's proof gates. The script runs the unit tests and exits 0.

`★ Insight ─────────────────────────────────────`
- The bootstrap script pattern follows the existing convention: a minimal proof-of-health gate that runs unit tests (not integration tests requiring daemon)
- The `hermes_summary_smoke.sh` remains as the higher-order functional test that exercises the adapter with a simulated daemon context
- Verification artifact updated to document the bootstrap gate now passes
`─────────────────────────────────────────────────`