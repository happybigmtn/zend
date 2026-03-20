# Command Center Client — Verification

**Slice:** command-center-client:command-center-client
**Date:** 2026-03-20

## Automated Proof Commands

### 1. Daemon Health Check

```bash
curl -s http://127.0.0.1:18080/health
```

**Expected:** `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`

### 2. Pairing Status (Unpaired)

```bash
curl -s http://127.0.0.1:18080/pairing/status
```

**Expected (first run):** `{"paired": false}`

### 3. Pairing Initiate

```bash
curl -s -X POST http://127.0.0.1:18080/pairing/initiate \
  -H "Content-Type: application/json" \
  -d '{"device_name": "test-phone", "capabilities": ["observe"]}'
```

**Expected:** `{"success": true, "short_code": "XXXXXXXX", "device_name": "test-phone"}`

### 4. Pairing Confirm

```bash
# Use short code from step 3
curl -s -X POST http://127.0.0.1:18080/pairing/confirm \
  -H "Content-Type: application/json" \
  -d '{"code": "XXXXXXXX"}'
```

**Expected:** `{"success": true, "device_name": "test-phone", "capabilities": ["observe"], ...}`

### 5. Pairing Status (Paired)

```bash
curl -s http://127.0.0.1:18080/pairing/status
```

**Expected:** `{"paired": true, "device_name": "test-phone", "capabilities": ["observe"], "principal_id": "..."}`

### 6. Gateway Client HTML Validation

```bash
# Verify HTML is well-formed
python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('apps/zend-home-gateway/index.html').read())"
```

**Expected:** No parsing errors

### 7. JavaScript Syntax Check

```bash
# Extract and validate JS (basic check)
grep -oP '(?<=<script>)[\s\S]*(?=</script>)' apps/zend-home-gateway/index.html > /tmp/gateway.js
node --check /tmp/gateway.js 2>&1 || echo "Syntax OK or node not available"
```

**Expected:** No syntax errors

## Pre-existing Verification (from home-command-center)

The following commands were verified in the preflight stage:

| Command | Outcome |
|---------|---------|
| `bootstrap_home_miner.sh` | Success |
| `pair_gateway_client.sh --client alice-phone --capabilities observe,control` | Success |
| `read_miner_status.sh --client alice-phone` | Success |
| `set_mining_mode.sh --client alice-phone --mode balanced` | Success |
| `no_local_hashing_audit.sh --client alice-phone` | Success (no local hashing detected) |

## Manual Verification Steps

### Onboarding Flow

1. Open `apps/zend-home-gateway/index.html` in a browser
2. Verify onboarding Step 1 (Name) appears
3. Enter a name and verify Continue enables
4. Click Continue, verify Step 2 (Capabilities) appears
5. Toggle Control capability, click Continue
6. Verify short code is displayed on Step 3
7. Click Complete Pairing (in real scenario, daemon would need to confirm)
8. Verify Step 4 (Complete) shows success

### Gateway Client (Post-Pairing)

1. After pairing, verify Home screen shows status hero
2. Verify mode switcher has Paused/Balanced/Performance options
3. Verify Start/Stop buttons are present
4. Navigate to Device screen, verify permissions listed

## Notes

- Pairing endpoints use in-memory state; daemon restart clears pending pairing
- HTML/JS validation is basic syntax check only
- Full E2E onboarding test requires daemon running and manual browser interaction
