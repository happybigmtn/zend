# Hermes Adapter Implementation — Capability Spec

**Status:** Draft · First honest reviewed slice
**Lane:** `hermes-adapter`
**Last Updated:** 2026-03-22

---

## Purpose / User-Visible Outcome

After this slice lands, Hermes Gateway can connect to the Zend home-miner daemon through a Zend-native adapter. Hermes receives only the capabilities Zend explicitly grants: **observe** (read miner status) and **summarize** (append a Hermes summary into the encrypted operations inbox). Hermes cannot issue miner control commands, cannot read user messages, and cannot bypass Zend's capability checks.

A user or agent can see that Hermes is connected, what authority it holds, and which summaries it has appended — all surfaced in the Zend Home **Agent** tab and the **Inbox** tab alongside other operational receipts.

---

## Whole-System Goal

Zend milestone 1 must own its gateway contract and keep Hermes as an integrated but bounded participant. The Zend adapter is the single enforcement boundary: every Hermes request passes through it, and the adapter enforces capability scope, filters event kinds, and appends structured receipts before any action is taken.

This goal is a durable product decision confirmed in `specs/2026-03-19-zend-product-spec.md`: "Zend owns the canonical gateway contract. Hermes integration is required in phase one, but it enters through a Zend adapter rather than defining the core protocol."

---

## Scope

This slice delivers the Hermes adapter as a first-class daemon module. It does not change the gateway contract itself, the event-spine schema, or any inbox projection. The slice is bounded to:

- `hermes.py` — the adapter Python module
- `HermesConnection` — a connection handle holding validated authority scope
- `readStatus()` — delegated status read through the adapter
- `appendSummary()` — Hermes summary appended to the event spine through the adapter
- Event filtering — `user_message` events are never delivered to Hermes
- Hermes pairing endpoint — the daemon-side `/hermes/pair` route that issues authority tokens
- Authority token validation — decode and enforce expiration and scope

---

## Current State

The daemon scaffold exists in `services/` (or equivalent) and exposes a gateway contract with `observe` and `control` capability scopes. The event spine schema is defined in `references/event-spine.md` with `hermes_summary` as a valid `EventKind`. The `PrincipalId` contract and pairing records are defined in `references/inbox-contract.md`. No Hermes adapter module exists yet.

---

## Architecture / Runtime Contract

### Adapter Module: `hermes.py`

```
Hermes Gateway
      |
      | HTTPS / local RPC
      v
hermes.py  ← Zend Hermes Adapter
      |
      | validate token + filter events
      v
Zend Gateway Contract (existing daemon)
      |
      v
Event Spine
```

### `HermesConnection`

```python
class HermesConnection:
    authority_token: str       # JWT or opaque token issued by /hermes/pair
    scope: list[HermesCapability]   # ['observe', 'summarize']
    expires_at: datetime
    principal_id: PrincipalId
```

`HermesConnection` is obtained by calling `hermes_adapter.connect(authority_token)`. The adapter validates the token signature and expiry before returning a handle. All subsequent operations are methods on this handle.

### `HermesCapability`

```python
HermesCapability = Literal['observe', 'summarize']
```

Phase 1 Hermes authority is **observe-only plus summarize**. Direct `control` of the miner through Hermes is not part of milestone 1 and is explicitly out of scope.

### `hermes_adapter.connect(token: str) → HermesConnection`

1. Decode the authority token (JWT or sealed local token).
2. Verify signature against the daemon's secret.
3. Check `expires_at` is in the future.
4. Extract `scope` and `principal_id`.
5. Return a `HermesConnection` handle.

Raises `hermes_adapter.InvalidToken` if signature fails. Raises `hermes_adapter.TokenExpired` if `expires_at` is past.

### `HermesConnection.readStatus() → MinerSnapshot`

Requires scope `'observe'`. Calls the daemon's existing status-read path and returns a `MinerSnapshot` with a freshness timestamp. Raises `hermes_adapter.Unauthorized` if scope does not include `'observe'`.

### `HermesConnection.appendSummary(summary: HermesSummary) → None`

Requires scope `'summarize'`. Validates the summary payload, wraps it in a `hermes_summary` spine event, and appends it through the daemon's event-spine writer. Raises `hermes_adapter.Unauthorized` if scope does not include `'summarize'`.

The event payload:

```python
HermesSummary = {
    "summary_text": str,
    "authority_scope": list[HermesCapability],
    "generated_at": str,   # ISO 8601
}
```

### Event Filtering

The adapter must filter the event stream before returning any data to Hermes. `user_message` events must never be delivered to Hermes. All other event kinds (`hermes_summary`, `miner_alert`, `control_receipt`) are readable by Hermes when `'observe'` is granted.

