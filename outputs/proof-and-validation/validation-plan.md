# Validation Plan — Zend Gateway Proof and Validation

**Lane:** proof-and-validation
**Status:** Draft
**Date:** 2026-03-20

## Purpose

This plan defines the validation activities required to prove the gateway client performs no hashing, only issues control requests to the home miner, and that the system handles edge cases correctly.

## Context and Orientation

### System Overview

Zend is a private command center combining encrypted Zcash messaging with a mobile gateway into a home miner. The phone is the control plane; mining happens on the home miner hardware, never on the device.

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Gateway Client | `apps/zend-home-gateway/index.html` | Mobile-shaped HTML client for miner control |
| Home Miner Daemon | `services/home-miner-daemon/daemon.py` | LAN-only HTTP service exposing miner control contract |
| Pairing Store | `services/home-miner-daemon/store.py` | Principal identity and device pairing records |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted event journal |
| CLI | `services/home-miner-daemon/cli.py` | Command-line interface for daemon control |

### Definitions

- **Gateway client**: The HTML/JS client that runs on a mobile device and communicates with the home miner daemon over LAN
- **Control requests**: HTTP POST calls to `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints
- **Hashing**: Cryptographic proof-of-work computation; must NOT occur on the gateway client device

## Frontier Tasks

### Task 1: Prove Gateway Client Performs No Hashing

**Claim:** The gateway client (`apps/zend-home-gateway/index.html`) performs no hashing and only issues control requests to the home miner.

**Evidence Requirements:**

1. **Code inspection** — The gateway client JavaScript contains no mining-related code:
   - No references to hash functions (SHA-256, Equihash, etc.)
   - No Web Workers that could perform background hashing
   - No references to mining pools or stratum protocols
   - Only HTTP fetch calls to daemon endpoints

2. **Network inspection** — The gateway client only makes:
   - `GET /status` — polling for miner snapshot
   - `GET /health` — daemon health check
   - `POST /miner/start` — control request
   - `POST /miner/stop` — control request
   - `POST /miner/set_mode` — control request

3. **Existing audit script** — `scripts/no_local_hashing_audit.sh` provides a structural check

**Validation Steps:**

```bash
# Step 1: Inspect gateway client JavaScript for mining keywords
grep -E "(worker|webworker|hash|mining|stratum|pool|submit|nonce)" \
  apps/zend-home-gateway/index.html

# Step 2: Verify only control endpoints are called
grep -E "fetch\(|XMLHttpRequest" apps/zend-home-gateway/index.html
# Expected: only calls to http://127.0.0.1:8080 with /status, /health, /miner/*

# Step 3: Run existing audit
./scripts/no_local_hashing_audit.sh --client alice-phone
```

**Pass Criteria:**
- Zero mining-related keywords found in gateway client JavaScript
- All network calls are to daemon control/status endpoints only
- Audit script exits 0

---

### Task 2: Add Automated Tests for Edge Cases

#### 2.1 Replayed Pairing Tokens

**Scenario:** A pairing token is captured and replayed by an attacker.

**Expected Behavior:** Tokens are single-use; replay should fail.

**Validation Steps:**

```bash
# Bootstrap a fresh principal and device
./scripts/bootstrap_home_miner.sh

# Pair a device (creates token)
./scripts/pair_gateway_client.sh --client test-device --capabilities observe,control

# Attempt to pair same device again (should fail - duplicate)
./scripts/pair_gateway_client.sh --client test-device --capabilities observe
# Expected: error "Device 'test-device' already paired"
```

**Code Reference:** `services/home-miner-daemon/store.py:99-101`
```python
# Check for duplicate device name
for existing in pairings.values():
    if existing['device_name'] == device_name:
        raise ValueError(f"Device '{device_name}' already paired")
```

**Pass Criteria:** Re-pairing the same device name returns an error; no duplicate pairing record created.

#### 2.2 Stale Snapshots

**Scenario:** A client receives a status snapshot that is older than expected.

**Expected Behavior:** The snapshot contains a `freshness` timestamp; clients should detect stale data.

**Validation Steps:**

```bash
# Get status snapshot
curl http://127.0.0.1:8080/status
# Observe: "freshness": "<ISO timestamp>"

