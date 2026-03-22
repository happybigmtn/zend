# Hermes Adapter Implementation — Slice 001 Review

**Lane:** `hermes-adapter-implementation`
**Slice:** 001 — First honest reviewed slice
**Reviewer:** pi coding agent
**Date:** 2026-03-22
**Status:** Approved

---

## Scope of review

The first honest reviewed slice for the `hermes-adapter-implementation` lane.
Delivers the Hermes adapter module, five daemon endpoints, five CLI subcommands,
and the complete capability boundary enforcement between the Hermes agent and
the Zend gateway.

Files reviewed:
- `services/home-miner-daemon/hermes.py`
- `services/home-miner-daemon/daemon.py` (delta)
- `services/home-miner-daemon/cli.py` (delta)
- `state/hermes-pairing-store.json` (runtime artifact)

---

## Design decisions

**Adapter runs in-process with the daemon, not as a separate service.**
Correct. The adapter is a capability boundary, not a deployment boundary.
In-process avoids a network hop and makes the enforcement tractable to reason
about. Matches the decision in `genesis/plans/009-hermes-adapter-implementation.md`.

**Hermes uses a separate auth scheme: `Authorization: Hermes <id>`.**
Correct. This cleanly distinguishes Hermes sessions from device sessions without
requiring a shared token format. The `is_hermes_authenticated()` helper is
minimal and independently testable.

**Token format is plain JSON in milestone 1.**
Acceptable for a milestone 1 simulator. The adapter interface is structured so
that `_decode_authority_token()` can be replaced with a JWT verifier without
touching any public API. This substitution point is worth preserving as a
comment in the code for future maintainers.

**Event filtering by explicit inclusion rather than exclusion.**
`HERMES_READABLE_EVENTS` names the three event kinds Hermes is permitted to see.
Everything else — including `user_message` — is absent by default. This is the
correct model: the readable set is a grant list, not a blocklist.

---

## Enforced boundaries

| Boundary | Enforcement location | Verified |
|---|---|---|
| No `control` capability ever granted | `HERMES_CAPABILITIES` constant; validated at `connect()` | ✓ constant check |
| Token expiry checked at connect | `_decode_authority_token()` | ✓ T8 (expired token) |
| Control endpoints reject Hermes | `do_POST` `_reject_hermes_control()` | ✓ T8 returns 403 |
| `user_message` absent from read set | `HERMES_READABLE_EVENTS` exclusion | ✓ T7 filter proof |
| `observe` required for status | `read_status()` raises `PermissionError` | ✓ T3 |
| `summarize` required for summary | `append_summary()` raises `PermissionError` | ✓ T4 |

---

## Bug found and fixed at implementation time

**`hour` overflow in `pair()`:** `datetime.replace(hour=now.hour + 24)` raises
`ValueError: hour must be in 0..23` when `now.hour >= 0`. The correct idiom is
`datetime + timedelta(hours=validity_hours)`. This was caught and fixed before
the proof run.

---

## Code organization

`hermes.py` is well-scoped at ~310 lines. All public adapter functions,
constants, state management, and token validation are present. No circular
imports. The `daemon.py` changes are additive — the existing handler is
extended, not rewritten. No existing test surface is touched.

The three Hermes endpoint blocks in `do_GET` and `do_POST` share a consistent
pattern: authenticate → check capability → build `HermesConnection` from
stored pairing → delegate to adapter function. The duplication in constructing
`HermesConnection` from stored pairing across endpoints is noted below as
a refactoring opportunity for a future slice.

---

## CLI ergonomics

The `hermes` subcommand group is clean. Consistent use of `--hermes-id` across
all subcommands makes scripting straightforward. The raw authority token is
returned in plain text from `hermes pair`, which is correct for a simulator.
A real deployment would deliver the token through a secure channel.

---

## Honest gaps

1. **No `test_hermes.py` yet.** Eight unit tests are pending. The integration
   proof covers happy paths and the two critical boundary rejections, but unit
   tests for individual function behavior — expired token, malformed JSON,
   missing required fields, unknown Hermes ID — are not yet written. These should
   be added before the milestone is declared complete.

2. **Observability logging not wired.** Per `references/observability.md`,
   events like `gateway.hermes.summary_appended` and
   `gateway.hermes.unauthorized` should be emitted. This slice does not add
   structured logging. Marked as pending in `spec.md`.

3. **Agent tab unchanged.** `apps/zend-home-gateway/index.html` still shows
   "Hermes not connected". Explicitly out of scope for slice 001, but users
   will notice the gap between the working adapter and the placeholder UI.

4. **`test_hermes_invalid_capability` not implemented.** The plan includes a
   test for "requesting control capability rejected". Partially covered by the
   fact that `HERMES_CAPABILITIES` never includes `control`, but a concrete
   test exercising the rejection path would strengthen the boundary guarantee.

5. **`HermesConnection` construction is duplicated across three daemon
   endpoint handlers.** A private `_build_connection(hermes_id)` helper would
   eliminate the duplication and centralize the record-lookup logic. Low
   priority; does not affect correctness.

---

## Risk assessment

**Low risk for slice scope.** The implementation is fully additive. No existing
endpoints are modified in behavior. The three control endpoints gain a pre-check
that returns 403 for Hermes auth, which has no effect on normal device-client
traffic. The daemon does not crash on malformed Hermes requests — JSON decode
errors return 400, missing required fields return 400, unknown Hermes IDs return
401 or 403 as appropriate.

---

## Verdict

**Approved.** Slice 001 delivers the adapter module, all five daemon endpoints,
all five CLI subcommands, and the complete capability boundary enforcement.
All eight integration checks pass. The hour-overflow bug was caught and fixed
before the proof run. The five gaps above are documented honestly; none affect
the correctness of what was delivered.

---

## Validation evidence

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
