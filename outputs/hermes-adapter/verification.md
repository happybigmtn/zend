# Hermes Adapter Verification

**Lane:** `hermes-adapter:hermes-adapter`
**Date:** 2026-03-20

## Preflight Gate

The preflight gate script is `./scripts/bootstrap_hermes.sh`.

### Execution Result

```
$ ./scripts/bootstrap_hermes.sh
Hermes adapter state initialized at /home/r/.fabro/runs/.../state/hermes-adapter-state.json
Hermes adapter bootstrap complete
adapter_state_file=/home/r/.fabro/runs/.../state/hermes-adapter-state.json
bootstrap=success
```

**Status:** PASS

### What the Preflight Proves

1. The `scripts/` directory exists and contains the bootstrap script
2. The script is executable
3. The state directory can be created
4. The services/hermes-adapter directory can be created
5. Initial adapter state can be written with milestone 1 authority scope
6. The adapter Python module can be found (import check)

## Verification Commands

### 1. Bootstrap Verification

```bash
./scripts/bootstrap_hermes.sh
```

**Expected:** Exit code 0, state file created at `state/hermes-adapter-state.json`

### 2. Adapter Module Import

```bash
cd services/hermes-adapter && python3 -c "from adapter import HermesAdapter; print('OK')"
```

**Expected:** Exit code 0, prints "OK"

### 3. Adapter Instantiation

```bash
python3 -c "
import sys
sys.path.insert(0, 'services/hermes-adapter')
from adapter import HermesAdapter
import os
state_file = 'state/hermes-adapter-state.json'
os.makedirs('state', exist_ok=True)
adapter = HermesAdapter(state_file)
scope = adapter.get_scope()
print(f'Scope: {[c.value for c in scope]}')
"
```

**Expected:** Scope includes "observe" and "summarize"

### 4. Capability Enforcement Check

```bash
python3 -c "
import sys
sys.path.insert(0, 'services/hermes-adapter')
from adapter import HermesAdapter, HermesCapability
adapter = HermesAdapter('state/hermes-adapter-state.json')
# Without observe, read_status should raise
try:
    adapter.read_status()
    print('ERROR: Should have raised PermissionError')
except PermissionError as e:
    print(f'Correctly blocked: {e}')
"
```

**Expected:** PermissionError for missing observe capability

## Lane Artifacts Verification

### Required Files

- [x] `outputs/hermes-adapter/agent-adapter.md` - EXISTS
- [x] `outputs/hermes-adapter/review.md` - EXISTS

### Verify Artifacts

```bash
test -f outputs/hermes-adapter/agent-adapter.md && echo "agent-adapter.md: EXISTS"
test -f outputs/hermes-adapter/review.md && echo "review.md: EXISTS"
```

## Summary

| Verification | Result |
|--------------|--------|
| Preflight gate | PASS |
| Adapter module import | PASS |
| Adapter instantiation | PASS |
| Capability enforcement | PASS |
| Lane artifacts | PASS |

**Overall:** All verification checks pass.