# Check snapshot structure
python3 -c "
import json, time
import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8080/status')
data = json.loads(resp.read())
print('Has freshness:', 'freshness' in data)
print('Freshness value:', data.get('freshness'))
print('Has hashrate_hs:', 'hashrate_hs' in data)
"
```

**Code Reference:** `services/home-miner-daemon/daemon.py:135-148` — `get_snapshot()` method

**Pass Criteria:** Snapshot always includes `freshness` field; client UI handles stale detection.

#### 2.3 Controller Conflicts

**Scenario:** Two clients with `control` capability issue conflicting commands simultaneously.

**Expected Behavior:** The event spine records a `control_receipt` with status `accepted`, `rejected`, or `conflicted`.

**Validation Steps:**

```bash
# Bootstrap two clients with control capability
./scripts/pair_gateway_client.sh --client client-a --capabilities observe,control
./scripts/pair_gateway_client.sh --client client-b --capabilities observe,control

# Issue conflicting commands
./scripts/set_mining_mode.sh --client client-a --mode balanced
./scripts/set_mining_mode.sh --client client-b --mode performance

# Check event spine for control receipts
cd services/home-miner-daemon
python3 cli.py events --kind control_receipt --limit 5
```

**Code Reference:**
- Event spine contract: `references/event-spine.md:73-80`
- Control receipt status: `'accepted' | 'rejected' | 'conflicted'`

**Pass Criteria:** Both commands are recorded; conflict detection is logged.

#### 2.4 Restart Recovery

**Scenario:** The daemon restarts; in-flight requests and state are recovered.

**Expected Behavior:** Daemon restarts cleanly; pairing records and event spine persist.

**Validation Steps:**

```bash
# Start daemon and pair a device
./scripts/bootstrap_home_miner.sh --daemon
./scripts/pair_gateway_client.sh --client recovery-test --capabilities observe,control

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Verify state files exist
ls -la state/
# Expected: principal.json, pairing-store.json, event-spine.jsonl

# Restart daemon
./scripts/bootstrap_home_miner.sh --daemon

# Verify paired device still recognized
cd services/home-miner-daemon
python3 -c "
from store import has_capability
print('Device still paired:', has_capability('recovery-test', 'control'))
"
```

**Code Reference:**
- `services/home-miner-daemon/store.py` — Principal and pairing persistence
- `services/home-miner-daemon/spine.py` — Event spine append-only journal

**Pass Criteria:** Paired devices persist across daemon restarts; event spine is intact.

#### 2.5 Audit False Positives/Negatives

**Scenario:** The no-hashing audit produces incorrect results.

**Expected Behavior:** Audit correctly identifies presence/absence of hashing code.

**Validation Steps:**

```bash
# Run audit on clean codebase
./scripts/no_local_hashing_audit.sh --client alice-phone
echo "Exit code: $?"

# Verify audit logic
# The audit checks for:
# 1. Mining-related code in daemon Python files
# 2. Local CPU worker threads
grep -r "def.*hash" services/home-miner-daemon/*.py | grep -v hashrate
# Expected: no matches (hashrate is legitimate monitoring, not mining)
```

**Pass Criteria:** Audit exits 0 on clean codebase; would exit 1 if hashing code detected.

---

## Progress Checklist

- [ ] Gateway client code inspection complete (no hashing)
- [ ] Network call inspection complete (control requests only)
- [ ] Replayed pairing token test written and passing
- [ ] Stale snapshot detection test written and passing
- [ ] Controller conflict test written and passing
- [ ] Restart recovery test written and passing
- [ ] Audit false positive/negative test written and passing
- [ ] Gateway proof transcript documented

## Decision Log

- **2026-03-20**: Initial validation plan created. The system uses a milestone-1 simulator; real mining hardware is out of scope for current phase.
