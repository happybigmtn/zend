# Home Miner Service — Verification

## Slice: Authorization Enforcement

**Date:** 2026-03-20

## Verification Commands

### Bootstrap and Pairing

```bash
# Clean state
rm -f state/daemon.pid state/pairing-store.json state/principal.json state/event-spine.jsonl

# Bootstrap daemon and create alice-phone with observe capability
./scripts/bootstrap_home_miner.sh
```

**Expected output:**
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: ...)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  ...
}
[INFO] Bootstrap complete
```

**Result:** PASS — Daemon started, alice-phone paired with observe capability

---

### Authorization Enforcement Tests

#### Test 1: Control request without Authorization header

```bash
curl -s -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
```

**Expected:** `{"error": "GATEWAY_UNAUTHORIZED", "message": "This device lacks 'control' capability"}`

**Result:** PASS

---

#### Test 3: Control request with observe-only device

```bash
curl -s -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
```

**Expected:** `{"error": "GATEWAY_UNAUTHORIZED", "message": "This device lacks 'control' capability"}`

**Result:** PASS

---

#### Test 4: Health endpoint (no auth required)

```bash
curl -s http://127.0.0.1:8080/health
```

**Expected:** `{"healthy": true, ...}`

**Result:** PASS

---

#### Test 5: Status endpoint (no auth required)

```bash
curl -s http://127.0.0.1:8080/status
```

**Expected:** Status JSON with freshness timestamp

**Result:** PASS

---

### Control-Capable Device Test

#### Pair bob-phone with control capability

```bash
cd services/home-miner-daemon
python3 cli.py pair --device bob-phone --capabilities observe,control
```

**Expected:** `{"success": true, "device_name": "bob-phone", "capabilities": ["observe", "control"], ...}`

**Result:** PASS

---

#### Control action with control-capable device

```bash
curl -s -X POST -H "Authorization: Bearer bob-phone" http://127.0.0.1:8080/miner/start
curl -s http://127.0.0.1:8080/status
curl -s -X POST -H "Authorization: Bearer bob-phone" http://127.0.0.1:8080/miner/stop
```

**Expected:** Start succeeds, status shows RUNNING, stop succeeds

**Result:** PASS

---

## Summary

| Test | Command | Expected | Result |
|------|---------|----------|--------|
| No auth header | `POST /miner/start` | GATEWAY_UNAUTHORIZED | PASS |
| Observe-only device | `POST /miner/start` | GATEWAY_UNAUTHORIZED | PASS |
| Observe-only device | `POST /miner/stop` | GATEWAY_UNAUTHORIZED | PASS |
| Health check | `GET /health` | 200 + health JSON | PASS |
| Status check | `GET /status` | 200 + status JSON | PASS |
| Control device start | `POST /miner/start` | success | PASS |
| Control device stop | `POST /miner/stop` | success | PASS |

**All tests: PASS**
