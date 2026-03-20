# Hermes Adapter — Integration

## Overview

The Hermes adapter bridges Hermes Gateway to Zend's home-miner infrastructure. It is bootstrapped via `scripts/bootstrap_hermes.sh` and exposes health status via `scripts/hermes_status.sh`.

## Component Integration

```
┌─────────────────────────────────────────────────────┐
│  bootstrap_hermes.sh                                │
│  ├─ starts home-miner-daemon (daemon.py)            │
│  ├─ creates state/hermes/principal.json             │
│  └─ verifies append_hermes_summary() via spine.py  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  home-miner-daemon (daemon.py)                       │
│  ├─ HTTP server on 127.0.0.1:8080                  │
│  ├─ /health endpoint                               │
│  └─ spine.append_hermes_summary()                 │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  state/                                             │
│  ├─ hermes/principal.json  (Hermes identity)       │
│  ├─ daemon.pid             (daemon PID)           │
│  └─ event-spine.jsonl      (append-only event log) │
└─────────────────────────────────────────────────────┘
```

## State Files

| File | Purpose | Created By |
|------|---------|------------|
| `state/hermes/principal.json` | Hermes adapter identity and authority | `bootstrap_hermes.sh` |
| `state/daemon.pid` | Daemon process ID | `bootstrap_hermes.sh` |
| `state/event-spine.jsonl` | Append-only event log | `daemon.py` via `spine.py` |

## Boot Sequence

1. **Daemon start** — `bootstrap_hermes.sh` starts `daemon.py` in the background, writes PID to `state/daemon.pid`
2. **Health wait** — curl polls `http://127.0.0.1:8080/health` until daemon responds
3. **Hermes state creation** — `state/hermes/principal.json` written with observe-only authority
4. **Summary append verification** — Python inline script calls `spine.append_hermes_summary()` to prove write access

## Authority Model

Hermes milestone 1 is **observe-only**:
- Reads miner status and state from daemon
- Appends Hermes summary events to the event spine
- No direct miner control, no capability mutation

## Daemon Health Endpoint

The daemon exposes `GET /health` returning daemon status. When the daemon starts successfully:
- HTTP 200 with health payload
- Bootstrap proceeds to Hermes state creation

## Socket Binding Constraints

The daemon binds to `127.0.0.1:8080` (LAN-only). In sandboxed environments where socket bind/connect is restricted, the daemon startup may fail with `PermissionError` or `OSError`. The Hermes adapter fails closed in such cases — `bootstrap_hermes.sh` exits non-zero.

## Event Spine

The event spine (`state/event-spine.jsonl`) is the source of truth for Hermes events. Each `hermes_summary` event records:
- `id` — event UUID
- `kind` — `"hermes_summary"`
- `principal_id` — Hermes adapter principal (`hermes-adapter-001`)
- `authority_scope` — `["observe"]`
- `summary_text` — the summary content
- `created_at` — ISO8601 timestamp
