# Hermes Adapter — Verification

**Lane:** `hermes-adapter-implement`
**Status:** Verified
**Date:** 2026-03-20

## Proof Gate

The first proof gate `./scripts/bootstrap_hermes.sh` passed against a clean isolated state directory.

### Bootstrap Result

```
$ ./scripts/bootstrap_hermes.sh
[INFO] Bootstrapping Hermes Adapter...
[INFO] Adapter connected successfully
[INFO] Connection ID: a3af5842-6c0d-4dee-90e3-b9cf829b3ead
[INFO] Principal ID: hermes-demo-principal
[INFO] Verifying Hermes capabilities...
[INFO]   [OK] observe capability
[INFO]   [OK] summarize capability
[INFO]   [OK] status read via observe
[INFO]   [OK] summary appended: c36f015c-918c-4abf-8da6-b29a9a13e5d6
[INFO]   [OK] summarize denied without summarize capability
[INFO]   [OK] observe denied without observe capability
[INFO]   [OK] invalid authority token rejected

[INFO] Hermes Adapter bootstrap complete
[INFO] Capabilities verified: observe, summarize
[INFO] Bootstrap proof: PASS
```

## Additional Command Proof

The adapter was also exercised directly against the same isolated state directory:

| Command | Outcome |
|---------|---------|
| `python3 cli.py connect --token <observe,summarize token>` | PASS |
| `python3 cli.py scope` | PASS |
| `python3 cli.py status` | PASS |
| `python3 cli.py summary --text "verification summary"` | PASS |

Observed direct output:
- connection_id: `7173a6a4-7275-4d9a-978b-1e829c50931b`
- principal_id: `hermes-demo-principal`
- observe snapshot: `status=running`, `mode=balanced`, `hashrate_hs=50000.0`
- appended summary event: `ff668a54-8608-460f-8d1c-717739c55566`

## What Was Proven

1. The adapter accepts only valid delegated authority tokens and rejects malformed input.
2. Observe reads real event-spine evidence for the active principal by reconstructing state from accepted `control_receipt` events.
3. Summarize appends a valid `hermes_summary` event to the shared event spine.
4. Capability boundaries are enforced in both negative directions:
   `observe` alone cannot summarize, and `summarize` alone cannot observe.
5. The bootstrap proof is deterministic because it runs in `state/hermes-bootstrap` instead of reusing ambient repo state.

## Remaining Risk

- Observe is still a coarse control-receipt-derived snapshot, not live daemon telemetry.
- Authority tokens are still demo-issued for local proof instead of coming from the real pairing flow.
- Inbox projection and encrypted payload handling remain outside this slice.
