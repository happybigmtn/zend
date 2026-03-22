## Summary

I've implemented the Hermes Adapter for Zend. Here's what was created:

### Created Files

1. **`services/home-miner-daemon/hermes.py`** - The adapter module with:
   - `HermesConnection` dataclass with authority token validation
   - `HermesPairing` for persistent pairing records
   - `pair_hermes()`, `connect()`, `read_status()`, `append_summary()`, `get_filtered_events()`
   - Capability enforcement (`HermesCapabilityError`, `HermesTokenError`)
   - Event filtering (blocks `user_message`, allows `hermes_summary`, `miner_alert`, `control_receipt`)

2. **`outputs/hermes-adapter-implementation/spec.md`** - Implementation specification

3. **`outputs/hermes-adapter-implementation/review.md`** - Review and approval document

### Modified Files

1. **`services/home-miner-daemon/daemon.py`** - Added Hermes endpoints:
   - `POST /hermes/pair` - Create Hermes pairing
   - `POST /hermes/connect` - Establish connection with token
   - `GET /hermes/status` - Read miner status (requires Hermes auth)
   - `POST /hermes/summary` - Append summary (requires Hermes auth)
   - `GET /hermes/events` - Read filtered events (requires Hermes auth)
   - Control endpoints (`/miner/*`) return 403 for Hermes auth

2. **`services/home-miner-daemon/cli.py`** - Added Hermes subcommands:
   - `hermes pair --hermes-id <id>`
   - `hermes connect --hermes-id <id>`
   - `hermes status --hermes-id <id>`
   - `hermes summary --hermes-id <id> --text <text>`
   - `hermes events --hermes-id <id>`

### Verification

- Module self-test passes: `Capabilities: ['observe', 'summarize']`, `Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']`, `Blocked events: ['user_message']`
- Pairing and connection work correctly
- Capability enforcement verified (control denied for Hermes)
- Event filtering correctly blocks `user_message`