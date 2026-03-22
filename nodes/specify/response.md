## Summary

Implemented the Hermes Adapter for the Zend Home Miner project. Here's what was delivered:

### Created Files

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | Core adapter module with capability enforcement |
| `services/home-miner-daemon/tests/test_hermes.py` | 16 unit tests covering all adapter functions |
| `outputs/hermes-adapter-implementation/spec.md` | Specification document |
| `outputs/hermes-adapter-implementation/review.md` | Implementation review |

### Modified Files

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints (pair, connect, status, summary, events) |
| `services/home-miner-daemon/cli.py` | Added Hermes subcommands |
| `apps/zend-home-gateway/index.html` | Updated Agent tab with real connection state |

### Key Features Implemented

1. **HermesConnection** with authority token validation
2. **readStatus** through adapter (requires observe capability)
3. **appendSummary** through adapter (requires summarize capability)
4. **Event filtering** — blocks `user_message` events from Hermes reads
5. **Hermes pairing endpoint** — creates observe+summarize pairings
6. **Control rejection** — Hermes auth returns 403 on `/miner/*` endpoints
7. **Gateway Agent tab** — shows real connection state and summaries

### Test Results

```
16 tests passed — all adapter boundaries enforced correctly
```

### Proof of Capability Boundaries

```bash
# Control rejected
curl -X POST /miner/start -H "Authorization: Hermes hermes-001"
→ {"error": "HERMES_UNAUTHORIZED", "message": "Hermes agents cannot issue control commands"}

# user_message filtered
GET /hermes/events returns hermes_summary, miner_alert, control_receipt
→ No user_message events
```