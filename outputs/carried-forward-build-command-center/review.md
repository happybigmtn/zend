# Zend Home Command Center — Carried Forward Review

**Lane:** `carried-forward-build-command-center`
**Status:** Reviewed — carried forward to genesis plans 002–014
**Generated:** 2026-03-22
**Reviewer:** Genesis Sprint

---

## Summary

The first honest reviewed slice of the Zend Home Command Center is complete at the spec and scaffolding level. The happy path is functional: daemon starts, pairing creates records, status reads succeed, control commands are enforced by capability, and the event spine appends events. Four significant gaps require genesis-plan treatment: token replay prevention, automated tests, Hermes adapter implementation, and encrypted inbox. The review below is honest about what was tested, what was inferred, and what remains unverified.

---

## What Was Reviewed

### Repo Scaffolding ✓

```
apps/zend-home-gateway/index.html           Mobile-first gateway client (680 lines)
services/home-miner-daemon/
  daemon.py                                 Threaded HTTP API, 5 endpoints
  store.py                                  Principal + pairing store (JSON persistence)
  spine.py                                  Append-only JSONL event journal
  cli.py                                    CLI interface with capability checks
scripts/
  bootstrap_home_miner.sh                   Daemon bootstrap
  pair_gateway_client.sh                    Client pairing
  read_miner_status.sh                      Status reads
  set_mining_mode.sh                        Miner control
  hermes_summary_smoke.sh                  Hermes summary append test
  no_local_hashing_audit.sh                 Security audit stub
references/
  inbox-contract.md                         PrincipalId + pairing contract
  event-spine.md                            Event spine contract
  hermes-adapter.md                        Hermes adapter contract (interface only)
  error-taxonomy.md                         10 named error classes
  design-checklist.md                       Design compliance checklist
  observability.md                          Structured logging contract
```

### Home Miner Daemon

**`daemon.py` — Threaded HTTP server, zero dependencies.**
Five endpoints (`/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`). LAN-only binding (`127.0.0.1:8080` default). `MinerSimulator` holds state in-memory; restart resets mode and payout-target. Acceptable for milestone 1.

**`store.py` — Principal and pairing store.**
JSON file persistence at `state/principal.json` and `state/pairing-store.json`. Creates `PrincipalId` (UUID v4), generates pairing tokens, records capabilities. **Known gap: `token_used` is set to `False` at creation but never set to `True`. Token replay prevention is defined but unforced. Risk: HIGH. Mapped to genesis plan 006.**

**`spine.py` — Append-only event journal.**
JSONL persistence at `state/event-spine.jsonl`. Seven event kinds defined per `event-spine.md` contract. Source-of-truth constraint enforced: all events flow through spine first, inbox is derived. **Known gap: plaintext JSONL, no encryption. Risk: MEDIUM. Mapped to genesis plan 012.**

**`cli.py` — CLI interface.**
Capability checks on status and control operations. `GatewayUnauthorized` enforced. Clean JSON error responses.

### Gateway Client

**`apps/zend-home-gateway/index.html` — 680 lines, vanilla HTML/CSS/JS.**

Design system compliance (per `DESIGN.md` and `design-checklist.md`):

| Requirement | Status |
|-------------|--------|
| Space Grotesk headings (600–700) | ✓ |
| IBM Plex Sans body (400–500) | ✓ |
| IBM Plex Mono for status values | ✓ |
| Calm domestic palette | ✓ |
| Mobile-first, 420px max-width | ✓ |
| Bottom tab bar, 4 destinations | ✓ |
| Status Hero with freshness | ✓ |
| Mode Switcher (3 modes) | ✓ |
| Receipt Card style | ✓ |
| 44x44 touch targets | ✓ |
| Screen reader landmarks | ✓ |
| Color + icon for status (not color alone) | ✓ |
| Reduced-motion fallback | ✗ Not yet |
| Live regions for new receipts | ✗ Not yet |

**Not implemented:**
- Real inbox view (empty state only)
- Hermes panel (shows "not connected")
- Real-time spine polling
- Reduced-motion media query fallback

### CLI Scripts

Six scripts built with argument parsing, error handling, and colored output. Happy path verified via smoke testing.

### Reference Contracts

Six contracts define the durable surface. All are consistent with each other and with `DESIGN.md`. No internal contradictions found.

