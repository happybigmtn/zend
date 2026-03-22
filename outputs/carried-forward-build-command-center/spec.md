# Zend Home Command Center — Capability Spec

**Status:** Carried Forward — Milestone 1 Polish
**Supersedes:** `outputs/home-command-center/spec.md`
**Inputs:** `plans/2026-03-19-build-zend-home-command-center.md`,
`specs/2026-03-19-zend-product-spec.md`,
`DESIGN.md`

---

## Purpose / User-Visible Outcome

A paired mobile gateway client can read live miner status, issue safe control
actions (start / stop / mode), and receive pairing approvals, control receipts,
Hermes summaries, and miner alerts in one encrypted operations inbox — all while
the daemon proves it is bound to a LAN interface and the gateway client proves it
performs no on-device hashing.

## Whole-System Goal

Prove the first honest Zend product slice: a thin mobile command center paired
to a home-miner daemon over LAN, with an encrypted event spine as the single
source of truth for all operational receipts and a Hermes adapter that connects
through delegated authority only.

## Frontier Tasks Remaining

This slice addresses the following carried-forward items from genesis planning:

| # | Task | Genesis Plan | This Spec Covers |
|---|---|---|---|
| 1 | Automated tests for error scenarios | 004 | Full test taxonomy below |
| 2 | Tests for trust ceremony state | 004 | `TrustCeremonyStateTest` |
| 3 | Tests for Hermes delegation boundaries | 009 | `HermesDelegationBoundaryTest` |
| 4 | Tests for event spine routing | 012 | `EventSpineRoutingTest` |
| 5 | Document gateway proof transcripts | 008 | `references/gateway-proof.md` |
| 6 | Implement Hermes adapter | 009 | `hermes-adapter.md` + integration |
| 7 | Implement encrypted operations inbox | 011, 012 | `references/event-spine.md` + `references/inbox-contract.md` |
| 8 | LAN-only with formal test proof | 004 | `daemon.py` binds `127.0.0.1`; test verifies |

## Scope

### In Scope

- Repo scaffolding: `apps/`, `services/home-miner-daemon/`, `scripts/`,
  `references/`, `upstream/`, `state/`
- Design doc: `docs/designs/2026-03-19-zend-home-command-center.md`
- Inbox contract: `references/inbox-contract.md` — `PrincipalId` (UUID v4),
  gateway pairing record, future inbox metadata reuse constraint
- Event spine contract: `references/event-spine.md` — 7 `EventKind` variants,
  append-only journal, spine-as-source-of-truth constraint
- Upstream manifest: `upstream/manifest.lock.json` + `scripts/fetch_upstreams.sh`
- Home-miner daemon: `services/home-miner-daemon/daemon.py` binding
  `127.0.0.1:8080`, HTTP/JSON API, `/health`, `/status`, `/miner/start`,
  `/miner/stop`, `/miner/set_mode`
- Gateway client: `apps/zend-home-gateway/index.html` — mobile-first web UI,
  four-tab navigation (Home / Inbox / Agent / Device), `StatusHero`,
  `ModeSwitcher`, `ReceiptCard`
- Six operator scripts: `bootstrap_home_miner.sh`,
  `pair_gateway_client.sh`, `read_miner_status.sh`,
  `set_mining_mode.sh`, `hermes_summary_smoke.sh`,
  `no_local_hashing_audit.sh`
- Error taxonomy: `references/error-taxonomy.md`
- Gateway proof: `references/gateway-proof.md`
- Hermes adapter contract: `references/hermes-adapter.md`
- Design checklist: `references/design-checklist.md`
- Onboarding storyboard: `references/onboarding-storyboard.md`
- Observability contract: `references/observability.md`

### Out of Scope

- Remote internet access (LAN-only enforced)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Multi-device sync
- Dark-mode expansion

## Architecture / Runtime Contract

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

One stable identity owned by the operator. Referenced by gateway pairing
records, event-spine items, and all future inbox metadata. Must not be split
across separate auth namespaces.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Phase one uses exactly two scopes. `observe` reads status. `control` issues
start / stop / mode commands. Payout-target mutation is explicitly deferred.

