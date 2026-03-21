# Hermes Adapter Verification

## Automated Proof Commands

1. `./scripts/bootstrap_hermes.sh`
   Outcome: exit `0`
   Result:
   - initialized `state/hermes-adapter-state.json`
   - proved disconnected adapters reject `read_status`
   - proved malformed authority tokens are rejected
   - proved observe-only tokens can read status and cannot append summaries
   - proved summarize-only tokens can append summaries and cannot read status
   - proved expired authority tokens are rejected

2. `./scripts/bootstrap_hermes.sh`
   Outcome: exit `0`
   Result:
   - confirmed bootstrap is idempotent when adapter state already exists
   - reran the in-script capability proof successfully

3. `cat state/hermes-adapter-state.json`
   Outcome: exit `0`
   Result:
   - confirmed persisted bootstrap state contains `observe` and `summarize`
   - confirmed bootstrap leaves the adapter disconnected after proof execution
   - confirmed `last_summary_ts` remains unset in the seeded repo-local state file
