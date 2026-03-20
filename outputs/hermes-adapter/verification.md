# Hermes Adapter — Verification

**Status:** Milestone 1.1 Complete
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Automated Proof Commands

### Bootstrap Gate

```bash
./scripts/bootstrap_hermes.sh
```

**Outcome:** Daemon starts and Hermes token created successfully

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrapping Hermes authority token...
token=<uuid>
principal_id=test-hermes-principal
capabilities=observe,summarize
[INFO] Hermes token bootstrap complete
```

### Unit Tests

```bash
cd services/home-miner-daemon
python3 test_adapter.py -v
```

**Outcome:** 14 tests pass

```
test_append_summary_requires_summarize ... ok
test_append_summary_success ... ok
test_connect_with_expired_token ... ok
test_connect_with_invalid_token ... ok
test_connect_with_valid_token ... ok
test_create_token ... ok
test_disconnect ... ok
test_disconnect_nonexistent ... ok
test_get_connection_not_found ... ok
test_get_scope ... ok
test_read_status_requires_observe ... ok
test_capability_from_string ... ok
test_capability_values ... ok
test_token_persistence ... ok

Ran 14 tests in 0.003s
OK
```

### Syntax Validation

```bash
python3 -m py_compile services/home-miner-daemon/adapter.py
python3 -m py_compile services/home-miner-daemon/daemon.py
python3 -m py_compile services/home-miner-daemon/store.py
python3 -m py_compile services/home-miner-daemon/spine.py
python3 -m py_compile services/home-miner-daemon/__init__.py
```

**Outcome:** All files compile without errors

### Module Import

```bash
cd /home/r/.fabro/runs/20260320-01KM6HCVAYPQDS23BF72PJPKRY/worktree
python3 -c "from services.home-miner-daemon.daemon import hermes_adapter; print(type(hermes_adapter))"
```

**Outcome:** `<class 'adapter.HermesAdapter'>`

### Integration Script

```bash
./scripts/hermes_summary_smoke.sh --client alice-phone
```

**Outcome:**
```
event_id=876d0ec1-1205-4448-91fd-be2b16f20223
principal_id=d3226029-f88d-41d7-8cb6-fa4548fa94f2
summary_appended_to_operations_inbox=true
```

## Manual Verification Steps

### 1. Start Daemon

```bash
cd services/home-miner-daemon
python3 daemon.py &
```

### 2. Create Hermes Token (for testing)

```python
import sys
sys.path.insert(0, '.')
from adapter import create_hermes_token, HermesAdapter

token, _ = create_hermes_token(
    principal_id="test-principal",
    capabilities=["observe", "summarize"]
)
print(f"Token: {token}")
```

### 3. Connect via Hermes Adapter

```bash
curl -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d "{\"authority_token\": \"$TOKEN\"}"
```

Expected response:
```json
{
    "connection_id": "...",
    "principal_id": "test-principal",
    "capabilities": ["observe", "summarize"],
    "expires_at": "..."
}
```

### 4. Read Status with Connection

```bash
curl http://127.0.0.1:8080/hermes/status \
  -H "X-Connection-ID: $CONNECTION_ID"
```

Expected response:
```json
{
    "status": "stopped",
    "mode": "paused",
    "hashrate_hs": 0,
    "temperature": 45.0,
    "uptime_seconds": 0,
    "freshness": "2026-03-20T..."
}
```

### 5. Append Summary

```bash
curl -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Content-Type: application/json" \
  -d "{\"connection_id\": \"$CONNECTION_ID\", \"summary_text\": \"Test summary\"}"
```

Expected response:
```json
{
    "event_id": "...",
    "created_at": "2026-03-20T..."
}
```

### 6. Verify Unauthorized Access

```bash
# Try to read status without connection ID
curl http://127.0.0.1:8080/hermes/status

# Expected: {"error": "missing_connection_id"}

# Try with invalid connection ID
curl http://127.0.0.1:8080/hermes/status \
  -H "X-Connection-ID: invalid-id"

# Expected: {"error": "connection_not_found"}
```

## Test Coverage

| Capability | Test |
|------------|------|
| Token creation | `test_create_token` |
| Valid token connect | `test_connect_with_valid_token` |
| Invalid token | `test_connect_with_invalid_token` |
| Expired token | `test_connect_with_expired_token` |
| Scope retrieval | `test_get_scope` |
| Observe required | `test_read_status_requires_observe` |
| Summarize required | `test_append_summary_requires_summarize` |
| Summary append | `test_append_summary_success` |
| Disconnect | `test_disconnect`, `test_disconnect_nonexistent` |
| Connection lookup | `test_get_connection_not_found` |
| Token persistence | `test_token_persistence` |
| Capability enum | `test_capability_values`, `test_capability_from_string` |
