# Hermes Adapter — Verification

## First Proof Gate

**Command:** `./scripts/bootstrap_hermes.sh`

**Result:** PASS

The bootstrap script successfully:
1. Started the home-miner daemon on `127.0.0.1:8080`
2. Created Hermes adapter state at `state/hermes/principal.json` with observe-only authority
3. Verified Hermes summary append to the event spine

```
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1648569)
[INFO] Creating Hermes adapter state...
[INFO] Hermes state created at .../state/hermes/principal.json
[INFO] Verifying Hermes adapter connection...
[INFO] Hermes summary append verified
verification_event_id=1a521d08-8f7a-44dc-909d-0663fc3fd7f0
hermes_principal_id=hermes-adapter-001

[INFO] Hermes adapter bootstrap complete

hermes_principal_id=hermes-adapter-001
authority_scope=observe
summary_append_enabled=true
milestone=1
```

**What it proved:**
- Daemon HTTP server binds successfully to `127.0.0.1:8080`
- Hermes principal identity created with milestone 1 authority (`observe` + `summary_append_enabled`)
- `append_hermes_summary()` writes to the event spine and returns a valid event with UUID

## Automated Proof Commands

### 1. Clear Hermes daemon state

```bash
$ ./scripts/bootstrap_hermes.sh --stop
[INFO] Stopping Hermes adapter daemon
[INFO] Hermes adapter stopped
```

**Outcome:** PASS — cleared stale daemon PID state before status verification.

### 2. Standalone Hermes health check

```bash
$ ./scripts/hermes_status.sh
[INFO] Hermes Adapter Status:

  principal_state=initialized
  principal_id=hermes-adapter-001
  capabilities=observe
  authority_scope=observe
  summary_append_enabled=true
  milestone=1
  daemon_pid_status=missing
  daemon_pid=missing
  daemon_endpoint=skipped
  hermes_summary_count=3
  last_hermes_summary_at=2026-03-20T19:29:34.603875+00:00
  overall_status=degraded
  issues=daemon_not_running
```

**Outcome:** PASS — the standalone status script reports Hermes milestone 1
authority and fails closed when the daemon is not running.

### 3. Bootstrap status delegation

```bash
$ ./scripts/bootstrap_hermes.sh --status
[INFO] Hermes Adapter Status:

  principal_state=initialized
  principal_id=hermes-adapter-001
  capabilities=observe
  authority_scope=observe
  summary_append_enabled=true
  milestone=1
  daemon_pid_status=missing
  daemon_pid=missing
  daemon_endpoint=skipped
  hermes_summary_count=3
  last_hermes_summary_at=2026-03-20T19:29:34.603875+00:00
  overall_status=degraded
  issues=daemon_not_running
```

**Outcome:** PASS — `bootstrap_hermes.sh --status` now delegates to the
standalone Hermes health-check surface.

## Verification Checklist

- [x] `./scripts/hermes_status.sh` reports Hermes milestone 1 authority from `state/hermes/principal.json`
- [x] `./scripts/hermes_status.sh` counts Hermes summary events from the event spine
- [x] `./scripts/bootstrap_hermes.sh --status` delegates to the standalone status surface
- [x] `./scripts/bootstrap_hermes.sh` completes successfully (daemon starts, state created, summary append verified)
