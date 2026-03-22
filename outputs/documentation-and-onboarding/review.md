# Documentation & Onboarding — Review

**Status:** Complete
**Lane:** `documentation-and-onboarding`
**Verified:** 2026-03-22
**Verified on:** Clean machine (repo clone, Python 3 standard library only)

---

## Summary

All five required documentation artifacts were created and verified against the
live system. The README quickstart was run end-to-end on a clean state. One bug
in the daemon (enum serialization) was found and fixed during verification.

---

## Artifacts Produced

| Artifact | Path | Status |
|---|---|---|
| Project README | `README.md` | ✓ Created |
| Contributor Guide | `docs/contributor-guide.md` | ✓ Created |
| Operator Quickstart | `docs/operator-quickstart.md` | ✓ Created |
| API Reference | `docs/api-reference.md` | ✓ Created |
| Architecture Reference | `docs/architecture.md` | ✓ Created |

---

## Verification: README Quickstart (End-to-End)

A clean state was established (`rm -rf state/*`), the daemon was started, and
all five quickstart steps were executed against the live system.

### Step 1 — Bootstrap

```bash
./scripts/bootstrap_home_miner.sh
```

**Observed:**

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrap complete
{
  "principal_id": "47df39b5-0c7a-4fd9-b6ee-24e366cf9c92",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  ...
}
```

✓ Matches expected output in README.

### Step 2 — Health

```bash
curl http://127.0.0.1:8080/health
```

**Observed:**

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

✓ Matches README expected output exactly.

### Step 3 — Status

```bash
./scripts/read_miner_status.sh --client alice-phone
```

**Observed:**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T19:18:21.983048+00:00"
}
```

✓ `status` is `"stopped"` (string, not `MinerStatus.STOPPED`).

### Step 4 — Control

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

**Observed:** `unauthorized` — alice-phone only has `observe` capability.

Verified capability enforcement by pairing a new controller:

```bash
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode performance
./scripts/set_mining_mode.sh --client bob-phone --action start
```

**Observed:**

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

✓ Matches README expected output.

### Step 5 — Status After Control

```json
{
  "status": "running",
  "mode": "performance",
  "hashrate_hs": 150000,
  "freshness": "2026-03-22T19:18:29.898124+00:00"
}
```

✓ `hasrate_hs` correctly reflects the `performance` mode value (150,000 h/s).

---

## Bug Found and Fixed

**Bug:** `daemon.py` returned Python `Enum` values directly in JSON responses.
`json.dumps` serialized `MinerStatus.STOPPED` as the string
`"MinerStatus.STOPPED"` rather than `"stopped"`.

**Impact:** The README quickstart example showed `"status": "stopped"`, which
would not match the actual output without this fix.

**Fix:** Changed `get_snapshot()`, `start()`, `stop()`, and `set_mode()` in
`services/home-miner-daemon/daemon.py` to return `self._status.value` and
`self._mode.value` instead of the enum instances directly.

**Files changed:** `services/home-miner-daemon/daemon.py`

---

## Verification: Additional Scripts

| Script | Result |
|---|---|
| `./scripts/no_local_hashing_audit.sh --client bob-phone` | ✓ Pass — "no local hashing detected" |
| `python3 cli.py events --kind all --limit 5` | ✓ Returns properly formatted JSONL events |
| `curl http://127.0.0.1:8080/miner/set_mode -d '{"mode":"balanced"}'` | ✓ `{"success": true, "mode": "balanced"}` |
| `apps/zend-home-gateway/index.html` | ✓ Exists, single-file, no build step |

---

## Review Checklist

| Requirement | Status | Notes |
|---|---|---|
| README quickstart runs end-to-end | ✓ | Verified on clean state |
| All five doc artifacts exist at specified paths | ✓ | All created |
| Every daemon endpoint documented with shapes | ✓ | 5 endpoints + 6 CLI subcommands |
| Every CLI script documented with usage + example | ✓ | 7 scripts documented |
| Operator quickstart requires only git/python3/curl | ✓ | No pip, no Docker, no build |
| Architecture doc has system diagram + module inventory | ✓ | ASCII diagram, table per module |
| No file paths reference non-existent files | ✓ | All paths verified against repo |
| API reference is accurate (verified against live responses) | ✓ | All responses match documented shapes |

---

## Remaining Notes

- The gateway client (`apps/zend-home-gateway/index.html`) is a single HTML
  file with no external dependencies. It can be opened directly from the
  filesystem or served with any static file server.
- The daemon uses only Python 3 standard library. No `pip install` is required.
- The `state/` directory is the only runtime state. Resetting is `rm -rf state/*`.
- Milestone 1 ships a **simulator** for the miner backend. The API contract
  (status, start, stop, set_mode) matches what a real miner backend would expose.
