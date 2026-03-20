# Hermes Adapter — Verification

**Generated:** 2026-03-20

## Automated Proof Commands

### Bootstrap Gate

```bash
./scripts/bootstrap_hermes.sh
```

Actual output:
```
test_appendSummary_records_event_in_spine (__main__.TestAdapterAppendSummary.test_appendSummary_records_event_in_spine)
appendSummary() appends a Hermes summary event to the spine. ... ok
test_appendSummary_without_summarize_raises (__main__.TestAdapterAppendSummary.test_appendSummary_without_summarize_raises)
appendSummary() raises HermesCapabilityError without summarize. ... ok
test_connect_twice_with_same_token_fails (__main__.TestAdapterConnect.test_connect_twice_with_same_token_fails)
Token can only be used once (replay protection). ... ok
test_connect_with_valid_token (__main__.TestAdapterConnect.test_connect_with_valid_token)
connect() succeeds with valid token. ... ok
test_getScope_returns_capabilities (__main__.TestAdapterGetScope.test_getScope_returns_capabilities)
getScope() returns the granted capabilities. ... ok
test_getScope_without_connect_raises (__main__.TestAdapterGetScope.test_getScope_without_connect_raises)
getScope() without connect() raises HermesConnectionError. ... ok
test_readStatus_without_observe_raises (__main__.TestAdapterReadStatus.test_readStatus_without_observe_raises)
readStatus() raises HermesCapabilityError without observe. ... ok
test_adapter_does_not_expose_control_methods (__main__.TestBoundaryEnforcement.test_adapter_does_not_expose_control_methods)
Adapter interface does not include start/stop/mode change. ... ok
test_no_control_capability_exists (__main__.TestBoundaryEnforcement.test_no_control_capability_exists)
control is not a valid HermesCapability in milestone 1. ... ok
test_root_package_exports_documented_symbols (__main__.TestPackageSurface.test_root_package_exports_documented_symbols)
Documented imports are available from the package root. ... ok
test_token_shim_exposes_creation_helpers (__main__.TestPackageSurface.test_token_shim_exposes_creation_helpers)
token.py compatibility shim exposes the reviewed token helpers. ... ok
test_create_token_returns_string_and_token (__main__.TestTokenCreation.test_create_token_returns_string_and_token)
create_hermes_token returns both token string and AuthorityToken. ... ok
test_created_token_is_valid (__main__.TestTokenCreation.test_created_token_is_valid)
Created token passes validation. ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.005s

OK
```

### Package Surface Check

```bash
cd services/hermes-adapter && python3 - <<'PY'
from hermes_adapter import HermesAdapter, make_summary_text
from hermes_adapter.token import create_hermes_token
print('package_ok', HermesAdapter.__name__)
print('helper_ok', callable(make_summary_text))
print('token_helper_ok', callable(create_hermes_token))
PY
```

Actual output:
```
package_ok HermesAdapter
helper_ok True
token_helper_ok True
```

### Smoke Proof

```bash
bash scripts/hermes_summary_smoke.sh --client test-client
```

Actual output:
```
connected=true
principal_id=test-principal
capabilities=['observe', 'summarize']
summary_appended=true
spine_event_verified=true

summary_appended_to_operations_inbox=true
```

## Coverage Notes

- The bootstrap gate now covers 13 tests, including package exports, the token-helper shim, replay protection, capability boundaries, and positive spine persistence for `appendSummary()`.
- The package-surface check proves the reviewed import paths execute directly from `services/hermes-adapter`.
- The smoke proof exercises the reviewed package surface and confirms that the latest `hermes_summary` spine event matches the emitted payload.
- `readStatus()` remains proofed at the capability-boundary level in this slice; no running-daemon status proof was added here.

## Verification Status

**VERIFIED** — The reviewed package surface, token shim, unit coverage, and summary smoke proof all pass in the current repo.
