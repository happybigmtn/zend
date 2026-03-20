# Hermes Adapter — Integration

## Current delegated flow

1. `scripts/bootstrap_hermes.sh` attempts a daemon health/start preflight, but keeps Hermes bootstrap store-backed if the sandbox denies socket binding.
2. The same bootstrap pairs `hermes-gateway` in `state/pairing-store.json` and writes a delegated token to `state/hermes-gateway.authority-token`.
3. `scripts/hermes_summary_smoke.sh` loads that token and calls `python3 -m hermes_adapter.adapter`.
4. `HermesAdapter.connect()` validates the token against the stored pairing record.
5. `append_summary()` appends a `hermes_summary` event into `state/event-spine.jsonl` under the connected principal.

## Source-of-truth surfaces

- Pairing store: delegated Hermes authority comes from the stored `hermes-gateway` pairing.
- Event spine: Hermes summaries land in the same principal-scoped spine as other operations receipts.
- Daemon HTTP API: unchanged observe path for `read_status()`, and still separate from the store-backed summary bootstrap path.

## Contract alignment

- Hermes enters through the Zend adapter, not by writing directly to the spine.
- Delegated scope is limited to the capabilities granted in the stored Hermes pairing.
- A token with an unknown `pairing_id` is rejected.
- A token scoped down to `observe` cannot append summaries.
- Hermes bootstrap remains honest in environments where the daemon cannot be rebound, because this slice only needs pairing and delegated token issuance.
