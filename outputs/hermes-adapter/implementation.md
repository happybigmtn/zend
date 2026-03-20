# Hermes Adapter — Implementation

**Status:** Milestone 1 Implementation Complete
**Generated:** 2026-03-20

## What Was Implemented

### Hermes Adapter Module (`services/hermes-adapter/`)

#### Core Adapter (`adapter.py`)

The `HermesAdapter` class implements the interface defined in `references/hermes-adapter.md`:

```python
class HermesAdapter:
    def connect(self, authority_token: str) -> HermesConnection
    def readStatus(self) -> MinerSnapshot
    def appendSummary(self, summary: HermesSummary) -> None
    def getScope(self) -> list[HermesCapability]
    def isConnected(self) -> bool
    def disconnect(self) -> None
```

Key implementation details:
- Token validation via `token.py` before connection established
- Token marked as used after successful `connect()` to prevent replay
- Capability checks before each operation (`_check_capability()`)
- Daemon communication via HTTP API (daemon.py endpoints)
- Spine integration via `spine.append_hermes_summary()`

#### Error Types (`errors.py`)

```python
HermesError               # Base exception
├── HermesUnauthorizedError   # Invalid/expired/replayed token
├── HermesCapabilityError      # Capability not in scope
└── HermesConnectionError     # Daemon unreachable or not connected
```

#### Token Management (`token.py`)

- `create_hermes_token()` — Creates token with principal, capabilities, expiration
- `validate_token()` — Validates token exists, not expired, not replayed
- `mark_token_used()` — Marks token used to prevent replay
- Tokens stored in `state/hermes-tokens.json`

#### Data Models (`models.py`)

- `HermesConnection` — Active connection with principal and capabilities
- `HermesSummary` — Summary text with authority scope and timestamp
- `MinerSnapshot` — Miner status with freshness timestamp
- `AuthorityToken` — Decoded token data
- `make_summary_text()` — Helper to create HermesSummary

### Tests (`services/hermes-adapter/tests/`)

| Test Class | Coverage |
|------------|----------|
| `TestTokenCreation` | Token creation and validation |
| `TestAdapterConnect` | Connect with valid/invalid tokens, replay protection |
| `TestAdapterReadStatus` | Observe capability enforcement |
| `TestAdapterAppendSummary` | Summarize capability enforcement |
| `TestAdapterGetScope` | Scope reporting |
| `TestBoundaryEnforcement` | Milestone 1 boundaries verified |

### Updated Smoke Test (`scripts/hermes_summary_smoke.sh`)

Updated to use the HermesAdapter instead of calling spine functions directly:
1. Creates authority token via `create_hermes_token()`
2. Connects via `adapter.connect()`
3. Appends summary via `adapter.appendSummary()`

## Files Changed

```
services/hermes-adapter/
    __init__.py
    adapter.py
    errors.py
    models.py
    token.py
    tests/
        __init__.py
        test_hermes_adapter.py

scripts/hermes_summary_smoke.sh (updated)

outputs/hermes-adapter/
    agent-adapter.md
    review.md
```

## Architecture

```
HermesAdapter
     |
     +-- token.py: validate_token(), create_hermes_token()
     |
     +-- adapter.py: connect(), readStatus(), appendSummary(), getScope()
           |
           +-- daemon.py: HTTP API calls (/status, /health)
           |
           +-- spine.py: append_hermes_summary()
```

## Key Design Decisions

1. **Token replay protection via used flag** — Tokens can only be used once, preventing replay attacks
2. **Capability checks before operations** — Each operation validates scope before execution
3. **HTTP API for daemon communication** — Adapter talks to daemon via HTTP, not direct Python calls
4. **Siblings import for spine** — Adapter imports from home-miner-daemon as sibling module
5. **Environment-based state directory** — Uses `ZEND_STATE_DIR` env var for testability