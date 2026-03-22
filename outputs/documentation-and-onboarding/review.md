# Documentation & Onboarding — Review

**Date:** 2026-03-22  
**Lane:** documentation-and-onboarding  
**Status:** Needs Correction

## Summary

Documentation is comprehensive but contains **critical inaccuracies** that must be fixed before approval:

1. **`/spine/events` HTTP endpoint is not implemented** — documented but doesn't exist in daemon.py
2. **Bootstrap creates `observe` only** — README examples use `control` actions which require `control` capability
3. **Device name mismatch** — bootstrap creates `alice-phone`, but quickstart examples use `my-phone`

## Deliverables Status

| Document | Location | Status | Issues |
|----------|----------|--------|--------|
| README.md (rewrite) | `README.md` | ⚠️ Needs Fix | Device name mismatch, capability mismatch |
| Contributor Guide | `docs/contributor-guide.md` | ⚠️ Needs Fix | References non-existent `/spine/events` endpoint |
| Operator Quickstart | `docs/operator-quickstart.md` | ✅ OK | Mostly accurate |
| API Reference | `docs/api-reference.md` | ❌ Fail | `/spine/events` not implemented |
| Architecture | `docs/architecture.md` | ⚠️ Needs Fix | Mentions `/spine/events` HTTP endpoint |

## Verified Implementation

### HTTP Endpoints (daemon.py)

```python
# GET handlers
GET /health      → miner.health
GET /status      → miner.get_snapshot()

# POST handlers
POST /miner/start     → miner.start()
POST /miner/stop      → miner.stop()
POST /miner/set_mode  → miner.set_mode(mode)
```

**No `/spine/events` endpoint exists.** The event spine is queryable only via CLI:
```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

### CLI Commands (cli.py)

| Command | File Access | HTTP Call | Capability Check |
|---------|-------------|-----------|------------------|
| `health` | No | GET /health | None |
| `status` | No | GET /status | `observe` or `control` |
| `events` | Yes (JSONL) | No | `observe` or `control` |
| `control` | No | POST /miner/* | `control` required |
| `bootstrap` | Yes (JSON) | No | None |
| `pair` | Yes (JSON) | No | None |

### Bootstrap Behavior

```python
# cli.py cmd_bootstrap()
pairing = pair_client(args.device, ['observe'])  # Only 'observe'!
spine.append_pairing_granted(...)  # NOT append_pairing_requested
```

Default device: `alice-phone`

### Pairing Capabilities

| Command | Capabilities Granted |
|---------|---------------------|
| `bootstrap --device X` | `['observe']` |
| `pair --device X --capabilities observe,control` | `['observe', 'control']` |

## Required Corrections

### 1. README.md — Quickstart Example

**Current (Wrong):**
```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced
```

**Correction:** Use `alice-phone` (default from bootstrap) OR pair with `control` capability:
```bash
# Option A: Use the default device with observe only (can't control)
# Option B: Pair with control capability first:
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control

# Then control works:
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### 2. API Reference — Remove /spine/events

**Remove:**
```
GET /spine/events    observe    Event journal query
```

**Add note:**
> **Note:** Event spine queries are CLI-only. Use:
> ```bash
> python3 services/home-miner-daemon/cli.py events --limit 10
> ```

### 3. Architecture.md — Data Flow Correction

The "Control Command Flow" is accurate. However, the "Status Query Flow" needs to clarify that `/spine/events` is NOT an HTTP endpoint. Remove any references to querying events via HTTP.

## What Works Correctly

### Bootstrap
```bash
./scripts/bootstrap_home_miner.sh
# Creates state/principal.json
# Creates state/pairing-store.json  
# Creates state/event-spine.jsonl
# Daemon starts on 127.0.0.1:8080
```

### Health Check
```bash
curl http://127.0.0.1:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### Status Check
```bash
curl http://127.0.0.1:8080/status
# {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

### Miner Control (after pairing with control capability)
```bash
curl -X POST http://127.0.0.1:8080/miner/start
# {"success": true, "status": "running"}
```

## Quality Assessment

### Completeness
- [x] README under 200 lines
- [x] Quickstart with 5 commands
- [x] Daemon endpoints documented
- [x] CLI commands documented
- [x] Environment variables documented
- [x] Error codes documented
- [x] Architecture diagrams included
- [x] Module guide complete
- [x] Data flow explained
- [x] Design decisions justified
- [x] Troubleshooting section included

### Accuracy
- [ ] All curl examples tested — **FAIL**: `/spine/events` doesn't exist
- [x] Daemon endpoints verified (health, status, miner/*)
- [x] CLI commands tested
- [x] File paths verified
- [x] Function names verified
- [x] Enum values verified
- [x] Environment variables verified

### Usability
- [x] Step-by-step instructions
- [x] Expected output shown
- [x] Error scenarios covered
- [x] Recovery procedures included

## Critical Defects

1. **api-reference.md**: Documents `GET /spine/events` which does not exist in daemon.py
2. **README.md**: Uses `my-phone` but bootstrap creates `alice-phone`
3. **README.md**: Uses `control` action without noting that bootstrap only grants `observe`

## Recommendations

### High Priority
1. Remove `/spine/events` from API reference
2. Fix README quickstart to use correct device name and capability
3. Add explicit note about CLI-only event queries

### Medium Priority
1. Update architecture.md to clarify spine is CLI-accessed only
2. Add clarification in operator guide about pairing for control

## Sign-Off

**Reviewer:** Genesis Sprint  
**Date:** 2026-03-22  
**Approved:** ❌ — Requires corrections listed above

---

## Verification Checklist

### Pre-Flight (Fresh Clone)

```bash
# From a clean directory:
git clone <repo-url> zend-test
cd zend-test

# Follow README quickstart
./scripts/bootstrap_home_miner.sh
# Expected: Daemon starts, pairing created (alice-phone with observe)

curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}

# Note: Control action requires pairing with 'control' capability first:
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control

python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
# Expected: {"success": true, ...}

# Clean up
./scripts/bootstrap_home_miner.sh --stop
cd .. && rm -rf zend-test
```

### HTTP Endpoint Verification

```bash
./scripts/bootstrap_home_miner.sh

# All of these work:
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
curl -X POST http://127.0.0.1:8080/miner/start
curl -X POST http://127.0.0.1:8080/miner/stop
curl -X POST http://127.0.0.1:8080/miner/set_mode -H "Content-Type: application/json" -d '{"mode":"balanced"}'

# This does NOT work (not implemented):
curl http://127.0.0.1:8080/spine/events  # 404
```

### CLI Event Query (instead of HTTP)

```bash
# Events are queried via CLI, not HTTP:
python3 services/home-miner-daemon/cli.py events --limit 10
```
