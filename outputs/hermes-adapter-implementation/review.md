# Hermes Adapter Implementation — Review

Status: Approved
Date: 2026-03-22

## Verdict

**Approved.** All 6 required tasks from the plan were completed and verified.

## Evidence

### Task 1: Create hermes.py adapter module ✅

- `services/home-miner-daemon/hermes.py` — 11826 bytes, clean module
- Exports: `HermesConnection`, `HERMES_CAPABILITIES`, `HERMES_READABLE_EVENTS`, `HERMES_WRITABLE_EVENTS`, `CONTROL_PATHS`
- Functions: `connect`, `connect_from_pairing`, `pair_hermes`, `read_status`, `append_summary`, `get_filtered_events`, `is_control_path`

### Task 2: Implement HermesConnection with authority token validation ✅

- `connect()` parses compact JSON authority tokens
- Validates: `hermes_id`, `principal_id` presence; expiration via `expires_at`; capability allowlist (`observe`, `summarize` only)
- Rejects `control` capability with named error `HERMES_UNAUTHORIZED_CAPABILITY`
- Rejects expired tokens with `HERMES_TOKEN_EXPIRED`
- Rejects malformed JSON with `HERMES_AUTH_INVALID`

Evidence:
```
$ curl -s -X POST .../hermes/connect -d '{"authority_token":"..."}'
{"connected": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

$ curl -s .../hermes/connect -d '{"authority_token":"{\"capabilities\":[\"control\"]}"}'
{"error": "HERMES_UNAUTHORIZED_CAPABILITY", "message": "'control' is not in the Hermes allowlist..."}

$ curl -s .../hermes/connect -d '{"authority_token":"{\"expires_at\":\"2020-01-01T00:00:00Z\"}"}'
{"error": "HERMES_UNAUTHORIZED", "message": "HERMES_TOKEN_EXPIRED"}
```

### Task 3: Implement readStatus through adapter ✅

- `read_status(connection)` checks `'observe'` capability, delegates to `daemon.miner.get_snapshot()`
- Rejects without observe with `PermissionError("observe capability required for read_status")`

Evidence:
```
$ curl -s .../hermes/status -H "Authorization: Hermes hermes-001"
{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}

$ curl -s .../hermes/status   # no auth
{"error": "HERMES_UNAUTHORIZED", "message": "Missing or invalid Hermes Authorization header"}
```

### Task 4: Implement appendSummary through adapter ✅

- `append_summary(connection, text, scope)` checks `'summarize'`, writes `hermes_summary` to spine
- Validates non-empty text; strips whitespace
- Returns `{"appended": true, "event_id": "...", "kind": "hermes_summary", "created_at": "..."}`

Evidence:
```
$ curl -s -X POST .../hermes/summary -H "Authorization: Hermes hermes-001" \
  -d '{"summary_text": "Miner running normally", "authority_scope": ["observe"]}'
{"appended": true, "event_id": "d2ebda70-...", "kind": "hermes_summary", "created_at": "2026-03-22T19:44:44+00:00"}
```

### Task 5: Event filtering (block user_message for Hermes) ✅

- `get_filtered_events()` only returns `hermes_summary`, `miner_alert`, `control_receipt`
- `user_message` and pairing events are excluded
- Verified by injecting a `user_message` event directly into the spine and confirming it does not appear in Hermes-filtered output

Evidence:
```
# Full spine contains user_message
$ python3 -c "append user_message event"
$ python3 -c "spine.get_events()" → [user_message, hermes_summary, ...]

# Hermes filtered events do NOT contain user_message
$ curl -s .../hermes/events -H "Authorization: Hermes hermes-001"
{"events": [...], "count": 5}   # only hermes_summary entries, no user_message
```

### Task 6: Add Hermes pairing endpoint to daemon ✅

- `POST /hermes/pair` — creates/updates pairing with 30-day token expiry
- `POST /hermes/connect` — accepts token or `hermes_id` (pairing-based)
- `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events` — auth-gated
- Control paths always return 403 for Hermes (even if Authorization header is present)

Evidence:
```
$ curl -s -X POST .../hermes/pair -d '{"hermes_id":"hermes-001","device_name":"hermes-agent"}'
{"paired": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

$ curl -s -X POST .../miner/start -H "Authorization: Hermes hermes-001"
{"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands..."}

$ curl -s -X POST .../miner/set_mode -H "Authorization: Hermes hermes-001"
{"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands..."}
```

## Test Results

```
23 passed in 0.04s
```

Test file: `services/home-miner-daemon/tests/test_hermes.py`

## Open Tasks (Not in Required Scope for This Slice)

- [ ] Update CLI with Hermes subcommands — ✅ DONE (part of this slice)
- [ ] Update gateway client Agent tab with real connection state — deferred (gateway client not yet implemented in this repo)
- [ ] Write tests for adapter boundary enforcement — ✅ DONE (23 tests)

## Decisions Made

1. **Adapter is in-process, not a separate service.** Rationale: it is a capability boundary, not a deployment boundary. In-process avoids network hop complexity for phase 1.

2. **Pairing token expires 30 days from creation.** Rationale: long enough for normal operation, short enough to force re-pairing if Hermes device is lost.

3. **`/hermes/connect` accepts `hermes_id` field in body** (in addition to authority token). Rationale: enables pairing-then-connect without the CLI needing to construct a token.

4. **Control paths return 403 unconditionally for Hermes.** Rationale: simplifies the boundary enforcement — no capability lookup needed for `/miner/*`; Hermes never gets control regardless of what token it presents.

## Notes

- The `user_message` filtering is implemented by name-based exclusion (`allowed_kinds = {e.value for e in HERMES_READABLE_EVENTS}`). This is correct for milestone 1 since `EventKind` is an enum. If new event kinds are added, they must be explicitly added to `HERMES_READABLE_EVENTS` to be accessible to Hermes.
- The daemon's in-memory `_hermes_connections` registry means sessions reset on daemon restart. This is acceptable for milestone 1. Persistent sessions would require a store-backed session mechanism.
- All error messages use `HERMES_*` prefixes matching the error taxonomy in `references/error-taxonomy.md`.
