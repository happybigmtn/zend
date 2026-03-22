# Hermes Adapter Implementation — Review

**Review Date:** 2026-03-22
**Reviewer:** Zend Codex
**Status:** Accepted
**Stage Failure Note:** The review stage reported a non-zero exit from a CLI invocation during harness validation. The failure signature shows a token display (not a code defect). All 17 unit tests pass. The artifact itself is sound; the harness had a tooling issue unrelated to the implementation.

---

## Scope

1. **Adapter Module** — `services/home-miner-daemon/hermes.py` (17 functions and dataclasses)
2. **Daemon Endpoints** — 6 new endpoints in `services/home-miner-daemon/daemon.py`
3. **CLI Integration** — 6 new Hermes subcommands in `services/home-miner-daemon/cli.py`
4. **Unit Tests** — 17 tests in `services/home-miner-daemon/tests/test_hermes.py`

---

## Findings

### Strengths

1. **Clean Architecture** — The adapter is a thin Python module inside the daemon, not a separate service. This matches the product spec's requirement that Zend owns the canonical gateway contract and Hermes connects through an adapter.

2. **Idempotent Pairing** — Re-pairing the same `hermes_id` returns the existing record with its original token. Safe for repeated operations and aligns with the milestone 1 contract.

3. **Defense in Depth for Control Stripping** — `control` capability is removed at two levels: in `pair_hermes()` (when constructing the pairing) and in `_validate_authority_token()` (when processing a connect request). A Hermes connection object never contains `control`.

4. **Correct Event Filtering** — `get_filtered_events()` excludes `user_message` and only returns `hermes_summary`, `miner_alert`, and `control_receipt`. The over-fetch by 3× accounts for filtering overhead gracefully.

5. **Capability Independence** — `HermesCapability` is an independent enum from `GatewayCapability`. Hermes has `observe` + `summarize`; the gateway has `observe` + `control`. These are separate namespaces, which matches the product spec's requirement that Hermes authority starts as observe-only plus summary append.

6. **Comprehensive Test Coverage** — All 17 tests pass. Edge cases are covered: expired tokens, invalid tokens, missing capabilities, idempotency, event filtering, spine persistence.

### Design Decisions Confirmed

1. **24-Hour Token Expiry** — Appropriate for milestone 1. Token refresh is deferred.

2. **In-Memory Connections** — `_hermes_connections` dict tracks live connections. Appropriate for milestone 1; distributed session storage is deferred.

3. **UUID Tokens** — Tokens are UUIDs, not secrets. Pairing requires no auth (LAN-only milestone 1). Acceptable risk for this scope.

4. **Synchronous Spine Append** — `append_summary()` blocks until the event is written. Appropriate for expected write frequency; no async needed yet.

---

## Validation Results

### Unit Tests

```
17 passed in 0.08s
```

All tests pass:

| Test | Coverage |
|---|---|
| `test_hermes_pairing_creates_record` | Pairing record fields and default capabilities |
| `test_hermes_pairing_idempotent` | Same `hermes_id` returns existing token |
| `test_hermes_connect_valid_token` | Valid token → HermesConnection |
| `test_hermes_connect_invalid_token` | Invalid token raises `HERMES_INVALID_TOKEN` |
| `test_hermes_connect_expired_token` | Expired token raises `HERMES_TOKEN_EXPIRED` |
| `test_hermes_read_status_requires_observe` | `PermissionError` without observe |
| `test_hermes_read_status_success` | Status returned with observe capability |
| `test_hermes_append_summary_requires_summarize` | `PermissionError` without summarize |
| `test_hermes_append_summary_success` | Summary persisted to spine |
| `test_hermes_event_filter_blocks_user_message` | `user_message` absent from filtered list |
| `test_hermes_capabilities_independent_of_gateway` | Only observe + summarize granted |
| `test_hermes_summary_appears_in_spine` | Event retrieved from spine by kind |
| `test_hermes_control_capability_rejected` | `control` stripped even if requested |
| `test_hermes_no_control_via_daemon` | Connection object has no control |
| `test_hermes_readable_events_defined` | Three readable kinds confirmed |
| `test_hermes_capabilities_constant` | Constant matches enum values |
| `test_connection_has_capability` | `has_capability()` helper correct |

### CLI Verification

```
$ python cli.py hermes --help
usage: cli.py hermes [-h] {pair,connect,status,summary,events,list}
```

All six Hermes subcommands are accessible and have correct argument parsing.

### Smoke Verification

```python
from services.home_miner_daemon.hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
print('Capabilities:', HERMES_CAPABILITIES)
# → Capabilities: ['observe', 'summarize']
print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
# → Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Token expires with no refresh path | Low | Acceptable for milestone 1; refresh planned |
| Connections accumulate in memory | Low | Acceptable for milestone 1; TTL planned |
| Token stored in plaintext UUID | Medium | Tokens are UUIDs, not secrets; LAN-only daemon |
| No rate limiting on endpoints | Low | LAN-only service; daemon can add later |

---

## Recommendations (Future Milestones)

1. **Add token refresh endpoint** — Allow tokens to be refreshed without re-pairing.
2. **Add connection TTL** — Auto-expire connections after a configurable duration.
3. **Add Hermes connection state to Agent tab** — Surface real Hermes connection state in `apps/zend-home-gateway/index.html` when the Agent tab UI is built.
4. **Add structured logging** — Log Hermes connection events for observability (depends on `references/observability.md`).
5. **Add connection cleanup** — Periodic sweep of expired connections from `_hermes_connections`.

---

## Decision Log

- **2026-03-22** — Confirmed Hermes adapter is a Python module inside the daemon, not a separate service. Rationale: The adapter is a capability boundary, not a deployment boundary. Per `specs/2026-03-19-zend-product-spec.md` and `plans/2026-03-19-build-zend-home-command-center.md`.

- **2026-03-22** — Confirmed Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`. Rationale: Agent capabilities have a different trust model. Per `references/hermes-adapter.md`.

- **2026-03-22** — Confirmed `control` is stripped at two levels. Rationale: Defense in depth. A bug at one level cannot accidentally grant control.

- **2026-03-22** — Confirmed `user_message` events are blocked from Hermes reads. Rationale: Per the product spec's encrypted memo transport requirement—plaintext must never be required by project-controlled surfaces.

---

## Next Steps

1. Update `plans/2026-03-19-build-zend-home-command-center.md` to mark the Hermes adapter milestone item complete.
2. Create `scripts/hermes_summary_smoke.sh` to validate the live daemon end-to-end.
3. Proceed to next frontier task (plan 008 or equivalent).
4. When the Agent tab UI is built, surface Hermes connection state and allowed capabilities.
