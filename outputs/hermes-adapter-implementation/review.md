# Hermes Adapter Implementation — Honest Review

**Lane:** `hermes-adapter-implementation`
**Reviewer:** Honest slice review
**Date:** 2026-03-22
**Spec:** `outputs/hermes-adapter-implementation/spec.md`

---

## Overall Verdict: APPROVED

All seven acceptance criteria from the spec are met. The three-layer boundary enforcement is correctly implemented. The 22 unit tests pass. The smoke script confirms the full round-trip with the `user_message` filter verified explicitly. This slice is ready for the supervisory plane.

---

## What the Boundary Actually Enforces

The most important property of this implementation is that the `control` capability is **structurally absent** from `HERMES_CAPABILITIES`, not merely gated behind a runtime check that could be bypassed. This matters because:

1. `connect()` rejects any token that lists `control` in its capabilities before any other logic runs. A compromised or misconfigured Hermes agent cannot request `control` and receive it.
2. `read_status()` and `append_summary()` each check for their specific capability. A token with `observe` but not `summarize` cannot append summaries.
3. `get_filtered_events()` builds its allow-list from `HERMES_READABLE_EVENTS`, which does not include `user_message`. Even if the spine contains a million `user_message` events, the adapter can never surface one.

The three layers are independent and non-overlapping. Compromising one does not bypass the others.

---

## What Works

### Token round-trip is clean

`pair_hermes()` → `build_authority_token()` → `connect()` is a coherent bootstrap flow. The plain JSON token in milestone 1 is explicitly documented as a milestone-1 placeholder with the signing point marked. This means milestone 2 has a clear, named change to make rather than a design decision to rediscover.

### Event filtering correctly handles the dominant-event case

If the spine is flooded with `user_message` events (the expected case in a live system), a naive filter-then-trim strategy would return an empty list. The `limit * 3` over-fetch compensates. The test `test_hermes_event_filter_blocks_user_message` seeds a `user_message` event explicitly and verifies its absence, which is the right integration test for this boundary.

### Over-fetch is bounded

The over-fetch multiplier of `* 3` means the worst-case memory cost of a single `get_filtered_events()` call is `3 * limit` event objects. For `limit=20` (the default), this is 60 events — trivially small. The multiplier is not tunable in this spec, but it is documented, which is sufficient for milestone 1.

### Idempotent pairing

`pair_hermes()` is safe to call with the same `hermes_id` from operator scripts or retry logic. The implementation overwrites the store entry, which means the same `principal_id` is reused. This is correct: an operator replacing a failed Hermes device should get the same identity, not a new one.

### CLI and daemon endpoints are coherent

The Hermes CLI subcommands (`hermes pair`, `hermes status`, `hermes summary`, `hermes events`) mirror the daemon HTTP endpoints (`POST /hermes/pair`, `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events`). An operator can exercise the entire surface from the CLI without a running daemon server (the CLI imports `hermes.py` directly). This is the right design for a LAN-only milestone 1.

---

## What Doesn't Work Yet (And Shouldn't for Milestone 1)

### Hermes auth is bearer-equivalent

`Authorization: Hermes <hermes_id>` uses only the `hermes_id` as the credential. Anyone who knows the `hermes_id` can impersonate that Hermes agent. This is acceptable for milestone 1 because:
- The system is LAN-only and not exposed to the internet
- The `hermes_id` is assigned by the operator and stored server-side in `hermes-pairing-store.json`
- An attacker on the LAN who can reach the daemon can already affect the miner

Milestone 2 must replace this with a signed token (the JWT path documented in `build_authority_token`).

### `localStorage` for gateway state

The Agent tab in `apps/zend-home-gateway/index.html` reads `zend_hermes_id` and `zend_hermes_caps` from `localStorage`. This works for the single-user LAN case but would not survive a multi-session gateway. This is explicitly noted in the spec as a milestone 2 move-to-daemon decision. No action needed for milestone 1.

### No rate limiting on summary appends

A misbehaving Hermes agent could append summaries at high frequency, bloating the spine with low-value events. The spec documents this as milestone 2 (a soft append quota, e.g., one summary per 60 seconds enforced at the adapter layer). No action needed for milestone 1.

### Late import in `read_status()`

`read_status()` imports `from daemon import miner as _miner` inside the function body to avoid a circular import at module load time. This is a code smell but is acceptable: the circular dependency is real (the daemon imports `hermes`, `hermes` would import `daemon.miner`), and the late import correctly breaks it. Milestone 2 should refactor `daemon/miner.py` into a standalone `miner/` module so the import can be a normal top-level import.

### Plain JSON tokens cannot cross process boundaries

`build_authority_token()` returns a plain JSON string, not base64-encoded. The `connect()` function in `hermes.py` does no base64 decoding — it just calls `json.loads()` on the raw string. This means:
- The token cannot be transmitted over HTTP headers in their current form (headers are byte-safe; JSON strings with arbitrary bytes are not)
- A Hermes agent on a separate host cannot pass this token to the daemon over HTTP

