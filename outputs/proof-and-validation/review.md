# Review — Zend Gateway Proof and Validation

**Lane:** proof-and-validation
**Status:** Reviewed
**Date:** 2026-03-20

## Executive Summary

This review covers the first honest reviewed slice for the proof-and-validation lane. It assesses the gateway client implementation against the product specification's trust promise: "the phone is only a control plane; hashing never happens on-device."

## Findings

### 1. Gateway Client Hashing Claim — PROVEN

**Claim:** The gateway client performs no hashing and only issues control requests to the home miner.

**Evidence:**

| Check | File | Result |
|-------|------|--------|
| No mining keywords in JS | `apps/zend-home-gateway/index.html` | PASS — Zero references to hash functions, workers, mining pools, or stratum protocols |
| Network calls limited to daemon | `apps/zend-home-gateway/index.html:632` | PASS — Only `http://127.0.0.1:8080` called; endpoints are `/status`, `/health`, `/miner/start`, `/miner/stop`, `/miner/set_mode` |
| No hashing imports in daemon | `services/home-miner-daemon/daemon.py` | PASS — No hashlib, crypto imports; `MinerSimulator` class is a mock |
| Control request pattern | `services/home-miner-daemon/daemon.py:186-200` | PASS — POST handlers only, no submit/share logic |

**Conclusion:** The gateway client is a pure control-plane interface. It polls for status and sends control intents. No cryptographic mining work occurs anywhere in the client code path.

---

### 2. Control Request Flow — VERIFIED

```
Gateway Client (index.html)
  ├── POST /miner/start  → daemon.py:GatewayHandler.do_POST() → MinerSimulator.start()
  ├── POST /miner/stop   → daemon.py:GatewayHandler.do_POST() → MinerSimulator.stop()
  ├── POST /miner/set_mode → daemon.py:GatewayHandler.do_POST() → MinerSimulator.set_mode()
  └── GET /status        → daemon.py:GatewayHandler.do_GET() → MinerSimulator.get_snapshot()
```

**Key observation:** The daemon exposes a clean contract (`MinerSimulator` class) that mirrors what a real miner backend would provide. This is explicitly documented in `daemon.py:9-11`:

> "This is a milestone 1 simulator that exposes the same contract a real miner backend will use."

---

### 3. Pairing Token Replay Protection — PARTIAL

**Finding:** Token replay is partially protected.

**What exists:**
- Device name uniqueness enforced (`store.py:99-101`)
- Single pairing record per device name

**What is missing:**
- Pairing tokens (UUID v4) are created (`store.py:86-90`) but not validated on use
- The `token_used` field in `GatewayPairing` is set to `False` but never checked
- No expiration enforcement on tokens

**Implication:** For milestone 1 (LAN-only, trusted network), this is acceptable. Token binding should be added before remote access is enabled.

---

### 4. Stale Snapshot Detection — IMPLEMENTED

**Finding:** Snapshots include a `freshness` timestamp.

```python
# daemon.py:147
"freshness": datetime.now(timezone.utc).isoformat(),
```

**Gap:** The gateway client UI (`index.html:669-672`) displays the freshness timestamp but does not implement stale detection (e.g., alert if snapshot is older than 30 seconds).

```javascript
// index.html:669-672 — displays but does not validate
if (state.freshness) {
    const date = new Date(state.freshness);
    freshnessEl.textContent = date.toLocaleTimeString();
}
```

**Recommendation:** Add a stale threshold check in `fetchStatus()` that shows the alert banner if `Date.now() - freshness > STALE_THRESHOLD_MS`.

---

### 5. Controller Conflict Detection — CONTRACT DEFINED, NOT IMPLEMENTED

**Finding:** The event spine contract defines `status: 'accepted' | 'rejected' | 'conflicted'` but the daemon does not generate `conflicted` events.

**Contract (event-spine.md:78):**
```typescript
status: 'accepted' | 'rejected' | 'conflicted';
```

**Current implementation (spine.py:119-133):**
```python
def append_control_receipt(command, mode, status, principal_id):
    # status is set by caller (cli.py:156)
    # 'conflicted' is never passed
```

