# Documentation & Onboarding — Review

**Verdict:** CONDITIONAL PASS — plan is structurally sound but contains five
factual errors that would produce dishonest documentation if unaddressed.

**Lane:** documentation-and-onboarding
**Date:** 2026-03-22
**Reviewed against:** codebase at `8ec70ae` (HEAD of main)

## Summary

Plan 008 proposes five documentation artifacts (README rewrite, contributor
guide, operator quickstart, API reference, architecture doc). The milestone
structure is reasonable. The deliverables are the right ones.

The problem is accuracy. The plan was authored from the ExecPlan and spec
documents, not from reading the implementation. It references three HTTP
endpoints that don't exist, one environment variable that doesn't exist, an
auth model that doesn't match reality, a non-idempotent quickstart, and a
test suite that hasn't been written. Documentation built on these claims
would be worse than no documentation — it would actively mislead.

## Correctness Findings

### C1: Phantom Endpoints (BLOCKING)

Plan milestone 4 (API Reference) lists eight endpoints. Only five exist in
`services/home-miner-daemon/daemon.py`:

| Endpoint | Exists | Notes |
|----------|--------|-------|
| `GET /health` | yes | |
| `GET /status` | yes | |
| `GET /spine/events` | **no** | Events accessed via `cli.py events`, not HTTP |
| `GET /metrics` | **no** | No metrics endpoint in daemon |
| `POST /miner/start` | yes | |
| `POST /miner/stop` | yes | |
| `POST /miner/set_mode` | yes | |
| `POST /pairing/refresh` | **no** | Referenced as "from plan 006" but never built |

**Impact:** The API reference would document endpoints a user cannot call.
Curl examples would 404.

**Fix:** Remove the three phantom endpoints from the plan, or implement
them before documenting. The plan is documentation-only, so it should
document what exists.

### C2: Phantom Environment Variable (BLOCKING)

Plan milestone 3 (Operator Quickstart) says to document `ZEND_TOKEN_TTL_HOURS`.
This variable does not exist anywhere in the codebase. The token expiration
in `store.py:create_pairing_token()` is hardcoded to `datetime.now()` (zero
TTL) and never enforced.

The actual environment variable `ZEND_DAEMON_URL` (used by `cli.py` and
all scripts) is not mentioned in the plan.

**Fix:** Replace `ZEND_TOKEN_TTL_HOURS` with `ZEND_DAEMON_URL` in the
operator quickstart plan.

### C3: Auth Model Misrepresentation (BLOCKING)

Plan milestone 4 says to document "Authentication requirement (none,
observe, control)" per endpoint. This framing implies the daemon enforces
auth. It does not.

Reality: all five daemon endpoints are completely unauthenticated at the
HTTP level. Anyone who can reach the daemon's IP:port can start, stop, or
reconfigure the miner with a raw curl. Capability checks (`observe`,
`control`) exist only in `cli.py`, which is a convenience wrapper.

The LAN-only binding (`127.0.0.1` by default) is the actual security
boundary. When operators configure `ZEND_BIND_HOST` to a LAN interface,
every device on that LAN has full control. This is by design for
milestone 1, but the documentation must say so honestly.

**Fix:** Document the auth model as-is: "The daemon has no HTTP-level
authentication. Capability scoping is enforced by the CLI tools. The
security boundary is the network binding (LAN-only). Direct HTTP access
to the daemon bypasses capability checks."

### C4: Non-Idempotent Bootstrap (MINOR)

Plan milestone 1 quickstart command sequence:

    git clone <repo-url> && cd zend
    ./scripts/bootstrap_home_miner.sh

This works once. On second run, `bootstrap_home_miner.sh` calls
`cli.py bootstrap --device alice-phone`, which calls `pair_client()`,
which raises `ValueError("Device 'alice-phone' already paired")`.

The plan's validation criterion ("a reader can follow the README quickstart
from a fresh clone") is met on first run but fails on retry.

**Fix:** Either fix `bootstrap_home_miner.sh` to skip pairing if the
device already exists, or document the state-wipe step
(`rm -rf state/ && ./scripts/bootstrap_home_miner.sh`).

### C5: No Test Suite (MINOR)

Plan milestone 1 says the README should include:

    python3 -m pytest services/home-miner-daemon/ -v

No test files exist in the repository. No `test_*.py` files, no
`conftest.py`, no pytest configuration. The contributor guide's
"run the test suite" instruction would fail.

**Fix:** Either create a minimal test suite before documenting it, or
remove the test-running instruction from the README plan until tests exist.

## Milestone Fit

| Milestone | Fit | Blockers |
|-----------|-----|----------|
| 1: README Rewrite | Good | C4 (bootstrap idempotence), C5 (no tests) |
| 2: Contributor Guide | Good | C5 (no tests to reference) |
| 3: Operator Quickstart | Good | C2 (phantom env var) |
| 4: API Reference | Blocked | C1 (phantom endpoints), C3 (auth model) |
| 5: Architecture Doc | Good | None |