### MinerSnapshot

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601
}
```

The daemon returns this to clients. `freshness` must be present on every
response so the client can distinguish live from stale data.

### EventKind

```typescript
type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';
```

The event spine is the source of truth. The inbox is a derived projection.
Engineers must not write some event variants only to the inbox and others only
to the spine.

### Daemon API

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | none | Liveness check |
| `/status` | GET | `observe` | MinerSnapshot with freshness |
| `/miner/start` | POST | `control` | Start mining |
| `/miner/stop` | POST | `control` | Stop mining |
| `/miner/set_mode` | POST | `control` | Set mode body `{mode}` |

### LAN Constraint

The daemon **must** bind `127.0.0.1:8080` in milestone 1. Binding to `0.0.0.0`
or any public interface is not acceptable. A test must verify this binding on
startup and fail if the daemon attempts a wider bind.

### Hermes Adapter Contract

Hermes connects through `references/hermes-adapter.md`. Milestone 1 Hermes
authority is **observe-only plus summary append** into the event spine. Direct
miner control through Hermes is deferred. The adapter must enforce Zend capability
checks before forwarding any action to the daemon.

## Automated Test Taxonomy

Tests must be implemented as executable scripts under `scripts/tests/` or as
pytest/unittest modules under `services/home-miner-daemon/tests/`.

### Error Scenario Tests

| Test | Input / Action | Expected Outcome |
|---|---|---|
| `test_expired_pairing_token` | Pair with expired token | `PairingTokenExpired`; pairing rejected |
| `test_replayed_pairing_token` | Pair same token twice | `PairingTokenReplay`; second attempt rejected; audit event logged |
| `test_observer_cannot_control` | POST `/miner/start` as `observe` client | `GatewayUnauthorized`; command rejected |
| `test_conflicting_control_commands` | Two concurrent mode-change requests | `ControlCommandConflict`; one succeeds, one rejected |
| `test_stale_snapshot_accepted_with_flag` | Read status after snapshot TTL | Snapshot returned with `stale: true`; no silent display-as-fresh |
| `test_daemon_restart_recovery` | Kill daemon, restart, re-pair | Client recovers; previous pairing record usable |
| `test_event_append_failure_surfaces` | Block spine write, issue control | `EventAppendFailed` surfaced to user; command not lost |
| `test_hermes_unauthorized_action` | Hermes adapter receives control request | `GatewayUnauthorized`; Hermes sees explicit error |

### Trust Ceremony Tests

| Test | State Transition | Assertion |
|---|---|---|
| `test_trust_ceremony_unpaired_to_observer` | Valid ceremony → `observe` grant | Client record has `observe`; no `control` |
| `test_trust_ceremony_observer_upgrades_to_controller` | Second ceremony with `control` grant | Client record updated to `control` |
| `test_trust_ceremony_revoke_reverts_to_observer` | Revoke `control` | Client record reverts to `observe` |
| `test_trust_ceremony_revoke_clears_all` | Full reset | No pairing record found for client |

### Hermes Delegation Boundary Tests

| Test | Action | Assertion |
|---|---|---|
| `test_hermes_observe_only_no_control_forward` | Hermes sends `/miner/start` | Adapter rejects; daemon never called |
| `test_hermes_summary_appends_to_spine` | Hermes calls summary endpoint | Event appended with kind `hermes_summary` |
| `test_hermes_cannot_read_other_clients` | Hermes requests `/status` of another principal | `GatewayUnauthorized` |

### Event Spine Routing Tests

| Test | Event Kind | Routing Assertion |
|---|---|---|
| `test_pairing_events_route_to_spine` | `pairing_granted` | Appears in spine; appears in inbox projection |
| `test_control_receipts_route_to_spine` | `control_receipt` | Appears in spine; appears in inbox projection |
| `test_hermes_summary_routes_to_spine` | `hermes_summary` | Appears in spine; appears in inbox projection |
| `test_miner_alert_routes_to_spine` | `miner_alert` | Appears in spine; appears in inbox projection |
| `test_user_message_routes_to_spine` | `user_message` | Appears in spine; appears in inbox projection |
| `test_inbox_is_projection_not_source` | Direct inbox write attempt | Rejected; only spine append is canonical |

### LAN-Only Verification Test

| Test | Assertion |
|---|---|
| `test_daemon_binds_localhost_only` | `daemon.py` socket bound to `127.0.0.1`; no `0.0.0.0` or public interface |

### Accessibility / UX State Tests

| Test | State | Assertion |
|---|---|---|
| `test_empty_inbox_shows_warm_copy` | Inbox with no events | Non-generic warm copy; primary next action visible |
| `test_status_loading_shows_shimmer` | Status request pending | Shimmer or skeleton; no blank flash |
| `test_stale_status_shows_explicit_warning` | Snapshot stale | Warning banner; color not sole signal |
| `test_observe_client_mode_switch_disabled` | Observer views mode switch | Control disabled; copy explains capability gap |

## Acceptance Criteria

1. All six operator scripts execute against the live daemon and produce the
   transcripts documented in `references/gateway-proof.md`.
2. Every named error in `references/error-taxonomy.md` maps to exactly one
   `assert`-able code path with a passing test.
3. The daemon binds `127.0.0.1:8080` and refuses to bind any wider interface in
   milestone 1. A test verifies this on every startup.
4. The event spine is the sole source of truth. No feature writes its own
   canonical store. The inbox is a read-only projection.
5. Hermes connects only through the adapter and only with observe-plus-summary
   authority. The adapter enforces Zend capability checks.
6. The `PrincipalId` created at bootstrap is reused by all subsequent features.
   No feature creates a second identity namespace.
7. The gateway client proves it performs no on-device hashing via the
   `no_local_hashing_audit.sh` transcript in `references/gateway-proof.md`.
8. Every feature surface has documented loading, empty, error, success, and
   partial states as defined in the interaction state coverage table.
9. All AI-slop guardrails from `DESIGN.md` are respected: no generic dashboard
   widgets, no hero-gradient CTAs, no "No items found" empty states without a
   next action.
10. Genesis plan 004 tests (trust ceremony, error scenarios, LAN-only proof)
    are implemented and passing.
11. Genesis plan 009 tests (Hermes delegation boundaries) are implemented and
    passing.
12. Genesis plans 011 and 012 tests (event spine routing, encrypted inbox) are
    implemented and passing.
13. `references/gateway-proof.md` contains copyable transcripts for every proof
    step with exact expected output.

## Failure Handling

If the daemon fails to start because the port is occupied, it must exit with
`GatewayUnavailable` and a recovery hint listing the process using the port.

If the event spine write fails, the control action must not be acknowledged.
The error `EventAppendFailed` must be returned to the client and logged.

If the gateway client is found to be performing local hashing, the audit script
must exit non-zero and log `LocalHashingDetected`. The daemon must not be
updated until this is resolved.

If a pairing token is replayed, the second attempt must be rejected and an
audit event must be written to the spine even though the pairing itself is
rejected.