### Hermes Pairing Endpoint: `POST /hermes/pair`

Daemon-side route that:
1. Accepts a Hermes pairing claim (device name, requested scope).
2. Issues an authority token encoding `principal_id`, granted `scope`, and `expires_at`.
3. Records the Hermes pairing record in the daemon's state.

Response:
```json
{
  "authority_token": "<token>",
  "scope": ["observe", "summarize"],
  "expires_at": "2026-04-22T00:00:00Z"
}
```

### Error Taxonomy

The adapter defines the following named errors, consistent with `references/error-taxonomy.md`:

| Error | Meaning |
|---|---|
| `InvalidToken` | Token signature invalid or malformed |
| `TokenExpired` | Token has passed its `expires_at` |
| `Unauthorized` | Operation requires a capability not in scope |
| `EventAppendFailed` | Spine write failed (raised from the event-spine writer) |
| `AdapterUnavailable` | Daemon or event-spine writer is not reachable |

---

## Adoption Path

This slice is the first of two planned Hermes adapter slices:

1. **This slice (milestone 1a):** Adapter module, observe + summarize, event filtering, Hermes pairing endpoint. Ends with a working `hermes.py` smoke test and a review pass.
2. **Future slice (milestone 1b):** Tests for trust-ceremony state, Hermes delegation boundaries, event-spine routing, inbox receipt behavior, and accessibility-sensitive states — as called out in the master ExecPlan.

The adapter is additive: the existing daemon continues to work without Hermes. A daemon flag or config entry gates Hermes pairing on or off.

---

## Acceptance Criteria

- [ ] `hermes.py` module exists and is importable
- [ ] `hermes_adapter.connect(token)` returns a `HermesConnection` for a valid, unexpired token
- [ ] `hermes_adapter.connect(invalid_token)` raises `InvalidToken`
- [ ] `hermes_adapter.connect(expired_token)` raises `TokenExpired`
- [ ] `connection.readStatus()` returns a `MinerSnapshot` when `'observe'` is in scope
- [ ] `connection.readStatus()` raises `Unauthorized` when `'observe'` is not in scope
- [ ] `connection.appendSummary(summary)` appends a `hermes_summary` event to the event spine when `'summarize'` is in scope
- [ ] `connection.appendSummary(summary)` raises `Unauthorized` when `'summarize'` is not in scope
- [ ] `user_message` events are never included in Hermes-readable event streams
- [ ] `POST /hermes/pair` issues a token with correct scope and expiry
- [ ] A smoke test script (`scripts/hermes_adapter_smoke.sh`) exercises the full adapter flow and prints pass/fail
- [ ] The `Agent` tab in the command-center surface can display Hermes connection state and last summary
- [ ] The `Inbox` tab shows Hermes summaries alongside other operational receipts

---

## Failure Handling

| Condition | Adapter Behavior |
|---|---|
| Malformed token | Raise `InvalidToken`; do not attempt to call daemon |
| Expired token | Raise `TokenExpired`; do not issue any daemon call |
| Missing `'observe'` | Raise `Unauthorized` on `readStatus()` |
| Missing `'summarize'` | Raise `Unauthorized` on `appendSummary()` |
| Spine write fails | Raise `EventAppendFailed`; Hermes receives an error receipt |
| Daemon offline | Raise `AdapterUnavailable`; Hermes retries with backoff |
| Hermes requests `user_message` | Return empty list; do not surface an error |

---

## Non-Goals

- Direct miner control through Hermes (`control` scope) — deferred to milestone 1b or later
- Payout-target mutation — explicitly out of scope for milestone 1
- Hermes acting as a general inbox client — Hermes receives only `hermes_summary` output, not arbitrary user messages
- Remote internet-facing Hermes connections — milestone 1 Hermes pairing is LAN-only, matching the daemon's LAN-only constraint

---

## Relationship to Other Artifacts

| Document | Role |
|---|---|
| `references/hermes-adapter.md` | Adapter interface contract this spec implements |
| `references/event-spine.md` | Spine event schema, including `hermes_summary` |
| `references/inbox-contract.md` | `PrincipalId` contract and pairing record shape |
| `plans/2026-03-19-build-zend-home-command-center.md` | Master ExecPlan; this slice is a sub-slice of its Hermes tasks |
| `specs/2026-03-19-zend-product-spec.md` | Durable product decision: "Zend owns the canonical gateway contract. Hermes enters through a Zend adapter." |
| `DESIGN.md` | Visual and interaction vocabulary for the Agent tab and Inbox Hermes summaries |
