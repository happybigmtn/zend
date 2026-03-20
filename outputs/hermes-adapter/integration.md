# Hermes Adapter — Integration

**Generated:** 2026-03-20
**Status:** Milestone 1 — Adapter Module Complete; Full Integration Deferred

## Integration Points

### What Exists

#### Token Storage (`state/hermes-tokens.json`)
- Tokens stored via `ZEND_STATE_DIR` env var (default: `state/hermes-tokens.json`)
- JSON store: token string → token data (principal_id, capabilities, issued_at, expires_at, token_id, used)
- Replay protection via `used` boolean flag

#### Sibling Module Imports (Test/Development Only)
The adapter imports from sibling `home-miner-daemon` module during test execution:
- `from errors import HermesError, HermesUnauthorizedError, HermesCapabilityError, HermesConnectionError`
- `from models import AuthorityToken, HermesCapability, HermesConnection, HermesSummary, MinerSnapshot, make_summary_text`
- `from auth_token import validate_token, mark_token_used`

These imports work because `sys.path` is modified to include the daemon directory during test setup. The daemon directory must contain `errors.py`, `models.py`, and `auth_token.py`.

#### HTTP API Intention (`readStatus`)
- `readStatus()` calls `http://{host}:{port}/status` expecting JSON response
- Default: `127.0.0.1:8080/status`
- Response schema: `{status, mode, hashrate_hs, temperature, uptime_seconds, freshness}`

#### Spine Integration Intention (`appendSummary`)
- `appendSummary()` calls `spine.append_hermes_summary()` from sibling module
- **Note:** `spine` module does not currently exist in `home-miner-daemon`
- This integration point is **not yet functional**

### What's Deferred

| Integration | Status | Blocker |
|-------------|--------|---------|
| Live daemon HTTP API | Not tested | Daemon not running during bootstrap |
| Real Hermes Gateway pairing | Not implemented | Token issued by gateway, not locally |
| Spine append | Not functional | `spine.append_hermes_summary()` missing |
| End-to-end smoke test | Not run | Requires live daemon + spine |

## Package Name Note

The package directory is `services/hermes-adapter/` (hyphenated). Python requires `importlib.util` workaround to import modules from hyphenated packages. The test file (`test_hermes_adapter.py`) demonstrates this by manually loading modules:

```python
import importlib.util
_adapter_spec = importlib.util.spec_from_file_location(
    "hermes_adapter.adapter",
    f"{_ADAPTER_DIR}/adapter.py"
)
```

## Bootstrap Integration

The `scripts/bootstrap_hermes.sh` script verifies the adapter module by:
1. Changing to `services/hermes-adapter` directory
2. Running `python3 tests/test_hermes_adapter.py -v`

This works because the test file pre-configures all import paths and constructs a virtual `hermes_adapter` namespace.

## Integration Status

**Adapter module is structurally complete and self-consistent.**
Full integration with live daemon and Hermes Gateway is a future slice.
