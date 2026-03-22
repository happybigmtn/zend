## Summary

I've successfully implemented the Hermes adapter for the Zend home-miner daemon. Here's what was delivered:

### Created Files

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | Hermes adapter module with capability enforcement |
| `outputs/hermes-adapter-implementation/spec.md` | Specification document |
| `outputs/hermes-adapter-implementation/review.md` | Review document |

### Modified Files

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Added Hermes subcommands |

### Implemented Features

1. **Hermes Adapter Module** (`hermes.py`):
   - `HermesConnection` with authority token validation
   - `pair_hermes()` - Create Hermes pairings (observe + summarize only)
   - `connect()` - Validate JWT authority tokens
   - `read_status()` - Read miner status (requires observe)
   - `append_summary()` - Append to event spine (requires summarize)
   - `get_filtered_events()` - Event filtering (blocks user_message)
   - Security enforcement (control capability blocked)

2. **Hermes Endpoints** (added to `daemon.py`):
   - `POST /hermes/pair` - Create Hermes pairing
   - `POST /hermes/connect` - Connect with authority token
   - `GET /hermes/status` - Read miner status
   - `POST /hermes/summary` - Append summary
   - `GET /hermes/events` - Read filtered events
   - `GET /hermes/capabilities` - Show Hermes capability set

3. **Control Blocking**: Control endpoints (`/miner/start`, etc.) return 403 when called with Hermes auth header

4. **CLI Commands**:
   - `hermes pair` - Pair a Hermes agent
   - `hermes status` - Read status as Hermes
   - `hermes summary` - Append summary
   - `hermes events` - Read filtered events
   - `hermes capabilities` - Show capability set

### Verification Results

```
✓ Capabilities: ['observe', 'summarize']
✓ Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
✓ Hermes can pair and receive authority token
✓ Hermes can read miner status
✓ Hermes can append summaries
✓ Hermes CANNOT issue control commands (403 returned)
✓ Hermes CANNOT read user_message events (filtered)
✓ Event filtering blocks user_message
```