Milestones 1, 2, 3, and 5 can proceed after minor corrections.
Milestone 4 requires the most rework.

## Nemesis Security Review

### Pass 1 — Trust Boundaries and Authority

**N1: No daemon-level auth (severity: acknowledged-by-design, doc-critical)**

The daemon is a naked HTTP server. No tokens, no headers, no TLS. The
trust model is: if you can reach the port, you have full authority. This is
acceptable for milestone 1's LAN-only scope, but the documentation MUST
NOT imply otherwise. The plan's per-endpoint auth table would create a
false sense of security.

The moment an operator binds to a LAN interface (which the operator
quickstart will tell them to do), every device on the network — including
compromised IoT devices, guest network spillover, or any process on the
same machine — can control the miner.

**Recommendation for docs:** Include a "Security Model" section in the
operator quickstart that says: "In milestone 1, the daemon has no
authentication. The only access control is the network binding. Do not
expose the daemon port to untrusted networks."

**N2: Pairing records are world-readable plaintext (severity: low)**

`state/pairing-store.json` and `state/principal.json` are unencrypted JSON
files. Any process with filesystem read access can enumerate paired devices,
principal IDs, and capability grants. No integrity checks — a malicious
process could inject a pairing record with `control` capability.

For milestone 1 (single-user, single-machine), this is acceptable. The
documentation should note that state files are not encrypted and should be
protected by filesystem permissions.

**N3: Event spine is unencrypted (severity: documentation-critical)**

The plan and spec repeatedly call the event spine "encrypted." The
implementation (`spine.py`) writes plaintext JSON to `event-spine.jsonl`.
Documentation that calls this "encrypted" would be a lie.

**Fix for docs:** Use "append-only event journal" instead of "encrypted
event journal" until encryption is implemented.

### Pass 2 — Coupled State and Protocol Surfaces

**N4: Token expiration is broken (severity: low, doc-relevant)**

`store.py:create_pairing_token()` sets `token_expires_at` to
`datetime.now()` — the token is expired at creation. The expiration is
stored but never checked. The `token_used` field is always `False`.

This means: pairing tokens do not expire, are not consumed, and can be
replayed. The error taxonomy documents `PairingTokenExpired` and
`PairingTokenReplay` as named errors, but the code never raises them.

The documentation should not describe token expiration as a security
feature. It should note this as a planned-but-unimplemented capability.

**N5: No control command serialization (severity: low)**

The plan and error taxonomy describe `ControlCommandConflict` as a named
error. The daemon uses `threading.Lock` for state mutations, which prevents
data races, but it does not detect or reject concurrent conflicting
commands. Two simultaneous `set_mode` requests will both succeed — the last
one wins silently.

The documentation should not describe conflict detection as a feature.

**N6: Bootstrap is a privileged operation with no confirmation**

`bootstrap_home_miner.sh` kills any running daemon (`kill -9`), creates a
new principal identity, and pairs a device — all without confirmation. An
operator quickstart that tells users to run this script should note that it
resets the daemon state.

### Pass 3 — Operator Safety

**N7: PID file management**

The bootstrap script writes `daemon.pid` and uses it for stop/start. If
the PID file is stale (daemon crashed without cleanup), the script may
kill an unrelated process that reused the PID. This is a standard Unix
hazard, but the operator quickstart should document the recovery path.

**N8: No systemd/service management**

The daemon runs as a foreground Python process backgrounded by the shell.
The operator quickstart should note that this is suitable for testing but
not for production deployment. No restart-on-crash, no log rotation, no
resource limits.

## Remaining Blockers

1. **Three phantom endpoints** must be removed from the API reference
   plan (or implemented, but this lane is docs-only).
2. **Auth model** must be described honestly — daemon is open, CLI has
   capability checks, network binding is the security boundary.
3. **`ZEND_TOKEN_TTL_HOURS`** must be replaced with `ZEND_DAEMON_URL`.
4. **"Encrypted"** language must be replaced with "append-only" until
   encryption is implemented.

## Recommended Plan Amendments

The corrections above are all documentation-plan text changes. None
require code modifications. The plan can be unblocked by amending the
milestone descriptions:

1. **Milestone 1 (README):** Remove `python3 -m pytest` line. Add
   state-wipe note for re-running bootstrap.
2. **Milestone 3 (Operator Quickstart):** Replace `ZEND_TOKEN_TTL_HOURS`
   with `ZEND_DAEMON_URL`. Add security model section.
3. **Milestone 4 (API Reference):** Remove `GET /spine/events`,
   `GET /metrics`, `POST /pairing/refresh`. Replace per-endpoint auth
   column with honest description of where capability checks live.
4. **All milestones:** Replace "encrypted event spine" with "append-only
   event journal" or "event spine (encryption planned)."

## Verdict

**CONDITIONAL PASS.** The lane structure is correct and the five
deliverables are the right ones. The corrections are all textual
amendments to the plan — no code changes, no architectural rework. Once
the five factual errors are fixed, the lane can proceed to implementation
without further review.
