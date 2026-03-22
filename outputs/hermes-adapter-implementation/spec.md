# Hermes Adapter — Capability Spec

**Spec type:** Capability Spec
**Lane:** `hermes-adapter-implementation`
**Status:** Complete (milestone 1)
**Date:** 2026-03-22

---

## Purpose / User-Visible Outcome

After this spec lands, an external AI agent (Hermes) can authenticate to the Zend daemon, observe miner status, and append summarization events to the event spine. A human operator can verify the boundary by running `hermes status` and `hermes summary` commands from the CLI and seeing the Agent tab in the gateway HTML reflect live connection state.

What Hermes **cannot** do is issue control commands or read `user_message` events — those capabilities are structurally absent, not merely gated behind a check.

---

## Whole-System Goal

Establish Hermes as a first-class, capability-scoped participant in the Fabro home-miner system alongside human operators. Hermes uses the same adapter surface as the gateway (observe, spine write) but with a narrower scope that matches the trust model for an external agent. This is the first step toward agent parity: agents and humans share primitives, but agents get a locked-down subset.

---

## Scope

### In scope

- Hermes authentication via authority token (plain JSON in milestone 1, JWT in production)
- `read_status()` through the adapter (requires `observe`)
- `append_summary()` through the adapter (requires `summarize`)
- Event filtering that blocks `user_message` at the adapter layer
- Hermes pairing lifecycle (`pair_hermes`, `get_hermes_pairing`)
- Hermes HTTP endpoints on the daemon (`/hermes/connect`, `/hermes/pair`, `/hermes/status`, `/hermes/summary`, `/hermes/events`)
- Hermes CLI subcommands (`hermes pair`, `hermes connect`, `hermes status`, `hermes summary`, `hermes events`)
- Agent tab in gateway HTML rendering real Hermes state

### Out of scope

- JWT signing (milestone 2)
- Rate limiting on summary appends (milestone 2)
- Hermes-to-Hermes multi-agent coordination
- Hermes daemon running as a separate process
- Cross-host Hermes authentication

---

## Current State

Before this spec: Hermes is an abstract reference in `references/hermes-adapter.md` with no implementation. The daemon has no Hermes endpoints. The CLI has no `hermes` subcommand. The gateway HTML shows a placeholder.

After this spec: Hermes has a working in-process adapter (`hermes.py`), daemon HTTP endpoints, CLI subcommands, 22 passing unit tests, and a gateway HTML tab with live polling.

---

## Architecture / Runtime Contract

```
  Hermes agent
       │
       ▼
  daemon HTTP server          HermesConnection
  POST /hermes/connect   ──▶  validate(token)  ──▶  HermesConnection
  GET  /hermes/status    ──▶  read_status(conn)  ──▶  miner snapshot
  POST /hermes/summary   ──▶  append_summary(conn, text)  ──▶  SpineEvent
  GET  /hermes/events    ──▶  get_filtered_events(conn)  ──▶  event list
       │
       ▼
  hermes.py adapter      ← 3-layer boundary enforcement:
  - connect(): reject any token requesting 'control'
  - read_status(): require 'observe'
  - append_summary(): require 'summarize'
  - get_filtered_events(): drop 'user_message' from result
       │
       ▼
  spine  (append_event, get_events)
```

### Key runtime contracts

**Capability set:** `HERMES_CAPABILITIES = ["observe", "summarize"]`
This is a constant. `control` is never added to this list and is rejected at `connect()` time.

**Readable events:** `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`
`user_message` is structurally absent from this list. No code path can return a `user_message` event through the adapter.

**Authority token (milestone 1):** plain JSON string returned by `build_authority_token()`. Format:
```json
{
  "principal_id": "<uuid>",
  "hermes_id": "<string>",
  "capabilities": ["observe", "summarize"],
  "expires_at": "ISO 8601",
  "signature": "milestone-1-placeholder"
}
```
Milestone 2 replaces the JSON blob with a signed JWT using a per-device JWK.

**Auth header scheme:** `Authorization: Hermes <hermes_id>` — bearer-equivalent in milestone 1 (the `hermes_id` alone is the credential). Separate from device `Authorization: Bearer <token>`.

