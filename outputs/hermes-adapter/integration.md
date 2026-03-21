# Hermes Adapter Integration

## Merge Surface

- Adds the Hermes-owned service surface at `services/hermes-adapter/`.
- Adds the Hermes preflight and verification entrypoint at `scripts/bootstrap_hermes.sh`.
- Restores the reviewed Hermes lane artifacts under `outputs/hermes-adapter/` so the implementation stage has local source material.

## Dependency Notes

- Uses Python standard library only.
- Persists repo-local state under `state/hermes-adapter-state.json`.
- Does not modify the existing home-miner daemon, gateway UI, or shell control flows.
- Introduces no schema migration and no external service dependency.

## Rerun

- `./scripts/bootstrap_hermes.sh`
