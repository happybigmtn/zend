## Hermes Adapter Implementation Complete

### What was implemented:

**1. Hermes Adapter Module** (`services/home-miner-daemon/hermes.py`)
- `HermesConnection` dataclass for connection state
- `HermesPairing` dataclass for persistent pairing records  
- `AuthorityToken` dataclass for token validation
- `pair_hermes()` - idempotent pairing
- `connect()` - connect with authority token
- `reconnect_with_token()` - reconnect paired Hermes
- `read_status()` - read miner status (requires observe)
- `append_summary()` - append summary to spine (requires summarize)
- `get_filtered_events()` - filtered events (blocks user_message)
- Token validation with expiration and capability checking

**2. Daemon Hermes Endpoints** (`services/home-miner-daemon/daemon.py`)
- `POST /hermes/pair` - pair new Hermes
- `POST /hermes/connect` - connect with authority token
- `GET /hermes/status` - read miner status (Hermes auth)
- `POST /hermes/summary` - append summary (Hermes auth)
- `GET /hermes/events` - read filtered events (Hermes auth)
- Control endpoints now return 403 for Hermes auth

**3. Test Suite** (`services/home-miner-daemon/tests/test_hermes.py`)
- 14 tests covering all boundary conditions
- All tests pass

**4. Output Artifacts**
- `outputs/hermes-adapter-implementation/spec.md` - Implementation specification
- `outputs/hermes-adapter-implementation/review.md` - Implementation review

### Validation:
```
=== Pairing ===
{'paired': true, 'hermes_id': 'hermes-003', 'capabilities': ['observe', 'summarize']}

=== Control Blocked ===
HTTP 403: {'error': 'hermes_unauthorized', 'message': 'Hermes cannot issue control commands'}

=== All 14 tests passed ===
```