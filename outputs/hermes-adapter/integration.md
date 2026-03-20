# Hermes Adapter — Integration

## Current delegated flow

1. `scripts/bootstrap_hermes.sh` pairs `hermes-gateway` in `state/pairing-store.json`.
2. The same bootstrap writes a delegated token to `state/hermes-gateway.authority-token`.
3. `scripts/hermes_summary_smoke.sh` loads that token and calls `python3 -m hermes_adapter.adapter`.
4. `HermesAdapter.connect()` validates the token against the stored pairing record.
5. `append_summary()` appends a `hermes_summary` event into `state/event-spine.jsonl` under the connected principal.

## Source-of-truth surfaces

- Pairing store: delegated Hermes authority comes from the stored `hermes-gateway` pairing.
- Event spine: Hermes summaries land in the same principal-scoped spine as other operations receipts.
- Daemon HTTP API: unchanged observe path for `read_status()`.

## Contract alignment

- Hermes enters through the Zend adapter, not by writing directly to the spine.
- Delegated scope is limited to the capabilities granted in the stored Hermes pairing.
- A token with an unknown `pairing_id` is rejected.
- A token scoped down to `observe` cannot append summaries.