**Event filtering:** `get_filtered_events()` over-fetches `limit * 3` events then trims to `limit`. This ensures the requested limit is met even when most events are filtered out (e.g., a spine dominated by `user_message`).

---

## Adoption Path

1. Operator pairs a Hermes agent: `python -m daemon.cli hermes pair --hermes-id <id>`
2. Operator copies the printed authority token to the Hermes agent's config
3. Hermes agent calls `POST /hermes/connect` with the token on first boot
4. Gateway Agent tab polls `GET /hermes/status` and `GET /hermes/events` and renders connection state and recent summaries
5. No changes required to the spine, miner simulator, or gateway control endpoints

---

## Acceptance Criteria

| Criterion | How to verify |
|-----------|---------------|
| Hermes can connect with a valid authority token | `hermes connect --token <json>` prints connection state |
| Hermes can read miner status | `hermes status --hermes-id <id>` returns a snapshot |
| Hermes can append a summary | `hermes summary --hermes-id <id> --text "..."` succeeds; summary appears in `hermes events` |
| Hermes cannot read `user_message` events | Seed a `user_message`, call `hermes events`, verify it is absent |
| Hermes cannot request `control` capability | Call `connect()` with `["observe", "control"]` token; expect `HERMES_INVALID_CAPABILITY` |
| Agent tab shows live Hermes state | Open gateway HTML, see capability pills and recent summaries |
| All 22 adapter unit tests pass | `python -m pytest services/home-miner-daemon/tests/test_hermes.py -v` |
| Smoke test passes | `bash scripts/hermes_summary_smoke.sh` prints `PASSED` |

---

## Failure Handling

| Failure mode | Adapter response |
|--------------|-----------------|
| Malformed token | `ValueError("HERMES_INVALID_TOKEN: ...")` |
| Expired token | `ValueError("HERMES_TOKEN_EXPIRED")` |
| Missing `principal_id` | `ValueError("HERMES_INVALID_TOKEN: missing principal_id")` |
| Missing `hermes_id` | `ValueError("HERMES_INVALID_TOKEN: missing hermes_id")` |
| `control` in token capabilities | `ValueError("HERMES_INVALID_CAPABILITY: 'control' is not in the Hermes scope ...")` |
| `read_status()` without `observe` | `PermissionError("HERMES_UNAUTHORIZED: observe capability required")` |
| `append_summary()` without `summarize` | `PermissionError("HERMES_UNAUTHORIZED: summarize capability required")` |
| Unknown `hermes_id` in pairing lookup | Returns `None` |

All failures are synchronous and return structured errors. No silent degradation.

---

## Idempotence Notes

- `pair_hermes(hermes_id, device_name)` overwrites any existing record for that `hermes_id`. Safe for retry scripts.
- `append_summary()` is append-only by spine contract. Repeating the same summary creates a new event.
- `connect()` validates per invocation; there is no persistent connection state beyond the returned `HermesConnection` dataclass.

---

## Decision Log

- **Decision:** Hermes adapter is an in-process Python module, not a separate HTTP service.
  **Rationale:** The adapter is a capability boundary, not a deployment boundary. A separate service would add a network hop and a new process to operate. In-process keeps the trust model simple for milestone 1.
  **Date:** 2026-03-22

- **Decision:** Hermes auth uses `Authorization: Hermes <hermes_id>` header, separate from device bearer auth.
  **Rationale:** The daemon needs to dispatch to different handlers based on auth scheme. A separate header scheme keeps the routing logic simple without adding a routing table.
  **Date:** 2026-03-22

- **Decision:** Plain JSON authority tokens in milestone 1, JWT in milestone 2.
  **Rationale:** Milestone 1 is LAN-only, single-user, in-process Hermes. Signing adds complexity (key distribution, JWKS endpoint) that is not justified yet. `build_authority_token()` documents the signing point clearly.
  **Date:** 2026-03-22

- **Decision:** Event filtering over-fetches then trims.
  **Rationale:** If the spine is dominated by `user_message` events, a naive `limit`-fetch followed by filter would return fewer than `limit` results. Over-fetching by `* 3` compensates for filtering while keeping the trim cheap.
  **Date:** 2026-03-22
