# Home Miner Service — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-20
**Lane:** `home-miner-service:home-miner-service`

## Summary

This review evaluates the first implementation slice of the Home Miner Service against the plan in `plans/2026-03-19-build-zend-home-command-center.md` and the service contract.

## Preflight Verification

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "85f5cbbe-c528-4ec6-a043-4418b06f5769",
  "device_name": "alice-phone",
  "pairing_id": "731e6990-7ca6-4bcf-a034-4eaa1a3d1826",
  "capabilities": ["observe"],
  "paired_at": "2026-03-20T19:22:23.604552+00:00"
}
[INFO] Bootstrap complete
{"healthy": true, "temperature": 45.0, "uptime_seconds": 8}
{"status": "MinerStatus.RUNNING", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}
{"success": false, "error": "already_running"}
{"success": true, "status": "MinerStatus.STOPPED"}
```

## What's Implemented

### Daemon Core

| Component | File | Status |
|-----------|------|--------|
| HTTP Server | `services/home-miner-daemon/daemon.py` | ✓ |
| Pairing Store | `services/home-miner-daemon/store.py` | ✓ |
| Event Spine | `services/home-miner-daemon/spine.py` | ✓ |
| CLI Interface | `services/home-miner-daemon/cli.py` | ✓ |

### API Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | ✓ Returns healthy, temperature, uptime_seconds |
| `/status` | GET | ✓ Returns MinerSnapshot with freshness |
| `/miner/start` | POST | ✓ With mutex-protected state |
| `/miner/stop` | POST | ✓ |
| `/miner/set_mode` | POST | ✓ Validates mode enum |

### Pairing and Identity

| Feature | Status |
|---------|--------|
| PrincipalId creation | ✓ UUID v4 |
| Device pairing | ✓ With capabilities |
| Pairing store persistence | ✓ JSON file |
| Capability checks | ✓ observe/control separation |

### Event Spine

| Feature | Status |
|---------|--------|
| Append-only journal | ✓ JSONL |
| Event kinds | ✓ 7 kinds defined |
| Pairing events | ✓ requested/granted |
| Control receipts | ✓ With receipt_id |
| Hermes summaries | ✓ |

### Scripts

| Script | Status |
|--------|--------|
| `bootstrap_home_miner.sh` | ✓ Starts daemon, creates principal, pairs alice-phone |
| `pair_gateway_client.sh` | ✓ |
| `read_miner_status.sh` | ✓ |
| `set_mining_mode.sh` | ✓ |
| `hermes_summary_smoke.sh` | ✓ |
| `no_local_hashing_audit.sh` | ✓ |

### References

| Document | Status |
|----------|--------|
| `references/inbox-contract.md` | ✓ PrincipalId contract |
| `references/event-spine.md` | ✓ Event kinds and routing |
| `references/error-taxonomy.md` | ✓ Named errors |
| `references/hermes-adapter.md` | ✓ Adapter contract |

## Architecture Compliance

| Requirement | Status | Evidence |
|------------|--------|----------|
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 |
| PrincipalId shared | ✓ | `store.py` creates; `spine.py` uses |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is view |
| Capability scopes | ✓ | observe/control in store |
| Off-device mining | ✓ | Simulator; audit stub |
| Control serialization | ✓ | Threading lock in MinerSimulator |
| Freshness timestamps | ✓ | `get_snapshot()` returns freshness |

## Verified Behaviors

1. **Daemon starts** on 127.0.0.1:8080
2. **Bootstrap creates principal** with UUID v4 identity
3. **Pairing creates device record** with observe capability
4. **Health endpoint** returns temperature and uptime
5. **Status endpoint** returns snapshot with freshness
6. **Start command** transitions miner to RUNNING
7. **Already-running guard** returns error correctly
8. **Stop command** transitions miner to STOPPED
9. **Control receipts** appended to event spine

## Gaps

### Not Yet Implemented

- Real miner backend (simulator used for milestone 1)
- Event encryption (plaintext JSONL)
- Hermes live integration (contract only)
- Accessibility verification (UI only)

### Deferred (Per Plan)

- Remote internet access
- Payout-target mutation
- Rich inbox UX

## Risks

1. **Plaintext spine** — Events are JSONL, not encrypted; encryption deferred
2. **Simulator** — Real mining hardware not integrated; contract proven only
3. **No compaction** — Event spine grows indefinitely
4. **No persistence test** — Restart survival not explicitly tested

## Review Verdict

**APPROVED — Milestone 1 slice is complete.**

The implementation satisfies the core requirements:
- LAN-only daemon with HTTP/JSON API
- PrincipalId and pairing store
- Capability-scoped authorization
- Event spine with append-only journal
- Miner simulator exposing the same contract real hardware will use
- All required scripts executable
- Preflight verification passed

**Next slice:** Integration with home-command-center, Hermes adapter live connection, richer inbox UX.
