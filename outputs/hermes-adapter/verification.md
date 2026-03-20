# Hermes Adapter — Verification

## Preflight Gate

**Command:** `set +e ./scripts/bootstrap_hermes.sh`

**Result:** PASS

The preflight script starts the daemon, creates Hermes state, and verifies
the summary append works. All steps completed successfully.

## Automated Proof Commands

### 1. Bootstrap Hermes Adapter

```bash
$ ./scripts/bootstrap_hermes.sh
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1558436)
[INFO] Creating Hermes adapter state...
[INFO] Hermes state created at state/hermes/principal.json
[INFO] Verifying Hermes adapter connection...
[INFO] Hermes summary append verified
verification_event_id=b85e09b6-319c-4f52-9cca-8ca9566d1119
hermes_principal_id=hermes-adapter-001

[INFO] Hermes adapter bootstrap complete

hermes_principal_id=hermes-adapter-001
authority_scope=observe
summary_append_enabled=true
milestone=1
```

**Outcome:** PASS — Daemon started, Hermes state created, summary appended to event spine.

### 2. Hermes Status

```bash
$ ./scripts/bootstrap_hermes.sh --status
[INFO] Hermes Adapter Status:

  State: initialized
  Authority: observe-only + summary append
  File: state/hermes/principal.json
  State: initialized
  Authority: observe-only + summary append
  File: state/hermes/principal.json
  {
      "principal_id": "hermes-adapter-001",
      "name": "Hermes Gateway Adapter",
      "capabilities": ["observe"],
      "authority_scope": ["observe"],
      "summary_append_enabled": true,
      "created_at": "2026-03-20T00:00:00Z",
      "milestone": 1,
      "note": "Hermes milestone 1: observe-only + summary append. Direct control deferred."
  }

  Daemon: running
```

**Outcome:** PASS — Status command works, shows correct authority scope.

### 3. Event Spine Verification

```bash
$ cat state/event-spine.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin if 'hermes' in l.lower()]"
```

**Outcome:** The event spine contains the Hermes summary event with correct structure.

## Verification Checklist

- [x] `./scripts/bootstrap_hermes.sh` starts daemon if not running
- [x] `./scripts/bootstrap_hermes.sh` creates Hermes state file
- [x] `./scripts/bootstrap_hermes.sh` verifies summary append to event spine
- [x] `./scripts/bootstrap_hermes.sh --status` shows Hermes state
- [x] `./scripts/bootstrap_hermes.sh --stop` stops the daemon
- [x] Hermes principal has observe-only authority
- [x] Hermes can append summaries to the event spine
- [x] No local hashing or mining work performed

## What Was Proven

1. **Daemon lifecycle**: The script correctly starts/stops the Zend daemon
2. **Hermes state creation**: The Hermes adapter gets its own identity file
3. **Event spine integration**: Hermes can append summaries through `append_hermes_summary()`
4. **Authority boundary**: Hermes is configured with observe-only scope
5. **No local mining**: The script only controls the daemon, never performs mining work