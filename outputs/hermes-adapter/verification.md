# Hermes Adapter Verification

## Automated Proof Commands

1. `./scripts/bootstrap_hermes.sh`
   Outcome: exit `0`
   Result:
   - confirmed repo-local Hermes adapter bootstrap remains idempotent
   - proved disconnected adapters reject `read_status()`
   - proved malformed authority tokens are rejected
   - proved observe-only tokens can read status and cannot append summaries
   - proved delegated observe-plus-summarize connections append a real `hermes_summary` event into the event spine
   - proved summary principal mismatch is rejected before any spine append
   - proved expired tokens are rejected both at connect time and after a connected session ages out

2. `./scripts/hermes_summary_smoke.sh --client alice-phone`
   Outcome: exit `0`
   Result:
   - loaded the repo-local principal and connected through `HermesAdapter`
   - appended one delegated Hermes summary through the adapter into `state/event-spine.jsonl`
   - printed the appended `event_id` and `principal_id`
   - confirmed the adapter state file was left disconnected and its `last_summary_ts` matched the appended spine event `created_at`

3. `cat state/hermes-adapter-state.json`
   Outcome: exit `0`
   Result:
   - confirmed repo-local adapter state is disconnected after the smoke proof
   - confirmed `last_summary_ts` is set from the latest appended spine event timestamp
   - confirmed the connection-only fields are cleared after disconnect

4. `tail -n 3 state/event-spine.jsonl`
   Outcome: exit `0`
   Result:
   - confirmed the newest repo-local event is kind `hermes_summary`
   - confirmed the payload includes the smoke summary text for `alice-phone`
   - confirmed the payload `authority_scope` recorded by the adapter is `["observe", "summarize"]`

## Proof Notes

- The smoke script now proves the Hermes summary path goes through the adapter instead of calling the spine module directly.
- The repo still treats the event spine as the source of truth for any inbox projection, so this slice stops at verified spine append behavior.
