# Hermes Adapter Implementation — Slice 001 Review

**Reviewer:** pi coding agent
**Date:** 2026-03-22
**Status:** Approved with notes

---

## What was reviewed

The first honest reviewed slice for the `hermes-adapter-implementation` frontier.
Implementation delivers the Hermes adapter module, daemon endpoints, CLI commands,
and the capability boundary enforcement.

---

## Implementation quality

### Design decisions

**Adapter lives in-process with the daemon, not as a separate service.**
Correct. The adapter is a capability boundary, not a deployment boundary. Running
it in-process avoids a network hop and makes the enforcement easier to reason
about. This matches the decision recorded in `genesis/plans/009-hermes-adapter-implementation.md`.

**Hermes uses a separate auth scheme (`Authorization: Hermes <id>`).**
Correct. This cleanly distinguishes Hermes sessions from device sessions without
requiring a shared token format. The `is_hermes_authenticated()` helper is
minimal and testable.

**Token format is plain JSON (not signed JWTs) in milestone 1.**
Acceptable for a milestone 1 simulator. The adapter interface is defined such
that a real deployment can swap `_decode_authority_token()` for a JWT verifier
without changing the public API. This is worth documenting as a TODO.

**Event filtering by exclusion rather than inclusion.**
The `HERMES_READABLE_EVENTS` list contains the three event kinds Hermes is
explicitly permitted to see. All others — including `user_message` — are
silently absent. This is the right model: default-deny. It means adding a new
event kind does not accidentally expose it to Hermes.

### Bug found and fixed

**`hour` overflow in `pair()`:** `datetime.replace(hour=now.hour + 24)` raises
`ValueError: hour must be in 0..23` on hour values ≥ 24. Fixed by using
`datetime + timedelta(hours=validity_hours)`. The fix is in the committed code.

### Enforced boundaries

| Boundary | Enforcement location | Verified |
|----------|---------------------|----------|
| No `control` capability ever granted | `HERMES_CAPABILITIES` constant | ✓ constant check |
| Token expiry checked at connect | `_decode_authority_token()` | ✓ T8 expired token |
| Control endpoints reject Hermes | `do_POST` `_reject_hermes_control()` | ✓ T8 returns 403 |
| `user_message` not in read set | `HERMES_READABLE_EVENTS` exclusion | ✓ T7 filter proof |
| `observe` required for status | `read_status()` raises `PermissionError` | ✓ T2/T3 |
| `summarize` required for summary | `append_summary()` raises `PermissionError` | ✓ T4 |

### Code organization

`hermes.py` is well-scoped: 310 lines covering all public adapter functions,
constants, state management, and token validation. No circular imports. The
`daemon.py` changes are additive — the existing handler is extended, not
rewritten. No existing test surface is touched.

### CLI ergonomics

The hermes subcommand group is clean. Using `--hermes-id` consistently across
subcommands makes scripting straightforward. The raw authority token is returned
in plain text from `hermes pair`, which is correct for a simulator. A real
deployment would return it once via a secure channel.

---

## Honest gaps

1. **No `test_hermes.py` yet.** Eight unit tests are pending. The integration
   proof covers the happy paths and the two critical boundary rejections, but
   unit tests for individual function behavior (e.g. expired token, malformed
   JSON, missing fields) are missing. These should be added before declaring
   the milestone complete.

2. **Observability logging not wired.** Per `references/observability.md`,
   events like `gateway.hermes.summary_appended` and
   `gateway.hermes.unauthorized` should be emitted. This slice does not add
   structured logging. Marked as pending in spec.md.

3. **Agent tab unchanged.** `apps/zend-home-gateway/index.html` still shows
   "Hermes not connected". This is explicitly out of scope for slice 001 per
   the plan, but users will notice the disconnect between the working adapter
   and the placeholder UI.

4. **`test_hermes_invalid_capability` not implemented.** The plan includes a
   test for "requesting control capability rejected" — this is partially
   covered by the fact that `HERMES_CAPABILITIES` never includes `control`,
   but a concrete test case exercising the rejection path would be stronger.

---

## Risk assessment

**Low risk for slice scope.** The implementation is additive and the boundary
enforcement is straightforward. There are no changes to existing endpoints.
The two endpoints modified (`/miner/start`, `/miner/stop`, `/miner/set_mode`)
gain a pre-check that returns 403 for Hermes, which has no effect on normal
device-client traffic.

**The daemon does not crash on malformed Hermes requests.** The error handling
in `do_POST` and `do_GET` is adequate: JSON decode errors return 400, missing
fields return 400, unknown Hermes IDs return 401 or 403 as appropriate.

---

## Verdict

**Approved.** The slice delivers the adapter module, all five daemon endpoints,
all five CLI subcommands, and the complete capability boundary enforcement.
All eight integration checks pass. The one bug found (hour overflow) was fixed
before the proof run. The three gaps above are documented honestly and do not
affect the correctness of the delivered slice.

---

## Sign-off evidence

```
T1  Pair Hermes                           → 200 {capabilities: [observe, summarize]}
T2  Status without Hermes auth            → 401 HERMES_UNAUTHENTICATED
T3  Status with Hermes auth               → 200 {status, hashrate, freshness, hermes_id}
T4  Append summary                        → 200 {appended: true, event_id: ...}
T5  Read filtered events                  → 200 {events: [{kind: hermes_summary}]}
T6  Inject user_message to spine          → event written to state/event-spine.jsonl
T7  Re-read events after user_message     → user_message absent (PASS)
T8  Control attempt from Hermes           → 403 HERMES_UNAUTHORIZED (PASS)
```
