# Zend Home Command Center — Carried-Forward Specification

**Lane:** `carried-forward-build-command-center`
**Status:** Milestone 1 — Implementation Pending Execution
**Source:** `plans/2026-03-19-build-zend-home-command-center.md`
**Parent spec:** `specs/2026-03-19-zend-product-spec.md`

---

## What This Document Is

This spec defines the contracts, interfaces, and acceptance criteria for the
Zend Home Command Center milestone 1 implementation. It is the authoritative
reference for what must exist and what it must do when the lane is executed.
All implementation must trace back to a line item in this document.

This spec is **not** a plan. It does not describe step-by-step how to build
things — that is the job of `plans/2026-03-19-build-zend-home-command-center.md`.
This spec describes **what** the implementation must produce.

---

## Scope of Milestone 1

Milestone 1 delivers the smallest honest Zend product: a thin mobile-shaped
command center paired to a LAN-only home-miner control service, with an
encrypted operations inbox and a Hermes adapter.

The following are **in scope** for milestone 1:

- a LAN-only home-miner daemon that never exposes a public control surface
- a thin mobile-shaped gateway client that pairs, reads status, and issues safe
  control commands
- a `PrincipalId` contract shared by gateway pairing records and the future inbox
- a private append-only event spine that is the single source of truth for all
  operational events
- an encrypted operations inbox that projects from the event spine
- a Zend-native gateway contract with a Hermes adapter (observe-only + summary
  append for milestone 1)
- automated tests covering the error scenarios, trust ceremony states, Hermes
  delegation boundaries, event spine routing, and off-device mining proof

The following are **explicitly out of scope** for milestone 1 and must not
block it:

- internet-facing or remote gateway access
- payout-target mutation
- rich conversation UX beyond the operations inbox
- Hermes-initiated miner control (Hermes is observe-only in milestone 1)
- dark-mode expansion beyond the first design system pass

---

## Data Types

### PrincipalId

```typescript
// A stable, opaque UUID v4 identifying one Zend principal (human or agent).
type PrincipalId = string;  // UUID v4
```

Every gateway pairing record and every event-spine item references the same
`PrincipalId` for this principal. The inbox must not use a separate identity
namespace.

### GatewayCapability

```typescript
// Milestone 1 supports exactly two scopes.
type GatewayCapability = 'observe' | 'control';
```

An `observe`-only client may read miner status. A `control` client may also
issue safe mode-change commands. Payout-target mutation is not a milestone 1
capability.

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

The daemon returns this to clients. Every snapshot must carry a `freshness`
field so clients can distinguish live data from stale data without guessing.

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

These are the seven event kinds milestone 1 must route through the event spine.
No event may be written only to the inbox or only to a feature-specific store —
the event spine is the source of truth and the inbox is a projection.

---

## Interfaces

### Daemon HTTP API (LAN-only)

The home-miner daemon must expose these endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `200 OK` with `{"status":"ok"}` when the daemon is running |
| GET | `/status` | Returns the current `MinerSnapshot` JSON |
| POST | `/miner/start` | Starts mining (requires `control` capability) |
| POST | `/miner/stop` | Stops mining (requires `control` capability) |
| POST | `/miner/set_mode` | Body: `{"mode":"paused"\|"balanced"\|"performance"}` (requires `control`) |

The daemon must bind to a private local interface. Binding to `0.0.0.0` or
an internet-facing address is not acceptable for milestone 1. The default
binding must be `127.0.0.1` or an explicit operator-chosen private address.

### CLI Script Interface

Each script must live at the path listed and expose the listed interface.
All scripts must be executable and must produce the described output or exit
code.

**`scripts/fetch_upstreams.sh`**

```
./scripts/fetch_upstreams.sh
```

Reads `upstream/manifest.lock.json` and checks out each pinned upstream into
`third_party/<name>`. Idempotent: rerunning updates to the pinned revision.

**`scripts/bootstrap_home_miner.sh`**

```
./scripts/bootstrap_home_miner.sh
```

Starts the daemon, creates a deterministic local `PrincipalId`, and emits a
pairing token or bundle for use by `pair_gateway_client.sh`. Must be safe to
re-run: if state already exists, it must either reuse it or wipe and recreate
deterministically.

**`scripts/pair_gateway_client.sh`**

```
./scripts/pair_gateway_client.sh --client <name>
```

Creates a durable local client record containing the client's `PrincipalId` and
capability set. Prints a clear success line including the human-readable device
name. Must fail with `PairingTokenExpired` or `PairingTokenReplay` for invalid
tokens.

**`scripts/read_miner_status.sh`**

```
./scripts/read_miner_status.sh --client <name>
```

Returns the current `MinerSnapshot` including `freshness` timestamp. If the
daemon is offline, exits non-zero with `GatewayUnavailable`. If the snapshot is
older than a defined threshold, returns `MinerSnapshotStale` alongside the data.

**`scripts/set_mining_mode.sh`**

```
./scripts/set_mining_mode.sh --client <name> --mode <paused|balanced|performance>
./scripts/set_mining_mode.sh --client <name> --action <start|stop>
```

