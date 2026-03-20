# Hermes Adapter — Agent Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-20

## Overview

The Hermes Adapter connects Hermes Gateway to the Zend-native gateway contract using delegated authority. It enforces capability boundaries (observe/summarize) before relaying any request.

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

## Capability Scope

```typescript
type HermesCapability = 'observe' | 'summarize';
```

Milestone 1 grants Hermes:
- **observe**: Read miner status via `/status` endpoint
- **summarize**: Append summaries to the event spine

Direct miner control (start/stop/set_mode) is NOT permitted in milestone 1.

## Implementation

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| HermesAdapter | `services/hermes-adapter/adapter.py` | Core adapter class |
| AuthorityToken | `services/hermes-adapter/authority.py` | Token encoding/decoding |
| CLI | `services/hermes-adapter/cli.py` | Command-line interface |
| Bootstrap | `scripts/bootstrap_hermes.sh` | Preflight verification |

### HermesAdapter Interface

```python
class HermesAdapter:
    def connect(authority_token: str) -> HermesConnection:
        """Connect using delegated authority token."""

    def readStatus() -> MinerSnapshot:
        """Read miner status (requires 'observe')."""

    def appendSummary(summary: HermesSummary) -> None:
        """Append summary to event spine (requires 'summarize')."""

    def getScope() -> list[HermesCapability]:
        """Return current authority scope."""
```

### Authority Token

The authority token is issued during Hermes pairing and encodes:
- Principal ID
- Granted capabilities
- Expiration time

Token format: base64-encoded JSON

### Event Spine Access

Hermes can read from event spine:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts it may have generated)
- `control_receipt` (recent actions)

Hermes can write to event spine:
- `hermes_summary` (new summaries)

## Boundaries (Enforced by Adapter)

| Action | Milestone 1 |
|--------|-------------|
| Read miner status | ✓ observe |
| Append summary | ✓ summarize |
| Start/stop miner | ✗ blocked |
| Set mining mode | ✗ blocked |
| Modify payout target | ✗ blocked |
| Read user messages | ✗ blocked |

## Bootstrap Script

```bash
./scripts/bootstrap_hermes.sh
```

Verification steps:
1. Start home-miner daemon if not running
2. Create Hermes authority token with observe+summarize
3. Verify observe capability (read status)
4. Verify summarize capability (append summary)

## Usage

```bash
# Generate authority token
cd services/hermes-adapter
python3 cli.py token --capabilities observe,summarize --save

# Connect to gateway
python3 cli.py connect

# Read miner status (requires observe)
python3 cli.py status

# Append summary (requires summarize)
python3 cli.py summarize --text "Miner running in balanced mode"
```

## Dependencies

- Home Miner Daemon (must be running on `127.0.0.1:8080`)
- Event Spine (via home-miner-daemon/spine.py)
- Principal store (via home-miner-daemon/store.py)

## Milestone 1 Completeness

- [x] HermesAdapter class with connect/disconnect
- [x] observe capability enforcement
- [x] summarize capability enforcement
- [x] Authority token encoding/decoding
- [x] CLI interface
- [x] Bootstrap verification script
- [ ] Real cryptographic token signing (deferred)
- [ ] Hermes Gateway live integration (future milestone)