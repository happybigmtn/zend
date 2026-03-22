# Stabilize Failed Fabro Implementation Lanes

Status: Draft
Date: 2026-03-22

## Purpose

Four parallel implementation lanes for the Zend Home Command Center all failed
to complete. This spec defines what must be fixed so that each lane can re-run
to completion against the existing milestone-1 codebase.

The four lanes are:

1. **command-center-client-implementation** — stalled
2. **hermes-adapter-implementation** — merge conflict
3. **home-miner-service-implementation** — bootstrap failure
4. **private-control-plane-implementation** — port conflict

Each failure has a distinct root cause, but several share a common structural
problem: the daemon HTTP API has no authentication, so the capability model
enforced by the CLI is bypassed by the mobile client and by any LAN peer.

## Failure Analysis

### Lane 1: command-center-client-implementation (stall)

**Root cause:** The HTML client at `apps/zend-home-gateway/index.html` talks
directly to the daemon HTTP API at `http://127.0.0.1:8080` with no
authentication or capability header. The client hardcodes `capabilities:
['observe', 'control']` in local JavaScript state (line 627) and checks
permissions client-side only. It never reads the pairing store. This means:

- The client cannot distinguish an observe-only device from a controller.
- The client never calls the CLI pairing flow; it skips trust ceremony.
- Any browser on the LAN can issue start/stop/set_mode with no credential.

The stall is architectural: the client cannot proceed because it has no way to
authenticate to the daemon and the daemon has no way to reject unauthorized
requests at the HTTP layer.

**Fix required:** Add a bearer-token or pairing-token header to the daemon HTTP
API. The daemon must reject requests that lack a valid pairing credential. The
client must acquire a token through the pairing flow and include it on every
request.

### Lane 2: hermes-adapter-implementation (merge conflict)

**Root cause:** The Hermes adapter does not exist as code. The reference
contract at `references/hermes-adapter.md` defines the interface, but the smoke
test at `scripts/hermes_summary_smoke.sh` bypasses it entirely. Lines 45-55 of
that script import Python modules directly (`from store import ...; from spine
import ...`) and call `append_hermes_summary` without any adapter, authority
token, or capability check. There is no `HermesAdapter` class anywhere in the
codebase.

A merge conflict is expected when two lanes (hermes-adapter and
home-miner-service) both modify `spine.py` or `store.py` without coordinating,
because there is no adapter boundary to isolate Hermes writes from direct daemon
writes.

**Fix required:** Implement a minimal `HermesAdapter` class in
`services/home-miner-daemon/hermes_adapter.py` that:

- Accepts an authority token scoped to `['observe', 'summarize']`
- Validates the token against the principal store before appending
- Calls `spine.append_hermes_summary` only after authorization
- Rejects direct control commands

Update `hermes_summary_smoke.sh` to use the adapter instead of direct imports.

### Lane 3: home-miner-service-implementation (bootstrap failure)

**Root cause:** The bootstrap script `scripts/bootstrap_home_miner.sh` has
several failure modes:

1. **State directory race:** `STATE_DIR` is resolved three different ways across
   `daemon.py`, `store.py`, and `spine.py` — each calls `default_state_dir()`
   independently, computing `Path(__file__).resolve().parents[2] / "state"`.
   While commit `a4cfd5c` unified this, the shell scripts also set
   `ZEND_STATE_DIR` and `cd` into the daemon directory, creating a fragile
   coupling between working directory and state location.

2. **Pairing token expires immediately:** `store.py:89` sets the token
   expiration to `datetime.now(timezone.utc).isoformat()` — the token expires
   at the moment of creation. Any downstream check for token validity will fail.

3. **Bootstrap re-runs create duplicate pairings:** Running bootstrap twice for
   the same device raises `ValueError("Device 'alice-phone' already paired")`
   because `pair_client` checks for duplicates but the bootstrap script does not
   handle this gracefully. The plan requires idempotent bootstrap.

**Fix required:**
- Fix `create_pairing_token` to set expiration in the future (e.g., +1 hour).
- Make bootstrap idempotent: skip pairing if device already exists.
- Standardize state directory resolution to one canonical mechanism.

### Lane 4: private-control-plane-implementation (port conflict)

**Root cause:** The daemon binds to `127.0.0.1:8080` with
`allow_reuse_address = True` but has no port-conflict detection beyond checking
if the PID file's process is alive. If another process (a previous crashed
daemon, a dev server, or another Zend instance) holds port 8080, the daemon
either steals the port via `SO_REUSEADDR` (masking the conflict) or fails with
an opaque `OSError`.

The error taxonomy defines `DaemonPortInUse` but the code never raises or
catches it. The bootstrap script's readiness loop (`curl` for 10 iterations)
will silently connect to the wrong process if something else is already on 8080.

**Fix required:**
- Before binding, attempt a connection to `BIND_HOST:BIND_PORT`. If it
  succeeds, fail with `DaemonPortInUse` and a clear message.
- In `bootstrap_home_miner.sh`, after starting, verify the responding process
  is the expected PID (e.g., check `/health` returns a Zend-specific response
  body, not just HTTP 200).

## Shared Structural Issues

All four lanes are blocked or degraded by:

1. **No HTTP-layer authentication.** The daemon serves unauthenticated JSON over
   HTTP. The capability model exists only in the CLI layer. The mobile client
   and any LAN script can bypass it entirely.

2. **No control command serialization.** The plan requires serialized control
   commands, but the daemon uses a simple `threading.Lock` on in-memory state
   with no command queue or conflict detection. Two concurrent HTTP requests can
   both succeed.

3. **Event spine is not encrypted.** The spec and contracts call it an
   "encrypted event journal," but `spine.py` writes plaintext JSON to a JSONL
   file. The word "encrypted" in the contracts is aspirational, not
   implemented.

4. **No automated tests.** The plan requires tests for replayed tokens, stale
   snapshots, controller conflicts, restart recovery, and audit false
   positives. None exist.

## Acceptance Criteria

This stabilization is accepted when:

- [ ] The daemon HTTP API rejects requests without a valid pairing credential
- [ ] The `HermesAdapter` class exists and the smoke test uses it
- [ ] Bootstrap is idempotent (re-run does not fail for existing devices)
- [ ] Pairing tokens have a future expiration time
- [ ] Port conflict is detected and reported before binding
- [ ] The mobile client acquires and sends a credential on every request
- [ ] At least one automated test exists per named error class
- [ ] All four lanes can re-run to completion without manual intervention

## Not in Scope

- Actual encryption of the event spine (deferred to a crypto integration
  milestone, but the current gap must be documented)
- Remote access beyond LAN
- Payout-target mutation
- Rich conversation UX