Issues a safe control command to the home miner and prints an explicit
acknowledgement. Must fail with `GatewayUnauthorized` if the client lacks
`control` capability. Must fail with `ControlCommandConflict` if a competing
in-flight command exists.

**`scripts/hermes_summary_smoke.sh`**

```
./scripts/hermes_summary_smoke.sh --client <name>
```

Proves Hermes can connect through the Zend adapter, append one delegated summary
event to the encrypted operations inbox, and that Zend capability checks are
enforced. Exits non-zero with `GatewayUnauthorized` if Hermes lacks authority.

**`scripts/no_local_hashing_audit.sh`**

```
./scripts/no_local_hashing_audit.sh --client <name>
```

Inspects the gateway client process tree and fails non-zero (exit 1) if any
hashing libraries, mining threads, or CPU-bound mining workers are detected.
Exit 0 means no local hashing detected.

---

## Required Reference Documents

The following must exist at these paths before milestone 1 is considered
complete. Each defines a contract that the implementation must satisfy.

| Path | Purpose |
|------|---------|
| `references/inbox-contract.md` | Defines `PrincipalId`, gateway pairing record schema, and the constraint that future inbox metadata must reuse the same identifier |
| `references/event-spine.md` | Defines the seven `EventKind` values, event schema with versioning, payload schemas, source-of-truth constraint, and routing rules for milestone 1 |
| `references/error-taxonomy.md` | Names every error class used in milestone 1: `PairingTokenExpired`, `PairingTokenReplay`, `GatewayUnauthorized`, `GatewayUnavailable`, `MinerSnapshotStale`, `ControlCommandConflict`, `EventAppendFailed`, `LocalHashingDetected` |
| `references/hermes-adapter.md` | Defines how Hermes Gateway connects to the Zend-native contract, which capabilities are delegable, and which event-spine items Hermes may read or append |
| `references/gateway-proof.md` | Contains transcripts proving every end-to-end scenario works, with exact commands and expected output |
| `references/onboarding-storyboard.md` | Narrative walkthrough of the Zend Home onboarding and trust ceremony |
| `references/observability.md` | Structured log events, metrics, and audit-log records required for milestone 1 |

---

## Required Tests

The following automated tests must exist and pass. Each maps to a named error
or codepath in the plan.

| Test | What It Validates |
|------|-------------------|
| `tests/test_pairing_expired_token.py` | A replayed or expired pairing token is rejected with `PairingTokenReplay` |
| `tests/test_pairing_duplicate_client.py` | Two clients with the same name are rejected or renamed deterministically |
| `tests/test_observer_cannot_control.py` | An `observe`-only client receives `GatewayUnauthorized` on any control call |
| `tests/test_stale_snapshot.py` | A `MinerSnapshot` with an old `freshness` field is flagged as stale, not silently treated as live |
| `tests/test_conflicting_commands.py` | Two in-flight `set_mode` calls produce `ControlCommandConflict`, not two independent successes |
| `tests/test_daemon_restart_recovery.py` | After a daemon restart, a previously paired client can reconnect and read status without re-pairing |
| `tests/test_trust_ceremony_states.py` | The pairing flow enforces the state machine: unpaired → observer → controller → receipt |
| `tests/test_hermes_adapter_boundary.py` | Hermes cannot read or write beyond the observe-only + summary-append scope |
| `tests/test_event_spine_routing.py` | All seven `EventKind` values are appended to the spine and retrievable via inbox projection |
| `tests/test_local_hashing_audit.py` | The audit script detects a process tree that includes mining workers and exits non-zero |
| `tests/test_empty_inbox.py` | The inbox renders a warm empty state with a primary next action, not a generic "No items found" |
| `tests/test_control_denied_copy.py` | An observe-only client attempting control sees clear copy explaining why, not a generic error |
| `tests/test_reduced_motion.py` | All animated transitions have a `prefers-reduced-motion` fallback that keeps the UI understandable |

---

## Acceptance Criteria

Milestone 1 is complete only when all of the following are true:

1. A new contributor reading only this repository understands that Zend is a
   private command center, not a public feed and not a new chain.
2. The implementation proves the mobile gateway into a home miner without any
   mining work occurring on the client device.
3. The daemon binds only to a private local interface; no public control
   surface is exposed.
4. Gateway authority is limited to `observe` and `control` scopes; a client
   without `control` cannot issue mode-change commands.
5. All seven `EventKind` values route through the event spine; the inbox is a
   projection, not a second store.
6. Hermes connects only through the Zend adapter with explicitly delegated
   authority.
7. Every named error class has a test that triggers it and verifies the
   correct response.
8. The gateway proof transcript in `references/gateway-proof.md` shows all
   end-to-end flows with exact commands and output.
9. The visual design follows `DESIGN.md`: calm domestic language, not crypto
   exchange aesthetics.
10. Touch targets are at least 44×44 logical pixels, text is at least 16px
    equivalent, and color is never the only signal for miner health.

---

## Supersession

This spec supersedes the draft output at `outputs/home-command-center/`. That
earlier artifact described aspirational implementation and is now stale.