**Gap:** When two controllers issue conflicting commands, the system records the second as `accepted` rather than detecting the conflict. The `conflicted` status is dead code in the current implementation.

---

### 6. Restart Recovery — VERIFIED

**Finding:** State persistence works correctly.

| State File | Purpose | Persistence |
|------------|---------|-------------|
| `state/principal.json` | Principal identity | Survives restart |
| `state/pairing-store.json` | Paired devices | Survives restart |
| `state/event-spine.jsonl` | Append-only event log | Survives restart |

**Daemon restart behavior:**
- In-memory `MinerSimulator` state resets to `STOPPED` (lines 63-70)
- This is correct: the daemon controls a remote miner that may have changed state independently

---

### 7. Audit Script Quality — BASIC

**Finding:** `scripts/no_local_hashing_audit.sh` provides minimal coverage.

**Strengths:**
- Checks for mining-related code patterns
- Links to product promise ("gateway client issues control requests only")

**Limitations:**
- Grep pattern `grep -v "hashrate"` is fragile (will miss `hashrate` variations)
- No actual process inspection (commented out at line 48)
- No runtime verification of network traffic

**Recommendation:** The audit is sufficient for milestone 1 but should be enhanced with actual packet capture or strace verification before production.

---

## Gap Summary

| Gap | Severity | Milestone |
|-----|----------|-----------|
| No token expiration enforcement | Low | Pre-remote-access |
| No stale snapshot threshold check in UI | Low | Milestone 1 |
| `conflicted` status never generated | Medium | Milestone 1 |
| Audit script lacks runtime verification | Medium | Pre-production |

---

## Honest Assessment

### What This Codebase Gets Right

1. **Clean separation of concerns** — Gateway client is HTML/JS only; daemon is Python with clear module boundaries (`daemon.py`, `store.py`, `spine.py`, `cli.py`)

2. **Explicit milestone 1 contract** — `daemon.py` explicitly states it is a simulator; the same HTTP API contract will be used with real miner hardware

3. **Capability scoping** — `observe` and `control` capabilities are checked before allowing operations (`cli.py:47-54`, `cli.py:134-140`)

4. **Event spine as source of truth** — All state changes flow through the append-only journal; inbox is a derived view

5. **LAN-only binding** — `daemon.py:34` binds to `127.0.0.1` by default; production would use LAN interface

### What Needs Attention Before Production

1. **Conflict detection** — The `conflicted` control receipt status is defined but never used
2. **Token lifecycle** — Pairing tokens are created but not validated or expired
3. **Stale detection** — Freshness timestamp exists but client doesn't act on it

### This Review Is Not

- A security audit (requires dedicated penetration testing)
- A performance review (no load testing infrastructure)
- A code quality review (style/linting handled separately)

---

## Rerun Instructions

To reproduce this review:

```bash
# 1. Clone and enter repo
cd /home/r/.fabro/runs/20260320-01KM4ZXHYCNAQPPH93KJR7Q4BT/worktree

# 2. Bootstrap daemon
./scripts/bootstrap_home_miner.sh

# 3. Verify gateway client code (no hashing)
grep -E "(worker|webworker|hash|mining|stratum)" apps/zend-home-gateway/index.html
# Expected: no output

# 4. Verify network calls only to control endpoints
grep -E "fetch\(" apps/zend-home-gateway/index.html
# Expected: only /status, /health, /miner/*

# 5. Run pairing token test
./scripts/pair_gateway_client.sh --client test-replay --capabilities observe
./scripts/pair_gateway_client.sh --client test-replay --capabilities observe
# Expected: error "already paired"

# 6. Verify snapshot freshness
curl -s http://127.0.0.1:8080/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('freshness:', d.get('freshness'))"

# 7. Check controller conflict (should see accepted/rejected, not conflicted)
cd services/home-miner-daemon
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
python3 cli.py events --kind control_receipt --limit 3

# 8. Test restart recovery
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh --daemon
python3 -c "from store import has_capability; print('alice-phone still paired:', has_capability('alice-phone', 'control'))"

# 9. Run audit script
./scripts/no_local_hashing_audit.sh --client alice-phone
echo "Audit exit code: $?"
```
