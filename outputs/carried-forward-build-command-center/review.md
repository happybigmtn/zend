# Zend Home Command Center — Review

**Status:** Milestone 1 — Carried Forward Review
**Generated:** 2026-03-22
**Parent Plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Genesis Plan:** `genesis/plans/001-master-plan.md`

## Summary

This review evaluates the first honest implementation slice of the Zend Home Command Center. The implementation satisfies the core requirements of the carried-forward plan with verified working behavior.

## What Was Verified

### Daemon API ✓

All endpoints verified working via curl:

```bash
$ curl http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

$ curl http://127.0.0.1:8080/status
{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}

$ curl -X POST http://127.0.0.1:8080/miner/start
{"success": true, "status": "MinerStatus.RUNNING"}

$ curl -X POST -H "Content-Type: application/json" -d '{"mode":"balanced"}' http://127.0.0.1:8080/miner/set_mode
{"success": true, "mode": "MinerMode.BALANCED"}
```

**Note:** Daemon returns Python enum values (`MinerStatus.STOPPED`) instead of string literals (`stopped`). This is a known issue to address.

### Bootstrap Script ✓

```bash
$ bash scripts/bootstrap_home_miner.sh
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
{
  "principal_id": "87b28d71-9a10-4f17-80e9-2d5bcd76088b",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  ...
}
[INFO] Bootstrap complete
```

### Pairing Script ✓

```bash
$ bash scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
{
  "success": true,
  "device_name": "bob-phone",
  "capabilities": ["observe", "control"],
  ...
}
paired bob-phone
capability=observe,control
```

### Status Script ✓

```bash
$ bash scripts/read_miner_status.sh --client bob-phone
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  ...
}
status=MinerStatus.STOPPED
mode=MinerMode.PAUSED
freshness=2026-03-22T19:48:27.824319+00:00
```

### Control Script ✓

```bash
$ bash scripts/set_mining_mode.sh --client bob-phone --mode balanced
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
acknowledged=true
note='Action accepted by home miner, not client device'
```

### Hermes Summary Script ✓

```bash
$ bash scripts/hermes_summary_smoke.sh --client test-phone
event_id=9324f118-6b33-4404-b0d6-c20d4fc0d153
principal_id=408fe0b4-1b43-4651-b32a-311c2f34d83d
summary_appended_to_operations_inbox=true
```

### No Local Hashing Audit ✓

```bash
$ bash scripts/no_local_hashing_audit.sh --client test-phone
checked: client process tree
checked: local CPU worker count
result: no local hashing detected
Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
```

### Capability Enforcement ✓

Observe-only clients correctly rejected:

```bash
$ python3 cli.py control --client test-phone --action start
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

### Event Spine ✓

Events correctly append to `state/event-spine.jsonl`:
- `pairing_requested` events on pair
- `pairing_granted` events on pair
- `control_receipt` events on control actions
- `hermes_summary` events on Hermes smoke test

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared | ✓ | `store.py` creates; `spine.py` uses |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is view |
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 |
| Capability scopes | ✓ | observe/control in store.py |
| Off-device mining | ✓ | Simulator; audit passes |
| Hermes adapter | ✓ | Contract in `hermes-adapter.md` |

## Design System Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Typography (Space Grotesk, IBM Plex) | ✓ | Google Fonts loaded in index.html |
| Color system (Basalt, Slate, Moss) | ✓ | CSS variables defined |
| Mobile-first layout | ✓ | Single column, max-width 420px |
| Bottom tab navigation | ✓ | Fixed bottom nav, 4 tabs |
| Status Hero | ✓ | Shows status, mode, freshness |
| Mode Switcher | ✓ | 3-segment control |
| Touch targets (44x44) | ✓ | Min-height 44px on nav items |
| Reduced motion support | ✓ | CSS animation, respects prefers-reduced-motion |

## Known Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Python enum values in API response | Medium | `MinerStatus.STOPPED` instead of `stopped` |
| Token replay not enforced | Medium | `token_used` always False |
| Plaintext event storage | Low | Real encryption deferred |
| No event compaction | Low | Unbounded growth on restart |
| Hermes adapter not live | Medium | Only contract defined |

## What's Implemented

### Repo Scaffolding ✓

```
apps/zend-home-gateway/
  index.html
services/home-miner-daemon/
  __init__.py
  cli.py
  daemon.py
  spine.py
  store.py
scripts/
  bootstrap_home_miner.sh
  fetch_upstreams.sh
  hermes_summary_smoke.sh
  no_local_hashing_audit.sh
  pair_gateway_client.sh
  read_miner_status.sh
  set_mining_mode.sh
references/
  design-checklist.md
  error-taxonomy.md
  event-spine.md
  hermes-adapter.md
  inbox-contract.md
  observability.md
upstream/
  manifest.lock.json
state/
  (runtime data, gitignored)
```

### Output Artifacts ✓

```
outputs/home-command-center/
  spec.md
  review.md
outputs/carried-forward-build-command-center/
  spec.md
  review.md
genesis/
  plans/
    001-master-plan.md
```

## Gaps & Next Steps

### High Priority

1. **Automated Tests (Genesis 004)**
   - Error scenario tests
   - Trust ceremony tests
   - Event spine routing tests

2. **Token Enforcement (Genesis 006)**
   - Enforce `token_used` flag
   - Reject replayed tokens

3. **Security Hardening (Genesis 003)**
   - Fix Python enum serialization
   - Add input validation
   - Harden against injection

### Medium Priority

4. **Hermes Adapter (Genesis 009)**
   - Implement live Hermes Gateway connection
   - Test delegated authority

5. **Inbox UX (Genesis 012)**
   - Rich inbox view
   - Grouped receipts
   - Read state tracking

6. **Observability (Genesis 007)**
   - Structured logging
   - Metrics collection

### Lower Priority

7. **CI/CD Pipeline (Genesis 005)**
   - GitHub Actions workflow
   - Automated testing

8. **Documentation (Genesis 008)**
   - Gateway proof transcripts
   - API documentation

9. **Remote Access (Genesis 011)**
   - LAN-to-WAN bridge
   - Authentication

10. **Multi-Device & Recovery (Genesis 013)**
    - Recovery flows
    - Device management

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Daemon crashes on invalid input | Low | Medium | Add input validation (Genesis 003) |
| Event spine grows unbounded | Medium | Low | Add compaction (deferred) |
| Security vulnerability in pairing | Medium | High | Token enforcement (Genesis 006) |
| Hermes adapter incompatible | Medium | Medium | Define contract first (done) |

## Review Verdict

**APPROVED — First honest reviewed slice is complete.**

The implementation satisfies the carried-forward plan's core requirements:

- [x] Repo scaffolding in place
- [x] Contracts defined (PrincipalId, Event Spine)
- [x] Upstream manifest with fetch script
- [x] Home-miner daemon (simulator) running LAN-only
- [x] Gateway client UI demonstrates mobile-first command center
- [x] All required scripts executable and verified
- [x] Output artifacts delivered
- [x] Design system compliance verified
- [x] Capability enforcement working

**Next:** Execute genesis plans 002-014 to address remaining work.
