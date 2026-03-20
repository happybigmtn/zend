# Hermes Adapter — Implementation

**Status:** Milestone 1 Slice Complete
**Generated:** 2026-03-20

## What Was Built

### HermesAdapter Python Package

`services/hermes_adapter/` (Python requires underscores, not hyphens):

| File | Purpose |
|------|---------|
| `__init__.py` | Public exports: `HermesAdapter`, `HermesConnection`, `MinerSnapshot`, `HermesSummary`, `HermesCapability`, `CapabilityError` |
| `adapter.py` | Full `HermesAdapter` implementation with CLI entry point |

### HermesAdapter Interface

```python
class HermesAdapter:
    def connect(authority_token: str) -> HermesConnection
    def get_scope() -> list[HermesCapability]
    def read_status() -> MinerSnapshot      # requires 'observe'
    def append_summary(summary: HermesSummary) -> str  # requires 'summarize'
```

### Capability Boundaries (Milestone 1)

| Capability | Operations | Status |
|-------------|------------|--------|
| `observe` | `read_status()` | Implemented |
| `summarize` | `append_summary()` | Implemented |
| `control` | — | Out of scope |

### Bootstrap Script

`scripts/bootstrap_hermes.sh`:
- Starts the home-miner daemon if not running
- Creates a `hermes-gateway` principal with `observe` + `summarize` capabilities
- Appends a `hermes_summary` event and a `pairing_granted` event to the event spine

### CLI Commands

```bash
# Read miner status (requires observe token)
cd services/home-miner-daemon
python3 -c "from hermes_adapter.adapter import HermesAdapter; ..."

# Append a Hermes summary (requires summarize token)
cd services/home-miner-daemon
python3 -c "from hermes_adapter.adapter import HermesAdapter, HermesSummary; ..."
```

## Architecture Notes

- The adapter is a thin wrapper around the existing `home-miner-daemon` HTTP API and event spine.
- Authority tokens are base64-encoded JSON with `principal_id`, `capabilities`, and `expires_at`.
- `CapabilityError` is raised when an operation lacks the required capability — this enforces milestone 1 boundaries.
- No `control` operations are exposed; Hermes cannot start/stop/set_mode through the adapter.

## Files Changed/Created

| Path | Change |
|------|--------|
| `services/hermes_adapter/__init__.py` | Created |
| `services/hermes_adapter/adapter.py` | Created |
| `scripts/bootstrap_hermes.sh` | Created |
| `outputs/hermes-adapter/implementation.md` | Created |
| `outputs/hermes-adapter/verification.md` | Created |
| `outputs/hermes-adapter/quality.md` | Created |
| `outputs/hermes-adapter/integration.md` | Created |
| `outputs/hermes-adapter/promotion.md` | Created |

## Dependencies

- `services/home-miner-daemon/spine.py` — event spine append/query
- `services/home-miner-daemon/store.py` — principal and pairing management
- `services/home-miner-daemon/daemon.py` — HTTP API (status endpoint)

## Out of Scope (Deferred)

- Hermes `control` capability (requires new approval flow)
- Inbox message access for Hermes
- Direct miner command relay
- Event encryption (spine appends plaintext JSON in milestone 1)
