# Hermes Adapter Capability Spec

**Status:** Implemented — Milestone 1 complete
**Spec type:** Capability Spec (per `SPEC.md`)

---

## Purpose / User-Visible Outcome

Hermes is an AI agent that connects to the Zend home-miner daemon through a scoped adapter. After this capability is deployed:

- Hermes can authenticate using an authority token and read miner status through the adapter.
- Hermes can append structured summaries to the event spine.
- Hermes **cannot** issue control commands to the miner.
- Hermes **cannot** read `user_message` events — those remain private.
- Device-pairing and Hermes-pairing stores are separate concerns sharing one backing file, with distinct schemas.

Operators see Hermes summaries in the Inbox alongside miner alerts and control receipts. The Agent tab in the gateway client shows Hermes connection state (not yet wired in milestone 1).

---

## Whole-System Goal

Establish a durable, capability-gated adapter surface between the Hermes agent runtime and the Zend event spine and miner simulator. The adapter enforces a strict allowlist of capabilities (`observe`, `summarize`) and a strict allowlist of readable event kinds. This is the foundation for agent-delegated operations in Zend's ops inbox.

---

## Scope

This spec covers the first honest implementation slice:

| What is in scope | What is out of scope |
|-----------------|----------------------|
| `hermes.py` adapter module | Gateway client Agent tab wiring |
| Daemon `/hermes/*` HTTP endpoints | Integration tests against live daemon |
| CLI `hermes` subcommand group | Hermes token signing / HMAC |
| Authority token validation | Hermes-to-gateway RPC over LAN |
| Capability boundary enforcement | Real miner hardware integration |
| Event filtering (allowlist) | Token revocation / rotation |
| Idempotent Hermes pairing | Rate limiting on Hermes operations |

---

## Architecture / Runtime Contract

### Adapter layer

```
Hermes runtime
  └─► hermes.py adapter  ← THIS SPEC
       ├─ connect(authority_token) → HermesConnection
       ├─ pair_hermes(hermes_id, device_name) → HermesConnection
       ├─ read_status(connection) → MinerSnapshot
       ├─ append_summary(connection, text, scope) → EventRef
       └─ get_filtered_events(connection, limit) → List[SpineEvent]

  └─► daemon.py GatewayHandler
       ├─ POST /hermes/connect
       ├─ POST /hermes/pair
       ├─ GET  /hermes/status
       ├─ POST /hermes/summary
       └─ GET  /hermes/events

  └─► cli.py  (hermes subcommand group)
```

### HermesConnection dataclass

```python
@dataclass
class HermesConnection:
    hermes_id: str           # e.g. "hermes-001"
    principal_id: str        # UUID of the principal who owns this pairing
    capabilities: List[str]  # always ['observe', 'summarize'] for Hermes
    connected_at: str       # ISO-8601 UTC
```

### Constants (hardcoded — not derived from user input)

```python
HERMES_CAPABILITIES = ['observe', 'summarize']   # control intentionally absent

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]  # user_message intentionally absent
```

### Authority token format

```
hermes_id|principal_id|capabilities|expiry_iso
```

Example: `hermes-001|550e8400-e29b-41d4-a716-446655440000|observe,summarize|2026-04-21T12:00:00+00:00`

The token is stored in `pairing-store.json` keyed by `hermes_id`. The daemon's Hermes endpoints look up tokens server-side — the HTTP layer transmits only `hermes_id` via the `Authorization: Hermes <hermes_id>` header.

### Security boundary enforcement points

| Action | Required capability | Failure mode |
|--------|--------------------|--------------|
| `read_status` | `observe` | `PermissionError` → HTTP 403 |
| `append_summary` | `summarize` | `PermissionError` → HTTP 403 |
| `get_filtered_events` | `observe` | `PermissionError` → HTTP 403 |
| Any `/miner/*` POST with Hermes auth | — | HTTP 403 (hard reject) |

---

## Adoption Path

Hermes agents are onboarded by calling `pair_hermes(hermes_id, device_name)` once. Pairing is idempotent: re-pairing with the same `hermes_id` returns the existing record. If the stored token has expired, re-pairing regenerates it.

After pairing, the operator obtains the stored authority token (via `get_authority_token(hermes_id)`) and delivers it to the Hermes runtime out-of-band. The Hermes runtime calls `connect(authority_token)` on first use.

---

## Acceptance Criteria

All criteria are expressed as observable behavior, not checkbox state.

1. **Token validation:** A token with wrong structure, wrong capabilities, or past expiry causes `connect()` to raise `ValueError`. A token with correct structure, `observe`+`summarize`, and future expiry returns a valid `HermesConnection`.

2. **Capability gates:** Calling `read_status`, `append_summary`, or `get_filtered_events` with a connection that lacks the required capability raises `PermissionError` at the adapter layer before any I/O.

3. **Control rejection:** Any HTTP request to a `/miner/*` endpoint carrying `Authorization: Hermes <hermes_id>` receives HTTP 403 before miner logic runs.

4. **Event filter:** `get_filtered_events` returns events of kinds `hermes_summary`, `miner_alert`, and `control_receipt` only. Events of kind `user_message` are never returned.

5. **Pairing idempotence:** Calling `pair_hermes("hermes-001", ...)` twice returns the same `hermes_id` and `principal_id` both times. The second call does not create a duplicate pairing record.

6. **Expired re-pair:** If a stored token has expired, calling `pair_hermes` for that `hermes_id` regenerates a valid token and stores it.

7. **hermes_id injection guard:** `pair_hermes` rejects any `hermes_id` containing the `|` delimiter with `ValueError`.

8. **Test suite:** `python3 -m pytest tests/test_hermes.py -v` passes all 24 tests.

---

## Failure Handling

| Failure | Behavior |
|---------|----------|
| Empty authority token | `ValueError` with "Empty" in message |
| Malformed token (not 4 `\|`-separated parts) | `ValueError` with "Malformed" in message |
| Unknown capability in token | `ValueError` with "HERMES_INVALID_CAPABILITY" |
| Expired token | `ValueError` with "expired" in message |
| Missing required capability at action time | `PermissionError` |
| `hermes_id` not paired | `get_authority_token` returns `None`; daemon returns HTTP 401 |
| Server-side I/O error in `append_summary` | Propagates from `spine.append_event` |

---

## Relationship to Other Documents

- `DESIGN.md` defines the Zend visual and interaction design system. The Hermes adapter provides data that flows into the **Inbox** (summaries, alerts, receipts) and **Agent** (Hermes connection state) tabs described there.
- `plans/2026-03-19-build-zend-home-command-center.md` is the active ExecPlan. This spec covers Milestones 1 and 2 of that plan.
- `docs/designs/2026-03-19-zend-home-command-center.md` is the CEO-mode product direction.
