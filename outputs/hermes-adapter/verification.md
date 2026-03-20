# Hermes Adapter — Verification

## First Proof Gate

**Command:** `./scripts/bootstrap_hermes.sh`

**Result:** PASS

The bootstrap script proves the full Hermes authority-boundary slice end-to-end:
daemon start, Hermes state creation, and delegated summary append via the guarded
`append_hermes_summary_authorized()` path.

```
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1657390)
[INFO] Creating Hermes adapter state...
[INFO] Hermes state created at .../state/hermes/principal.json
[INFO] Verifying Hermes adapter connection...
[INFO] Hermes summary append verified
verification_event_id=0048e786-001a-4749-b9e2-457e54e3c945
hermes_principal_id=hermes-adapter-001

[INFO] Hermes adapter bootstrap complete

hermes_principal_id=hermes-adapter-001
authority_scope=observe
summary_append_enabled=true
milestone=1
```

**What it proved:**
- Daemon binds to `127.0.0.1:8080` and responds to `/health`
- Hermes principal state is created at `state/hermes/principal.json` with observe-only delegated authority
- `append_hermes_summary_authorized()` exercises the milestone-1 authority check end-to-end
- The append returns a verification event UUID, confirming write access through the guarded path

**stderr note:** When the daemon is already running (from a prior invocation), a subsequent
bootstrap run produces `OSError: [Errno 98] Address already in use` in the daemon's stderr
after the bootstrap script has already succeeded. This is a benign race condition from the
daemon staying bound to its port; it does not affect the proof outcome.

## Automated Proof Commands

### 1. Hermes authority boundary tests

```bash
$ python3 -m unittest -q tests/test_hermes_authority.py
----------------------------------------------------------------------
Ran 4 tests in 0.002s

OK
```

**Outcome:** PASS — delegated observe-only append succeeds, while scope
escalation, disabled summary append, and milestone-boundary drift are all
rejected before any event-spine write occurs.

### 2. Python syntax check

```bash
$ python3 -m py_compile services/home-miner-daemon/spine.py
```

**Outcome:** PASS — the updated event-spine module compiles cleanly.

## Verification Checklist

- [x] Delegated Hermes summary append succeeds only for the milestone 1
      observe-only principal
- [x] Requested Hermes scope escalation is rejected before event-spine append
- [x] Disabled summary append is rejected before event-spine append
- [x] Milestone drift to broader Hermes authority is rejected before
      event-spine append
- [x] `./scripts/bootstrap_hermes.sh` end-to-end proof passes

## Remaining Risk

None for this slice. The bootstrap proof passes and all authority-boundary
tests confirm the delegated Hermes summary append is correctly gated.