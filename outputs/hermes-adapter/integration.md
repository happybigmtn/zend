# Hermes Adapter — Integration

**Status:** Integrated
**Date:** 2026-03-20

## Slice Scope

`hermes-adapter:hermes-adapter`

## Integration Points

### Upstream Dependencies

| Dependency | Purpose | Interface |
|------------|---------|----------|
| `home-miner-daemon` | Principal identity store, event spine, status surface | Python import: `store.load_or_create_principal`, `spine.append_hermes_summary`, in-process proof transport |
| `ZEND_STATE_DIR` | Shared state directory for principal identity | Env var |
| `ZEND_DAEMON_URL` | Daemon transport selector | Env var (default: `http://127.0.0.1:8080`, proof fallback: `inproc://home-miner-daemon`) |

### Downstream Consumers

| Consumer | Uses |
|----------|------|
| Event spine (`state/event-spine.jsonl`) | `hermes_summary` events written by `appendSummary()` |
| Daemon status endpoint (`/status`) | Read by `readStatus()` via `HermesAdapter` |

### Event Flows

```
Hermes Gateway
    │
    ├──connect(authority_token)──►HermesAdapter
    │                                    │
    │                              decode + validate token
    │                                    │
    │                              principal binding check
    │                                    │
    │◄──HermesConnection─────────────────┘
    │
    ├──readStatus()──►_require_capability(OBSERVE)
    │                      │
    │                      ├──GET /status
    │                      ├──or inproc daemon snapshot
    │                      │
    │◄──MinerSnapshot──────┘
    │
    ├──appendSummary()──►_require_capability(SUMMARIZE)
    │                         │
    │                         ├──append_hermes_summary()
    │                         │
    │                         ▼
    │              state/event-spine.jsonl
    │              {"kind": "hermes_summary", ...}
    │
    └──getScope()──►_require_capability(...)
                       │
                       ▼
                  [capability list]
```

## Boundary Enforcement

| Boundary | Mechanism |
|----------|-----------|
| No direct miner control | `_require_capability()` gates all daemon calls |
| No payout-target mutation | No such method exists in `HermesAdapter` |
| No inbox composition | No inbox methods in `HermesAdapter` |
| Observe-only for status reads | `readStatus()` requires `observe` capability |
| Summarize-only for spine writes | `appendSummary()` requires `summarize` capability |

## State Persistence

| State | Location | Lifetime |
|-------|----------|----------|
| Principal identity | `state/principal.json` | Persistent across restarts |
| Event spine | `state/event-spine.jsonl` | Append-only, persistent |
| Daemon PID | `state/daemon.pid` | Removed on daemon stop |

## First Proof Gate

`./scripts/bootstrap_hermes.sh`

### What the Gate Proves

1. **Transport selection** — the adapter uses either the live daemon URL or the sandbox-safe in-process transport
2. **Principal existence** — principal identity is created/loaded from `ZEND_STATE_DIR`
3. **Adapter connection** — `HermesAdapter.connect()` establishes `HermesConnection` only after token validation
4. **Capability enforcement** — observe and summarize capabilities are checked
5. **Status reading** — `readStatus()` returns `MinerSnapshot` from the selected daemon transport
6. **Summary appending** — `appendSummary()` writes `hermes_summary` event to spine
7. **Scope reflection** — `getScope()` returns the granted capabilities
8. **Expired authority rejection** — the proof gate confirms stale delegated authority is denied

### Gate Output

```
[WARN] Socket bind unavailable; using in-process daemon proof transport
[INFO] Bootstrapping Hermes adapter...
principal_id=9167d7a6-0b71-4a3d-b643-4145168634a2
connected=true
daemon_transport=inproc://home-miner-daemon
device_name=hermes-gateway
capabilities=['observe', 'summarize']
status_read=true
miner_status=stopped
summary_appended=true
scope=['observe', 'summarize']
expired_token_rejected=true
[INFO] Hermes adapter bootstrap complete
```

**Result:** PASS — all assertions succeeded.
