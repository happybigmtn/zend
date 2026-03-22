## Implementation Complete

I've successfully implemented the Hermes adapter for the Zend home miner daemon. Here's a summary:

### Created Artifacts

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Core adapter module with HermesConnection, capability enforcement, event filtering |
| `services/home-miner-daemon/tests/test_hermes.py` | 19 unit tests covering all boundary cases |
| `outputs/hermes-adapter-implementation/spec.md` | Implementation specification |
| `outputs/hermes-adapter-implementation/review.md` | Honest review document |

### Modified Files

| File | Changes |
|------|---------|
| `daemon.py` | Added `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events` endpoints |
| `cli.py` | Added `hermes pair`, `hermes status`, `hermes summary`, `hermes events`, `hermes list` commands |

### Key Features

1. **Capability scope enforcement**: Hermes has `observe` and `summarize` only — no `control`
2. **Token validation**: Authority tokens validated for expiration, capabilities, and required fields
3. **Event filtering**: `user_message` events are blocked from Hermes reads
4. **Idempotent pairing**: Re-pairing same `hermes_id` updates timestamp

### Test Results

```
19 tests passed in 0.05s
```

### Verification Commands

```bash
# Run tests
python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v

# CLI workflow
python3 cli.py hermes pair --hermes-id test --name "Test Agent"
python3 cli.py hermes status --hermes-id test
python3 cli.py hermes summary --hermes-id test --text "Summary text"
python3 cli.py hermes events --hermes-id test
```