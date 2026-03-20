# Hermes Adapter — Implementation

**Status:** Milestone 1 Complete
**Generated:** 2026-03-20

## Overview

Implements the Zend Hermes Adapter: a capability-scoped relay between Hermes Gateway and the Zend-native gateway contract. Milestone 1 grants exactly two capabilities — `observe` (read miner status) and `summarize` (append to event spine). Direct miner control is blocked.

## Touched Surfaces

| Surface | Location | Change |
|---------|----------|--------|
| `services/hermes-adapter/adapter.py` | Core adapter | New |
| `services/hermes-adapter/authority.py` | Token encoding/decoding | New |
| `services/hermes-adapter/cli.py` | CLI interface | New |
| `services/hermes-adapter/__init__.py` | Package init | New |
| `scripts/bootstrap_hermes.sh` | Bootstrap verification | New |
| `services/home-miner-daemon/daemon.py` | Home miner daemon | Modified |
| `services/home-miner-daemon/spine.py` | Event spine | Modified |
| `services/home-miner-daemon/store.py` | Principal store | Modified |

## Components

### HermesAdapter (`adapter.py`)

```python
class HermesAdapter:
    def connect(authority_token: str) -> HermesConnection
    def readStatus() -> MinerSnapshot      # requires 'observe'
    def appendSummary(summary: HermesSummary) -> None  # requires 'summarize'
    def getScope() -> list[HermesCapability]
    def _require_capability(capability)     # enforces boundaries
```

**Key behaviors:**
- `connect()` validates token via `decode_authority_token()`, checks expiration
- `readStatus()` calls `GET /status` on the gateway, returns `MinerSnapshot`
- `appendSummary()` calls `spine.append_hermes_summary()` for event spine write
- `_require_capability()` raises `PermissionError` if capability not in scope

### AuthorityToken (`authority.py`)

```python
def encode_authority_token(principal_id, capabilities, expires_at=None) -> str
def decode_authority_token(token: str) -> AuthData
def save_hermes_token(token: str) -> None
def load_hermes_token() -> str | None
```

Token format: base64-encoded JSON. Milestone 1 uses placeholder encoding (no cryptographic signing).

### CLI (`cli.py`)

Subcommands: `connect`, `status`, `summarize`, `token`, `scope`

### Bootstrap Script (`bootstrap_hermes.sh`)

End-to-end proof script:
1. Starts home-miner daemon if not running
2. Creates Hermes authority token with `observe` + `summarize`
3. Verifies observe capability (reads miner status)
4. Verifies summarize capability (appends summary to event spine)

## Capability Boundaries (Milestone 1)

| Action | Allowed |
|--------|---------|
| Read miner status | ✓ (`observe`) |
| Append summary | ✓ (`summarize`) |
| Start/stop miner | ✗ blocked |
| Set mining mode | ✗ blocked |
| Modify payout target | ✗ blocked |

## Deferred

- Real cryptographic token signing (placeholder: base64 JSON)
- Hermes Gateway live integration (stub: adapter-to-daemon only)
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← Enforces capability boundaries
      |
      v
Zend Gateway Contract (home-miner-daemon)
      |
      v
Event Spine
```