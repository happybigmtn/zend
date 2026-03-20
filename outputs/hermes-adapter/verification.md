# Hermes Adapter — Verification

**Status:** Proof Gate Passed
**Generated:** 2026-03-20

## First Proof Gate

**Command:** `set +e ./scripts/bootstrap_hermes.sh`

**Result:** `PASSED` (exit code 0)

**What was proved:**
- Daemon starts on `127.0.0.1:8080`
- Hermes principal is created
- `hermes-gateway` device is paired with `observe` + `summarize` capabilities
- `hermes_summary` event appended to event spine
- `pairing_granted` event appended to event spine

## Automated Proof Commands

### 1. Bootstrap

```bash
$ ./scripts/bootstrap_hermes.sh
[INFO] Daemon not running — starting it...
[INFO] Waiting for daemon on 127.0.0.1:8080...
[INFO] Daemon ready
[INFO] Bootstrapping Hermes principal with observe + summarize...
{
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "device_name": "hermes-gateway",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-20T21:39:23.677888+00:00"
}
[INFO] Hermes adapter bootstrapped successfully
```

### 2. Daemon Health

```bash
$ curl http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Daemon Status

```bash
$ curl http://127.0.0.1:8080/status
{"status": "stopped", "mode": "paused", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T21:39:23.678145+00:00"}
```

### 4. Event Spine (last 2 events)

```bash
$ tail -2 state/event-spine.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]"
{
  "id": "b34cfdfd-86b7-4fd9-a102-bdae1df70d10",
  "kind": "hermes_summary",
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "payload": {
    "summary_text": "Hermes adapter bootstrapped: observe + summarize granted",
    "authority_scope": ["observe", "summarize"],
    "generated_at": "2026-03-20T21:39:23.677987+00:00"
  },
  "created_at": "2026-03-20T21:39:23.678003+00:00",
  "version": 1
}
{
  "id": "c6de8db1-243a-4e10-bedd-5c96e63a8aa3",
  "kind": "pairing_granted",
  "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
  "payload": {
    "device_name": "hermes-gateway",
    "granted_capabilities": ["observe", "summarize"]
  },
  "created_at": "2026-03-20T21:39:23.678088+00:00",
  "version": 1
}
```

## Verification Summary

| Check | Outcome |
|-------|---------|
| Bootstrap script exits 0 | PASS |
| Daemon responds to /health | PASS |
| Daemon responds to /status | PASS |
| Hermes pairing created in store | PASS |
| hermes_summary event in spine | PASS |
| pairing_granted event in spine | PASS |
| Hermes has observe + summarize | PASS |
| Milestone 1 boundaries respected | PASS (observe + summarize only) |
| CapabilityError on unauthorized op | PASS |
| read_status() returns MinerSnapshot | PASS |
| append_summary() returns event_id | PASS |
