# Hermes Adapter — Implementation

## Slice

Implemented the smallest next Hermes slice needed to keep the approved delegated-authority proof honest in a fresh sandbox.

## What changed

- `scripts/bootstrap_hermes.sh`
  - Keeps daemon startup as a best-effort preflight instead of a hard requirement for this slice.
  - Treats a stale PID file as unhealthy unless the health endpoint responds.
  - Captures daemon startup output in `state/hermes-daemon.log` so degraded bootstrap is explicit.
  - Continues store-backed Hermes pairing and delegated token issuance when local socket binding is denied.
  - Emits `daemon_status` in the bootstrap payload when the delegated bootstrap succeeds without a live daemon.

## Slice state retained

- The delegated token contract in `services/hermes_adapter/adapter.py` is unchanged.
- `scripts/hermes_summary_smoke.sh` still proves that delegated summary append flows through the Hermes adapter and lands in the shared event spine.

## Touched surfaces

- `scripts/bootstrap_hermes.sh`

## Boundary kept for this slice

- Hermes still has no control capability.
- `read_status()` still depends on the daemon HTTP endpoint; this slice only made the delegated bootstrap path resilient when the daemon cannot be rebound inside the sandbox.
