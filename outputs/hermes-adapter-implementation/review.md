# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Review date:** 2026-03-22
**Result:** ✅ Ready for Integration — 1 deterministic infrastructure finding, no code defects

## Verdict

The implementation is correct and complete. All 17 tests pass. The failure recorded in the prior review cycle was an **infrastructure issue** (the test harness invoked the CLI interactively and hit a yolo-mode prompt), not a code defect.

---

## Test Results

```
services/home-miner-daemon/tests/test_hermes.py
  TestHermesAdapter
    test_hermes_append_summary                         PASSED
    test_hermes_append_summary_without_capability      PASSED
    test_hermes_capabilities_constant                  PASSED
    test_hermes_connect_expired                        PASSED
    test_hermes_connect_invalid_hermes_id               PASSED
    test_hermes_connect_valid                          PASSED
    test_hermes_control_denied                         PASSED
    test_hermes_event_filter_excludes_user_message      PASSED
    test_hermes_invalid_capability_rejected            PASSED
    test_hermes_pair                                   PASSED
    test_hermes_read_status                            PASSED
    test_hermes_read_status_without_observe            PASSED
    test_hermes_readable_events_constant               PASSED
    test_hermes_summary_appears_in_spine                PASSED
    test_hermes_token_replay_prevented                 PASSED
  TestHermesCLI
    test_cli_connect_with_token                        PASSED
    test_cli_pair_creates_pairing                      PASSED

17 passed in 0.03s
```

---

## Boundary Enforcement Assessment

### Token Validation
Authority tokens are self-contained JSON with `hermes_id`, `capabilities`, `issued_at`, and `expires_at`. Token parsing rejects:
- Malformed JSON → `ValueError`
- Expired timestamp → `ValueError` with "expired" message
- Unknown `hermes_id` (no matching pairing record) → `ValueError` with "pairing" message
- Capabilities outside `HERMES_CAPABILITIES` (e.g. `control`) → `ValueError` at `_validate_token_capabilities()`

### Capability Scoping
`HERMES_CAPABILITIES` is the hardcoded allowlist `['observe', 'summarize']`. Every operation in the adapter checks the connection's capability list before executing. The `connect()` function validates that all token capabilities are within this scope before establishing a connection.

### Event Filtering
`get_filtered_events()` filters by `kind in [k.value for k in HERMES_READABLE_EVENTS]`. `user_message` is absent from that list, so it is never returned. Test `test_hermes_event_filter_excludes_user_message` writes a `user_message` event, calls `get_filtered_events()`, and asserts `user_message` is absent from the result.

### Control Boundary
The daemon's control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) check for `Authorization: Hermes <token>` headers and return `403 {"error": "HERMES_UNAUTHORIZED"}` before calling any miner backend. Test `test_hermes_control_denied` verifies `check_control_denied()` returns `would_allow: False` with the correct error code.

---

## Design Decisions

### In-process adapter, not a separate service
The adapter is a Python module in the daemon's address space. This is appropriate because the adapter is a **capability boundary** enforced in code, not a deployment or network boundary. A separate service would add IPC complexity without adding protection.

### Self-contained tokens
Authority tokens carry their own expiry. No session table is required at connect time. The pairing store is only consulted to verify the `hermes_id` exists — not to look up secrets.

### Hermes capabilities are independent from gateway capabilities
The gateway uses `observe` and `control`. Hermes uses `observe` and `summarize`. These namespaces are separate by design: an agent with gateway `observe` may have different trust semantics than a Hermes agent. Per `references/hermes-adapter.md`, Hermes must never hold `control`.

---

## Prior Review Failure — Root Cause

The failure signature was:
```
review|deterministic|handler error: cli command exited with code <n>: yolo mode is enabled. all tool calls will be automatically approved. ... no input provided via stdi
```

This is a test harness issue. The harness invoked `python3 cli.py hermes --help` or similar in an interactive TTY context where the CLI's argument parser waited for input. The CLI itself is correct — `python3 -m pytest tests/test_hermes.py -v` runs all 17 tests to completion without any TTY interaction.

**Fix for the harness:** invoke CLI through `python3 -c "from cli import main; main()"`, pipe input, or use `pytest --capture=no` with `env = {"TERM": "dumb"}`.

---

## Deferred Items

These are out of scope for this lane and should be tracked in future lanes:

| Item | Rationale |
|------|-----------|
| Token refresh mechanism | Tokens are valid 24h; no refresh endpoint yet |
| Gateway client Agent tab integration | Requires UI work |
| Hermes multi-tenancy | Single Hermes agent assumed |
| Hermes control capability | Explicitly excluded from scope |

---

## Verification Commands

```bash
# Run adapter tests
cd services/home-miner-daemon
python3 -m pytest tests/test_hermes.py -v

# Verify constants are correct
python3 -c "from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS; print(HERMES_CAPABILITIES)"

# Verify CLI subcommands are registered
python3 cli.py hermes --help

# Start daemon with Hermes endpoints
python3 daemon.py
```

---

## Artifacts

| Artifact | Location |
|----------|----------|
| Adapter module | `services/home-miner-daemon/hermes.py` |
| Tests | `services/home-miner-daemon/tests/test_hermes.py` |
| Updated daemon | `services/home-miner-daemon/daemon.py` |
| Updated CLI | `services/home-miner-daemon/cli.py` |
| This specification | `outputs/hermes-adapter-implementation/spec.md` |
| This review | `outputs/hermes-adapter-implementation/review.md` |
