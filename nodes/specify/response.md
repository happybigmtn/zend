## Implementation Complete

Here's a summary of the Hermes adapter implementation:

### Files Created
| File | Description | Size |
|------|-------------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module | 16.4 KB |
| `services/home-miner-daemon/tests/test_hermes.py` | Test suite (16 tests) | 17.3 KB |
| `outputs/hermes-adapter-implementation/spec.md` | Specification | 7.4 KB |
| `outputs/hermes-adapter-implementation/review.md` | Review | 8.3 KB |

### Files Modified
| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints (`/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`) |
| `services/home-miner-daemon/cli.py` | Added Hermes subcommands (`pair`, `token`, `connect`, `status`, `summary`, `events`) |
| `apps/zend-home-gateway/index.html` | Updated Agent tab with real connection state, capabilities, summaries |
| `scripts/hermes_summary_smoke.sh` | Updated to use real adapter |

### Validation Results
```
✓ 16/16 unit tests passed
✓ Smoke test passed (all 7 steps)
✓ CLI commands verified working
✓ Event filtering confirmed (user_message blocked)
```

### What Hermes Can Do
- **Observe**: Read miner status (status, mode, hashrate, temperature, uptime)
- **Summarize**: Append summaries to event spine
- **Read filtered events**: hermes_summary, miner_alert, control_receipt (no user_message)

### What Hermes Cannot Do
- **Control**: Issue miner commands (start, stop, set_mode)
- **Read user messages**: Private communications blocked
- **Request invalid capabilities**: Tokens with `control` rejected at token level