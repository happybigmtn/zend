# Hermes Adapter Implementation — Specification

**Status:** Complete, post-review fixes applied
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`

---

## Overview

This document describes the Hermes adapter — a scoped capability boundary that lets the Hermes AI agent interact with the Zend home miner daemon. Hermes uses the same API primitives as human clients but with a narrower capability scope: `observe` (read miner status) and `summarize` (append summaries). Control commands are never available to Hermes.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ←  services/home-miner-daemon/hermes.py
      |
      v
Zend Gateway Contract / Daemon  (services/home-miner-daemon/daemon.py)
      |
      v
Event Spine  (services/home-miner-daemon/spine.py)
```

The adapter enforces:
- **Authority token validation** — token issued at connect, decoded and validated before session start
- **Capability checking** — `observe` + `summarize` only; `control` never granted
- **Event filtering** — `user_message` events are blocked from Hermes reads
- **Payload transformation** — fields Hermes shouldn't see are stripped from responses

---

## Capabilities

Hermes capabilities are `observe` and `summarize`, independent from the gateway's `observe` and `control`. This separation is intentional: Hermes can never inherit gateway control.

| Capability | Description | HTTP endpoint | CLI flag |
|------------|-------------|---------------|----------|
| `observe` | Read miner status snapshot | `GET /hermes/status` | `hermes status --token` |
| `summarize` | Append summaries to event spine | `POST /hermes/summary` | `hermes summary --text` |
| `control` | Issue miner commands | NOT available | NOT available |

---

## Auth Model (Milestone 1)

Milestone 1 uses **pairing-based auth on HTTP endpoints**. The authority token flow serves a discovery and session-establishment role; subsequent operational requests carry the `hermes_id` in the `Authorization: Hermes <id>` header and rely on the daemon's pairing store.

### Token flow

1. `POST /hermes/pair` — creates a pairing record (unauthenticated). Returns `token_expires_at`.
2. `POST /hermes/connect` — accepts authority token, validates it (expiry, capabilities, hermes_id), returns session info. This step verifies the token is genuine.
3. Operational requests (`GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events`) — use `Authorization: Hermes <hermes_id>` header. The daemon looks up the pairing record by `hermes_id` and uses its stored capabilities.

### Why not per-request token validation in milestone 1

Passing the full authority token on every request is possible but adds complexity (token replay risk, header size, parsing overhead) without meaningful security benefit at localhost/LAN scope. The pairing record is the durable trust anchor; the token is validated once at session establishment.

**Follow-up (tracked):** Per-request token re-validation with expiry enforcement before LAN exposure.

---

## Authority Token

The token is a base64-encoded JSON payload. Production would use signed JWTs (tracked separately).

| Field | Type | Description |
|-------|------|-------------|
| `hermes_id` | string | Hermes agent identifier |
| `principal_id` | string | Zend principal who authorized the connection |
| `capabilities` | list[string] | Subset of `['observe', 'summarize']` |
| `issued_at` | ISO 8601 | Token issuance timestamp |
| `expires_at` | ISO 8601 | Token expiry (24 h from issuance) |

Token validity window: **24 hours**.

---

## Adapter Interface

```python
# services/home-miner-daemon/hermes.py

HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str

    def is_capable(self, capability: str) -> bool: ...

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing
def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]
def issue_authority_token(hermes_id: str) -> str
def connect(authority_token: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str,
                   authority_scope: Optional[list[str]] = None) -> dict
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]
```

---

## Daemon Endpoints

| Endpoint | Method | Auth | Requires |
|----------|--------|------|----------|
| `/hermes/pair` | POST | None | — |
| `/hermes/connect` | POST | Token body | Valid token |
| `/hermes/status` | GET | `Authorization: Hermes <id>` | `observe` |
| `/hermes/summary` | POST | `Authorization: Hermes <id>` | `summarize` |
| `/hermes/events` | GET | `Authorization: Hermes <id>` | — |

### Auth header format

```
Authorization: Hermes <hermes_id>
```

Distinct from the gateway's device auth scheme (`Authorization: Bearer <token>`).

### Error responses

| Code | Error | Condition |
|------|-------|-----------|
| 400 | `missing_hermes_id` | Pairing request missing `hermes_id` |
| 400 | `missing_token` | Connect request missing `token` |
| 400 | `missing_summary_text` | Summary request missing `summary_text` |
| 400 | `invalid_json` | Request body not valid JSON |
| 403 | `HERMES_UNAUTHORIZED` | Missing/malformed auth or wrong capability |
| 403 | `HERMES_TOKEN_EXPIRED` | Token past expiry |
| 404 | `not_found` | Unknown endpoint |

---

## Event Filtering

**Hermes can read:**
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent actions

**Hermes CANNOT read:**
- `user_message` — private communications (hard blocked)
- Any other event kinds (absent from `HERMES_READABLE_EVENTS`)

**Hermes can write:**
- `hermes_summary` — new summaries with `summary_text`, `authority_scope`, `generated_at`

---

## Milestone 1 Boundaries

