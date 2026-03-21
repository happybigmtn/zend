# Hermes Adapter Integration

## Merge Surface

- Keeps Hermes-owned logic in `services/hermes-adapter/adapter.py`.
- Updates the Hermes lane proof entrypoint in `scripts/bootstrap_hermes.sh`.
- Updates the Hermes integration smoke path in `scripts/hermes_summary_smoke.sh` so it exercises the adapter instead of bypassing it.

## Dependency Notes

- Uses Python standard library only.
- Reuses the existing event spine append surface from `services/home-miner-daemon/spine.py` without modifying daemon code.
- Depends on `ZEND_STATE_DIR` for both adapter state and event spine persistence; the Hermes scripts export that state root before importing the shared daemon modules.
- Writes repo-local proof state to:
  - `state/hermes-adapter-state.json`
  - `state/event-spine.jsonl`

## Operational Notes

- The adapter now treats delegated session expiration as an active gate, not just a connect-time validation.
- The adapter records the connected principal in state only while the delegated session is active and clears it on disconnect.
- The shared event-spine contract text still needs a follow-up wording pass to align its Hermes scope language with the reviewed Hermes adapter lane.

## Rerun

- `./scripts/bootstrap_hermes.sh`
- `./scripts/hermes_summary_smoke.sh --client alice-phone`
