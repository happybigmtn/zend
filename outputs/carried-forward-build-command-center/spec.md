# Spec: Zend Home Command Center — Milestone 1 Slice

**Lane:** `carried-forward-build-command-center`
**Status:** Active — genesis implementation in progress
**Last Updated:** 2026-03-22
**Provenance:** Carried from `plans/2026-03-19-build-zend-home-command-center.md`

---

## Purpose / User-Visible Outcome

A home miner operator can open a mobile-shaped web client on their phone, pair it to their home miner over the local network, and see the miner's live status, mode, and temperature. They can pause or resume mining and switch between paused / balanced / performance modes. Every control action produces an auditable receipt. No mining work runs on the phone.

---

## Whole-System Goal

Prove Zend's core product claim — mobile-friendly mining without on-device work — by delivering a LAN-paired control plane between a thin gateway client and a home miner daemon. The system is designed so that future work can extend the control plane to remote access, add a Hermes delegation layer, and back the operations inbox with a private encrypted event spine, without changing the contracts established here.

---

## Scope

**In scope for milestone 1:**
- Home miner daemon exposing HTTP control and status endpoints
- Gateway client (mobile-shaped single-page app) with four destinations: Home, Inbox, Agent, Device
- Bootstrap and pairing scripts
- Reference contracts for inbox, event spine, error taxonomy, design checklist, observability, and Hermes adapter

**Out of scope for milestone 1:**
- Automated tests (genesis plan 004)
- CI/CD pipeline (genesis plan 005)
- Token replay prevention enforcement (genesis plan 006)
- TLS on local connections
- Remote access over WAN (genesis plan 011)
- Hermes adapter implementation (genesis plan 009)
- Encrypted operations inbox (genesis plans 011, 012)
- Real miner hardware backend

---

## Current State

The daemon, gateway client, scripts, and reference contracts are implemented. All HTTP endpoints respond correctly. The design system is applied and WCAG AA compliant. However, the following are not yet enforced: token replay prevention, event spine persistence (spine writes to JSONL but daemon does not call spine on control actions), Hermes adapter implementation, and automated test coverage.

---

## Architecture / Runtime Contract

```
┌─────────────────────┐     HTTP (LAN)      ┌──────────────────────────┐
│  Thin Mobile Client │ ──────────────────►  │  Home Miner Daemon       │
│  (zend-home-gateway)│  127.0.0.1:8080     │  (services/daemon/)     │
│  apps/index.html    │                     │                          │
└─────────────────────┘                     │  store.py  — principal   │
                                            │              + pairings  │
                                            │  spine.py  — events     │
                                            │  simulator — status     │
                                            └──────────────────────────┘
```

### Daemon Contract

- Binds to `ZEND_BIND_HOST` (default `127.0.0.1`) on port `ZEND_PORT` (default `8080`)
- No authentication on endpoints; relies on LAN isolation for milestone 1
- No TLS

### Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/health` | `MinerSnapshot.health` |
| GET | `/status` | Full `MinerSnapshot` |
| POST | `/miner/start` | `{"success": bool}` |
| POST | `/miner/stop` | `{"success": bool}` |
| POST | `/miner/set_mode` | `{"success": bool, "mode": "paused\|balanced\|performance"}` |

### MinerSnapshot Schema

```python
{
    "status": "running" | "stopped" | "offline" | "error",
    "mode": "paused" | "balanced" | "performance",
    "hashrate_hs": int,        # hashes per second
    "temperature": float,        # celsius
    "uptime_seconds": int,
    "freshness": str            # ISO 8601 UTC
}
```

### Principal Schema

```python
{
    "id": str,            # UUID v4
    "created_at": str,    # ISO 8601
    "name": str
}
```

### GatewayPairing Schema

```python
{
    "id": str,
    "principal_id": str,
    "device_name": str,
    "capabilities": ["observe", "control"],
    "paired_at": str,          # ISO 8601
    "token_expires_at": str,   # ISO 8601
    "token_used": bool         # NOTE: not yet enforced in daemon
}
```

### SpineEvent Schema

```python
{
    "id": str,             # UUID v4
    "principal_id": str,
    "kind": "pairing_requested" | "pairing_granted" | "capability_revoked" |
            "miner_alert" | "control_receipt" | "hermes_summary" | "user_message",
    "payload": dict,
    "created_at": str,     # ISO 8601
    "version": 1
}
```

### Error Taxonomy

| Code | User Message |
|------|-------------|
| `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired." |
| `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used." |
| `GATEWAY_UNAUTHORIZED` | "You don't have permission to perform this action." |
| `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home." |
| `MINER_SNAPSHOT_STALE` | "Showing cached status. Zend Home may be offline." |
| `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress." |
| `EVENT_APPEND_FAILED` | "Unable to save this operation." |
| `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity detected." |

---

## Adoption Path

New contributors can verify the slice works in four commands:

```bash
./scripts/bootstrap_home_miner.sh              # starts daemon, creates principal
curl http://127.0.0.1:8080/health              # → {"healthy": true, ...}
curl http://127.0.0.1:8080/status               # → full MinerSnapshot
open apps/zend-home-gateway/index.html          # → live gateway client
./scripts/no_local_hashing_audit.sh             # → proves no mining on client
```

---

## Acceptance Criteria

1. `curl http://127.0.0.1:8080/health` returns HTTP 200 with `{"healthy": true}` when daemon is running
2. `curl http://127.0.0.1:8080/status` returns a complete `MinerSnapshot`
3. `curl -X POST -d '{"mode":"balanced"}' http://127.0.0.1:8080/miner/set_mode` returns `{"success": true, "mode": "balanced"}`
4. Gateway client at `apps/zend-home-gateway/index.html` fetches and displays live miner status
5. `state/principal.json` is created and populated after bootstrap
6. `state/pairing-store.json` contains at least one pairing record after `pair_gateway_client.sh` runs
7. `state/event-spine.jsonl` is created and appended to after control actions (spine appends are wired)
8. `no_local_hashing_audit.sh` exits 0 on the gateway client

---

## Remaining Work

| Item | Genesis Plan | Priority |
|------|-------------|----------|
| Fix token replay prevention | 006 | High |
| Add automated tests | 004 | High |
| Wire event spine appends to daemon control paths | 012 | High |
| Wire principal ID from daemon to gateway client | — | Medium |
| Security hardening (capability checks, TLS) | 003 | Medium |
| Hermes adapter implementation | 009 | Medium |
| CI/CD pipeline | 005 | Medium |
| Observability: structured logging | 007 | Medium |
| Document gateway proof transcripts | 008 | Medium |
| Encrypted operations inbox | 011, 012 | Medium |
| LAN-only enforcement verification | 004 | Medium |
| Remote access with formal verification | 011 | Low |
| Multi-device & recovery | 013 | Low |
| UI polish & accessibility | 014 | Medium |

---

## References

- Design system: `DESIGN.md`
- Spec guide: `SPEC.md`
- Plans guide: `PLANS.md`
- Original ExecPlan: `plans/2026-03-19-build-zend-home-command-center.md`
- Design doc: `docs/designs/2026-03-19-zend-home-command-center.md`
- Reference contracts: `references/`