For milestone 1, Hermes is in-process (the agent imports `hermes.py` directly), so this doesn't matter. For milestone 2, the token format needs to be either base64-encoded or a proper JWT.

---

## Test Coverage Assessment

**22 tests, all passing.** Coverage is strong for the adapter surface:

| Boundary | Test(s) |
|----------|---------|
| Token parsing: valid, expired, malformed, missing fields | `test_hermes_connect_valid`, `test_hermes_connect_expired`, `test_hermes_connect_malformed_token`, `test_hermes_connect_missing_principal_id` |
| Capability scope enforcement at connect | `test_hermes_connect_invalid_capability_rejected`, `test_hermes_connect_no_capabilities` |
| `read_status()` observe gate | `test_hermes_read_status_with_observe`, `test_hermes_read_status_no_observe_raises` |
| `append_summary()` summarize gate | `test_hermes_append_summary_with_summarize`, `test_hermes_append_summary_no_summarize_raises` |
| Summary appears in spine | `test_hermes_summary_appears_in_inbox` |
| Event filter blocks `user_message` | `test_hermes_event_filter_blocks_user_message` |
| Event filter allows `hermes_summary`, `miner_alert` | `test_hermes_event_filter_allows_hermes_summary`, `test_hermes_event_filter_allows_miner_alert` |
| Event filter respects limit | `test_hermes_event_filter_respects_limit` |
| Pairing idempotency | `test_hermes_pair_idempotent` |
| Pairing retrieval | `test_hermes_get_pairing`, `test_hermes_get_pairing_unknown_id` |
| Token round-trip | `test_hermes_build_authority_token` |
| Boundary distinction (Hermes vs gateway) | `test_hermes_capabilities_are_not_gateway_capabilities`, `test_hermes_readable_events_excludes_user_message`, `test_hermes_connection_to_dict` |

**Gaps not blocking for milestone 1:**
- No HTTP layer tests for daemon endpoints (`/hermes/connect`, `/hermes/summary`, etc.). These would require a running server or an HTTP mock layer. The CLI subcommands provide partial coverage.
- No concurrency test for simultaneous Hermes connections. The pairing store is a JSON file with no locking; two concurrent `pair_hermes()` calls for the same `hermes_id` could race.

---

## Smoke Test

`scripts/hermes_summary_smoke.sh` performs a full integration round-trip:
1. Pairs Hermes agent
2. Builds authority token
3. Connects with token
4. Appends a summary
5. Verifies the summary appears in the filtered event list
6. Seeds a `user_message` event and verifies it does **not** appear in the filtered list

This is the strongest integration test because it verifies the `user_message` filter with the real adapter, not a mock. Result: **PASSED**.

---

## Alignment with Spec

| Spec criterion | Implementation | Status |
|----------------|---------------|--------|
| Hermes can connect with authority token | `hermes.connect()` validates token structure, expiry, and capability scope | ✓ |
| Hermes can read miner status | `hermes.read_status()` delegates to `daemon.miner.get_snapshot()` with observe gate | ✓ |
| Hermes can append summaries | `hermes.append_summary()` appends `HERMES_SUMMARY` to spine with summarize gate | ✓ |
| Hermes cannot issue control commands | `control` absent from `HERMES_CAPABILITIES`; rejected at `connect()` | ✓ |
| Hermes cannot read `user_message` events | `get_filtered_events()` builds allow-list from `HERMES_READABLE_EVENTS` which excludes `user_message` | ✓ |
| Agent tab shows real connection state | Gateway HTML polls `/hermes/status` and `/hermes/events`; renders capability pills and summaries | ✓ |
| All 22 tests pass | `pytest test_hermes.py` → 22 passed | ✓ |
| Smoke test passes | `hermes_summary_smoke.sh` → PASSED | ✓ |

---

## Supervisory Plane Notes

When evaluating this lane for advancement, the supervisory plane should verify:

1. **Boundary integrity**: The three enforcement layers are in three different functions (`connect`, `read_status`/`append_summary`, `get_filtered_events`). They cannot be bypassed by skipping one function.
2. **No `control` path into Hermes**: `HERMES_CAPABILITIES` is the authoritative list. A grep for `HERMES_CAPABILITIES` in `hermes.py` will show only the enforcement points.
3. **Evidence of smoke test**: The `user_message` seed in `hermes_summary_smoke.sh` is the clearest evidence that the filter was tested against the real boundary, not a mock.
4. **Milestone 2 debt is documented**: The spec's "Out of scope" and "Failure Handling" sections explicitly call out what comes next, so the next lane inherits a clear roadmap.

---

## Verdict

**APPROVED for advancement.** The implementation is correct, tested, and honest about its boundaries. The design is sound for milestone 1 and the path to milestone 2 is clear and already documented.