---

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared across systems | ✓ | `store.py` creates; `spine.py` references |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1` default |
| Capability scopes (observe/control) | ✓ | `store.py` records; `cli.py` enforces |
| Off-device mining | ✓ | Simulator; audit stub passes |
| Hermes adapter | ⚠ | Contract only; no Python impl |
| Token replay prevention | ✗ | Defined; not enforced |
| Token expiration enforcement | ✗ | Stored; not checked |
| Event encryption | ✗ | Plaintext JSONL |
| Automated tests | ✗ | None exist |
| CI/CD | ✗ | None exists |

---

## Error Taxonomy Compliance

| Error | Defined | Enforced | Notes |
|-------|---------|----------|-------|
| `PairingTokenExpired` | ✓ | ✗ | `token_expires_at` stored; not checked |
| `PairingTokenReplay` | ✓ | ✗ | `token_used` never set True |
| `GatewayUnauthorized` | ✓ | ✓ | Enforced in `cli.py` |
| `GatewayUnavailable` | ✓ | ✓ | Enforced in `daemon_call()` |
| `MinerSnapshotStale` | ⚠ | ✗ | `freshness` field present; no stale detection |
| `ControlCommandConflict` | ✓ | ✗ | Not enforced; in-memory state |
| `EventAppendFailed` | ✓ | ✗ | No retry logic; append fails silently |
| `LocalHashingDetected` | ✓ | ⚠ | Audit stub passes; not live-detected |
| `InvalidPrincipalId` | ✓ | ⚠ | Store validates UUID format |
| `DaemonPortInUse` | ✓ | ⚠ | Detected at bind; recovery hint given |

---

## Security Posture

### What works

- LAN-only binding prevents internet exposure
- Capability scoping prevents observers from controlling
- Token-based pairing with expiration timestamps
- No hashing code in daemon (audit passes)

### What needs work (by severity)

**HIGH — Token replay prevention.** `token_used` is never set to `True`. Any captured pairing token is valid indefinitely.

**HIGH — No daemon authentication.** Any process on the local machine can issue control commands. Acceptable for LAN-only milestone but must be documented and revisited in plan 011.

**MEDIUM — Token expiration not enforced.** `token_expires_at` is stored but never checked at request time.

**MEDIUM — Plaintext event spine.** All events visible to anyone with filesystem access. Encryption deferred to plan 012.

**LOW — No rate limiting on control commands.** Acceptable for milestone 1.

---

## Functional Verification

### Happy path (verified by smoke testing)

```
./scripts/bootstrap_home_miner.sh
  → Daemon starts on 127.0.0.1:8080
  → Principal created at state/principal.json
  → Pairing store initialized at state/pairing-store.json

curl http://127.0.0.1:8080/health
  → "OK"

./scripts/pair_gateway_client.sh --client alice-phone
  → Pairing event appended to spine
  → Success: device_name, capabilities, pairing_token

./scripts/read_miner_status.sh --client alice-phone
  → MinerSnapshot returned (status, mode, hashrate, uptime, freshness)
  → Exit code 0

./scripts/set_mining_mode.sh --client alice-phone --mode balanced
  → Control receipt appended to spine
  → Acknowledgement printed
  → Exit code 0
```

### Authorization enforcement (verified)

```
# Observer capability cannot control
./scripts/set_mining_mode.sh --client observer-phone --mode performance
  → {"success": false, "error": "unauthorized"}
  → Exit code 1
```

### Error cases (documented; some not exercised)

```
# Daemon offline
./scripts/read_miner_status.sh --client alice-phone
  → {"error": "daemon_unavailable"}  [not exercised in review]

# Invalid mode
./scripts/set_mining_mode.sh --client alice-phone --mode turbo
  → Error: Invalid mode  [not exercised in review]
```

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token replay attack | HIGH | Genesis plan 006 |
| Plaintext event spine | MEDIUM | Genesis plan 012 |
| No daemon auth (LAN-only constraint) | HIGH | Document; revisit in plan 011 |
| No automated tests | HIGH | Genesis plan 004 |
| Hermes adapter not implemented | MEDIUM | Genesis plan 009 |
| In-memory state lost on restart | LOW | Acceptable for milestone 1 |
| No CI/CD pipeline | MEDIUM | Genesis plan 005 |

---

## Verification Commands

```bash
# Bootstrap daemon
./scripts/bootstrap_home_miner.sh

# Health check
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Control miner
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# View recent events
cd services/home-miner-daemon && python3 cli.py events --limit 5

# View CLI help
cd services/home-miner-daemon && python3 cli.py --help

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

---

## Verdict

**APPROVED FOR CARRY-FORWARD.**

The implementation satisfies the core requirements:

- Zero-dependency daemon runs LAN-only ✓
- Pairing creates `PrincipalId` and capability record ✓
- Status endpoint returns `MinerSnapshot` with freshness ✓
- Control requires `control` capability ✓
- Events append to spine ✓
- Gateway client demonstrates mobile-first command center ✓
- Design system compliance verified ✓
- No local hashing (audit passes) ✓

**Four gaps require genesis-plan treatment before production readiness:**

1. Token replay prevention (genesis plan 006) — highest priority
2. Automated tests (genesis plan 004)
3. Hermes adapter implementation (genesis plan 009)
4. Encrypted inbox (genesis plans 011, 012)

**Next:** Genesis plans 002–014 address remaining work. Token enforcement and automated tests are the highest priority for the next sprint.