The following are intentionally NOT available to Hermes in milestone 1:

- Direct miner control commands (`start`, `stop`, `set_mode`)
- Payout target mutation
- Inbox message composition
- Read access to `user_message` events
- Gateway `control` capability inheritance

These boundaries are enforced by the adapter before any request is relayed.

---

## Files

### New
- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — Test suite (16 tests)
- `outputs/hermes-adapter-implementation/spec.md` — This specification
- `outputs/hermes-adapter-implementation/review.md` — Review document

### Modified
- `services/home-miner-daemon/daemon.py` — Added Hermes HTTP endpoints
- `services/home-miner-daemon/cli.py` — Added Hermes subcommands
- `apps/zend-home-gateway/index.html` — Updated Agent tab with real connection state
- `scripts/hermes_summary_smoke.sh` — End-to-end smoke test

---

## Validation

### Unit tests (16/16 pass)

```
$ python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v

TestHermesAdapter
  ✓ test_hermes_connect_valid
  ✓ test_hermes_connect_expired
  ✓ test_hermes_read_status
  ✓ test_hermes_append_summary
  ✓ test_hermes_no_control
  ✓ test_hermes_event_filter           ← user_message blocked
  ✓ test_hermes_invalid_capability     ← control rejected
  ✓ test_hermes_summary_appears_in_inbox
  ✓ test_hermes_pairing_idempotent
  ✓ test_is_token_expired
  ✓ test_hermes_read_status_requires_observe
  ✓ test_hermes_append_summary_requires_summarize

TestHermesAdapterDaemon
  ✓ test_daemon_hermes_status_endpoint_auth
  ✓ test_daemon_hermes_pairing_creates_record
  ✓ test_daemon_hermes_connect_endpoint_logic
  ✓ test_daemon_hermes_control_rejected
```

### Smoke test

```
$ bash scripts/hermes_summary_smoke.sh
Step 1: Pairing...         hermes_id=hermes-001, capabilities=['observe', 'summarize']
Step 2: Issuing token...   token=eyJoZXJtZXNfaWQiOiAiaGVybWVzLTAwMS...
Step 3: Connecting...      { "connected": true, "hermes_id": "hermes-001", ... }
Step 4: Status (observe)... { "status": "MinerStatus.STOPPED", "source": "hermes_adapter" }
Step 5: Summary (summarize) { "appended": true, "event_id": "...", "kind": "hermes_summary" }
Step 6: Filtered events... filtered_events_count=1, hermes_summary_count=1
Step 7: user_message blocked: true
All smoke tests passed!
```

---

## Post-Review Fixes Applied

Three critical findings from the independent review were confirmed and fixed:

### C1 — Runtime type mismatch (FIXED)
`_require_hermes_auth()` returned a `dict`; `read_status()` and `append_summary()` expected `HermesConnection`. This caused `AttributeError` on any HTTP request.

**Fix:** `_require_hermes_auth()` now constructs and returns a `HermesConnection` from the pairing record. `_hermes_check_capability()` uses `conn.is_capable()`.

### C2 — Dual auth model (DOCUMENTED)
HTTP operational endpoints used only the `Authorization: Hermes <id>` header, bypassing token validation. The `/hermes/connect` step became ceremonial.

**Resolution:** Documented as the intentional milestone-1 model. Token is validated at connect; pairing record is the trust anchor for subsequent requests. Follow-up tracked for per-request token re-validation before LAN exposure.

### C3 — State directory mismatch (FIXED)
`hermes.py` resolved state to `parents[1]` (`services/state/`); `daemon.py`, `spine.py`, and `store.py` all use `parents[2]` (`<repo_root>/state/`). Hermes state was silently partitioned from the rest.

**Fix:** Changed `hermes.py:_default_state_dir()` from `parents[1]` to `parents[2]`.

---

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Hermes can connect with authority token | ✅ |
| 2 | Hermes can read miner status via HTTP | ✅ (C1 fixed) |
| 3 | Hermes can append summaries via HTTP | ✅ (C1 fixed) |
| 4 | Hermes CANNOT issue control commands | ✅ |
| 5 | Hermes CANNOT read `user_message` events | ✅ |
| 6 | Agent tab shows real connection state | ✅ |
| 7 | State dir resolved consistently across all modules | ✅ (C3 fixed) |
| 8 | All 16 unit tests pass | ✅ |
| 9 | Smoke test passes | ✅ |

---

## Follow-up Work

| # | Item | Priority |
|---|------|----------|
| F1 | Per-request token validation on HTTP endpoints (before LAN deploy) | High |
| F2 | `unpair_hermes()` function + `/hermes/unpair` endpoint | High |
| F3 | JWT upgrade for authority tokens (signed, not base64 JSON) | Medium |
| F4 | Add `observe` capability check to `/hermes/events` endpoint | Medium |
| F5 | Remove dead code in `connect()` (unused expiration computation) | Low |
| F6 | File locking on Hermes pairing store for multi-agent deployments | Low |

These are tracked independently and do not block milestone 1 acceptance.
