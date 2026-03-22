## Summary

Successfully bootstrapped the first honest reviewed slice for the Hermes Adapter frontier.

### Created/Modified Files

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | New adapter module with `HermesConnection`, `connect()`, `read_status()`, `append_summary()`, `get_filtered_events()` |
| `services/home-miner-daemon/daemon.py` | Updated with Hermes endpoints: `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events` |
| `services/home-miner-daemon/cli.py` | Updated with Hermes subcommands: `hermes pair`, `hermes connect`, `hermes status`, `hermes summary`, `hermes events` |
| `outputs/hermes-adapter-implementation/spec.md` | Specification document for the adapter contract |
| `outputs/hermes-adapter-implementation/review.md` | Review document with correctness assessment |

### Verified Behavior

| Test | Result |
|------|--------|
| Hermes can connect with authority token | ✅ |
| Hermes can read miner status via `/hermes/status` | ✅ |
| Hermes can append summaries via `/hermes/summary` | ✅ |
| Hermes CANNOT issue control commands | ✅ (403 `HERMES_UNAUTHORIZED`) |
| Hermes CANNOT read `user_message` events | ✅ (filtered) |
| CLI commands work end-to-end | ✅ |

### Key Design Decisions

1. **Token format**: `hermes_id|capabilities|expires_iso` using pipe separator to avoid ISO datetime colon conflicts
2. **Capability independence**: Hermes `observe`/`summarize` are separate from gateway `observe`/`control`
3. **Auth scheme**: `Authorization: Hermes <id>` header distinguishes Hermes traffic
4. **In-process adapter**: Avoids network hop complexity for the capability boundary