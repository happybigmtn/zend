The plan file doesn't exist in this repository, but that's fine. The implementation is complete.

## Summary

Successfully completed the first honest reviewed slice for the Hermes Adapter Implementation lane.

### Deliverables

| Artifact | Status |
|----------|--------|
| `services/home-miner-daemon/hermes.py` | ✅ Created - 10KB adapter module |
| `services/home-miner-daemon/daemon.py` | ✅ Updated - Hermes endpoints added |
| `services/home-miner-daemon/cli.py` | ✅ Updated - Hermes subcommands added |
| `services/home-miner-daemon/tests/test_hermes.py` | ✅ Created - 21 tests |
| `outputs/hermes-adapter-implementation/spec.md` | ✅ Created - Specification document |
| `outputs/hermes-adapter-implementation/review.md` | ✅ Created - Review document |

### Implementation Highlights

1. **HermesConnection** with authority token validation
   - Token parsing with base64 encoding
   - Expiration checking
   - Capability validation
   - Registration verification

2. **Capability Enforcement**
   - `observe` - Read miner status and filtered events
   - `summarize` - Append summaries to event spine
   - `control` explicitly blocked

3. **Event Filtering**
   - Blocks `user_message` events
   - Allows: `hermes_summary`, `miner_alert`, `control_receipt`

4. **Daemon Endpoints**
   - `POST /hermes/pair` - Pair Hermes agent
   - `POST /hermes/connect` - Validate authority token
   - `GET /hermes/status` - Read miner status
   - `POST /hermes/summary` - Append summary
   - `GET /hermes/events` - Get filtered events

5. **CLI Subcommands**
   - `python3 cli.py hermes pair --hermes-id <id>`
   - `python3 cli.py hermes status --authority-token <token>`
   - `python3 cli.py hermes summary --authority-token <token> --text <text>`
   - `python3 cli.py hermes events --authority-token <token>`

### Test Results

```
21 tests passed in 0.13s
```

All acceptance criteria met:
- ✅ Hermes can connect with authority token
- ✅ Hermes can read miner status
- ✅ Hermes can append summaries to event spine
- ✅ Hermes CANNOT issue control commands (403)
- ✅ Hermes CANNOT read user_message events (filtered)
- ✅ All tests pass
- ✅ Pairing is idempotent