# Hermes Adapter — Integration

**Status:** Milestone 1 Slice
**Generated:** 2026-03-20

## Integration Points

### With home-miner-daemon

- **Daemon HTTP API** (`daemon.py`): `HermesAdapter.read_status()` calls `GET /status`
- **Event Spine** (`spine.py`): `HermesAdapter.append_summary()` calls `append_hermes_summary()`
- **Principal Store** (`store.py`): Authority tokens validated against stored pairing records

### With Zend Gateway (future)

Hermes connects to the Zend gateway via the adapter. In milestone 1:
- Hermes receives `observe` + `summarize` capabilities during pairing
- Hermes can read miner status and append summaries to the event spine
- Hermes cannot issue control commands (out of milestone 1 scope)

## Event Routing

| Event Kind | Source | Written by Hermes |
|------------|--------|-------------------|
| `hermes_summary` | Hermes adapter | Yes |
| `miner_alert` | Daemon | No |
| `control_receipt` | Gateway CLI | No |
| `pairing_granted` | Gateway | No |

## Next Integration Steps

- Connect Hermes Gateway to this adapter via authority token exchange
- Route Hermes summaries through the event spine to the inbox view
- Add encrypted memo transport for inbox delivery to Hermes
