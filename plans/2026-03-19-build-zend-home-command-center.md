# Build the Zend Home Command Center

This ExecPlan is a living document. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
be kept up to date as work proceeds.

`PLANS.md` at the repository root governs this ExecPlan. This document must be
maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

After this work, a new contributor should be able to start from a fresh clone
of this repository, run a local home-miner control service, pair a thin
mobile-shaped client to it, view live miner status in a command-center flow,
toggle mining safely, receive operational receipts in an encrypted inbox, and
prove that no mining work happens on the phone or gateway client.

This milestone matters because it proves the first real Zend product claim with
working behavior: Zend can make mining feel mobile-friendly without doing
mining on the phone, while already feeling like one private command center
instead of a pile of technical subsystems.

## Progress

- [x] (2026-03-19 22:47Z) Initial ExecPlan authored for the renamed Zend repo.
- [x] (2026-03-19 23:45Z) Accepted engineering-review recommendations folded
  into the plan: shared principal contract, LAN-only milestone 1, capability
  scopes, deferred payout mutation, diagrams, failure registry, and TODO
  capture.
- [x] (2026-03-19 23:55Z) Accepted CEO-review scope expansions folded into the
  plan baseline: trust ceremony, Hermes integration, Zend-native gateway
  contract, unified encrypted operations inbox, appliance-style onboarding, and
  private event spine.
- [x] (2026-03-20 00:10Z) Design-review recommendations folded into the plan:
  `DESIGN.md`, information hierarchy, interaction state coverage, emotional
  journey, AI-slop guardrails, and responsive or accessibility requirements.
- [ ] Create repo scaffolding for implementation artifacts: `apps/`,
  `services/`, `scripts/`, `references/`, `upstream/`, and `state/README.md`.
- [ ] Add `docs/designs/2026-03-19-zend-home-command-center.md` as the repo
  design doc for the expanded vertical slice.
- [ ] Add the minimal inbox architecture contract for milestone 1, including a
  shared `PrincipalId` that also owns future inbox access.
- [ ] Add the private event spine contract for milestone 1 and route operations
  inbox items through it.
- [ ] Add a pinned upstream manifest and fetch script for the reference mobile
  client repos plus the chosen home-miner backend or simulator.
- [ ] Implement a local home-miner control service that exposes safe status and
  control operations without performing any work on the client device.
- [ ] Implement a thin mobile-shaped gateway client that pairs with the home
  miner, reads live miner state, and surfaces a named Zend Home onboarding flow.
- [ ] Restrict milestone 1 to LAN-only pairing and control.
- [ ] Implement capability-scoped pairing records with `observe` and `control`
  permissions.
- [ ] Add a safe start or stop control flow with explicit acknowledgements and
  operator-visible guardrails.
- [ ] Add cached miner snapshots with freshness timestamps and serialized control
  command handling.
- [ ] Add a Zend-native gateway contract and a Hermes adapter that can connect
  to it using delegated authority.
- [ ] Add the encrypted operations inbox and route pairing approvals, control
  receipts, alerts, and Hermes summaries into it.
- [ ] Prove that the gateway client performs no hashing and only issues control
  requests to the home miner.
- [ ] Add automated tests for replayed pairing tokens, stale snapshots,
  controller conflicts, restart recovery, and audit false positives or negatives.
- [ ] Add tests for trust-ceremony state, Hermes delegation boundaries, event
  spine routing, inbox receipt behavior, and accessibility-sensitive states.
- [ ] Document gateway proof transcripts and exact rerun steps.

## Surprises & Discoveries

- Observation: The source repo used for bootstrapping this repo keeps the spec
  guide at `SPEC.md`, not `SPECS.md`.
  Evidence: `/home/r/coding/fabro/SPEC.md` exists; no `SPECS.md` file exists.

- Observation: Existing Zodl/Zashi clients already prove encrypted memo
  transport, so the new unknown is the home-miner gateway shape, not message
  encryption itself.
  Evidence: the reviewed iOS and Android code paths already support memo send
  and review flows.

- Observation: The product feels much more coherent when operational state and
  private messaging share one encrypted event spine.
  Evidence: the CEO review kept surfacing separate receipts, alerts, and Hermes
  summaries as a product smell compared with one unified private command center.

- Observation: Without an explicit design system, the likely failure mode is a
  generic crypto dashboard.
  Evidence: before this design pass, the repo had no `DESIGN.md` and the plan
  named the product surfaces without specifying hierarchy, states, or tone.

## Decision Log

- Decision: Rename the canonical planning repo and product to `Zend`.
  Rationale: the user rejected the previous name and wants all product-facing
  documents to use Zend instead.
  Date/Author: 2026-03-19 / Codex

- Decision: Do not fork the chain or mining algorithm in this phase.
  Rationale: the user chose the phone-as-control-plane approach, which avoids
  the consensus and app-store costs of on-device or mobile-friendly mining.
  Date/Author: 2026-03-19 / Codex

- Decision: Make the first implementation slice a home command center instead
  of a gateway-only proof.
  Rationale: the product should validate a real user experience, not just a
  transport or daemon concept.
  Date/Author: 2026-03-19 / Codex

- Decision: Mining must happen off-device.
  Rationale: this keeps the product compatible with the chosen direction and
  prevents the mobile gateway from becoming a disguised miner.
  Date/Author: 2026-03-19 / Codex

- Decision: Milestone 1 is LAN-only.
  Rationale: this is the boring default that lowers blast radius while still
  proving the product's control-plane thesis.
  Date/Author: 2026-03-19 / Codex

- Decision: Gateway permissions are limited to `observe` and `control`.
  Rationale: capability scoping is needed immediately, but payout-target mutation
  is deferred because it has higher financial risk.
  Date/Author: 2026-03-19 / Codex

- Decision: Milestone 1 must define a shared `PrincipalId` contract even though
  richer inbox UX is deferred.
  Rationale: identity must be stable across miner control and future inbox work
  or the architecture will fork in the wrong place.
  Date/Author: 2026-03-19 / Codex

- Decision: Zend owns a native gateway contract and Hermes connects through an
  adapter.
  Rationale: this keeps Zend future-proof and prevents Hermes from becoming the
  internal skeleton of the product.
  Date/Author: 2026-03-19 / Codex

- Decision: Milestone 1 includes a trust ceremony and appliance-style onboarding.
  Rationale: setup quality is part of the wedge, not polish to add later.
  Date/Author: 2026-03-19 / Codex

- Decision: Milestone 1 includes an encrypted operations inbox backed by one
  private event spine.
  Rationale: pairing approvals, alerts, receipts, Hermes summaries, and user
  messages should feel like one product.
  Date/Author: 2026-03-19 / Codex

- Decision: Zend uses a calm, domestic design system with Space Grotesk, IBM
  Plex Sans, and IBM Plex Mono.
  Rationale: the product needs to feel like a trusted household control surface,
  not a crypto exchange or a generic admin panel.
  Date/Author: 2026-03-20 / Codex

## Outcomes & Retrospective

At authoring time, this plan has not yet been executed. Its current outcome is
that the project now has a concrete, expanded first slice: build the smallest
real Zend product rather than proving the gateway in isolation.

## Context and Orientation

This repository currently contains planning documents only. `SPEC.md` explains
how durable specs should be written. `PLANS.md` explains how executable plans
must be authored and maintained. The accepted product boundary lives in
`specs/2026-03-19-zend-product-spec.md`. `DESIGN.md` is the visual and
interaction source of truth for implementation.

For this plan, "upstream" means an external repository or dependency that this
repo depends on conceptually but does not yet vendor. The critical upstreams
are the reference mobile clients for encrypted memo behavior and the chosen home
miner backend or miner simulator.

A `PrincipalId` is the stable identity Zend assigns to a user or agent account.
Milestone 1 must define it even though milestone 1 does not implement full
conversation UX.

A `GatewayCapability` is a named permission. Milestone 1 uses only `observe`
and `control`.

A `MinerSnapshot` is the cached status object the daemon returns to clients.
Snapshots must carry a freshness timestamp so the client can tell "live" from
"stale".

The first concrete consumers of the work in this plan are the thin
mobile-shaped command-center client, the home-miner daemon, and the Hermes
adapter. The scripts created here are intentionally designed so that a human
can run them from a terminal and an agent can call them as tools later without
a different code path.

## Design Intent

The command center should feel calm, domestic, and trustworthy. It must not
look like a trading terminal, a neon crypto app, or a generic admin dashboard.
All implementation should align with `DESIGN.md`, especially its typography,
color, layout, component vocabulary, and AI-slop guardrails.

### Information Architecture

The first product slice has four destinations. Their hierarchy is fixed:

1. `Home`
   This is the first screen after pairing. It shows miner state, active mode,
   snapshot freshness, and the single most important next action.
2. `Inbox`
   This is the second most important destination. It holds pairing approvals,
   control receipts, alerts, Hermes summaries, and private messages.
3. `Agent`
   This shows what Hermes can see and do, what it recently did, and where its
   authority stops.
4. `Device`
   This contains trust, permissions, pairing, recovery, and maintenance.

The mobile app uses a bottom tab bar for these four destinations. Larger
viewports may promote this to a left rail, but the order must stay the same.

```text
  HOME
   |
   +--> Status Hero
   +--> Mode Switcher
   +--> Latest Receipt
   +--> Quick link to Inbox

  INBOX
   |
   +--> Pairing approvals
   +--> Control receipts
   +--> Alerts
   +--> Hermes summaries
   +--> User messages

  AGENT
   |
   +--> Hermes connection state
   +--> Allowed capabilities
   +--> Recent agent actions

  DEVICE
   |
   +--> Device name
   +--> Pairing + trust
   +--> Observe / control grants
   +--> Recovery
```

### Interaction State Coverage

| Feature | Loading | Empty | Error | Success | Partial |
| --- | --- | --- | --- | --- | --- |
| Zend Home onboarding | skeleton + trust copy | n/a | clear setup failure with retry | named box + paired phone | paired but health check incomplete |
| Miner status hero | snapshot shimmer | n/a | daemon unavailable banner | fresh state with timestamp | stale state warning |
| Operations inbox | skeleton list | warm “nothing yet” copy + first action | inbox unavailable banner | grouped receipts/messages | some events unavailable, others visible |
| Mode switcher | disabled segmented control with pending label | n/a | explicit conflict or auth error | receipt appended | command queued |
| Hermes panel | pending handshake state | “Hermes not connected yet” with grant action | adapter unavailable or unauthorized | summary + last action | connected but degraded authority |
| Device trust screen | loading permissions sheet | no secondary devices paired | revoke or reset failure | updated grants | one grant updated, one pending |

### User Journey & Emotional Arc

| Step | User Does | User Feels | Plan Must Support |
| --- | --- | --- | --- |
| 1 | opens Zend Home for the first time | cautious curiosity | friendly onboarding, named box, no jargon wall |
| 2 | pairs device | vulnerability | explicit trust ceremony and permission framing |
| 3 | lands on Home | relief | clear miner state, freshness, and one obvious next action |
| 4 | changes miner mode | responsibility | explicit acknowledgement and reversible action language |
| 5 | checks Inbox | confidence | one private feed for receipts, alerts, and summaries |
| 6 | enables Hermes | guarded optimism | clear boundary of what Hermes may observe or control |
| 7 | returns days later | familiarity | stable layout, warm empty states, clear trust signals |

### AI Slop Guardrails

Implementation must avoid:

- generic crypto-dashboard widgets
- hero sections with abstract gradients and marketing slogans
- three-card feature grids
- decorative icon farms
- “No items found” empty states with no next step

The first slice should instead use:

- one dominant `Status Hero`
- one `Mode Switcher`
- one `Receipt Card` style for operational events
- one `Trust Sheet` style for capability grants
- one `Permission Pill` vocabulary for observe vs control

### Responsive & Accessibility

Mobile is primary. The phone layout is single-column with the bottom tab bar
always reachable by thumb. The tablet or desktop layout may widen into a two-
pane structure, but never by simply stacking mobile cards on a wider screen.

Accessibility requirements for milestone 1:

- minimum `44x44` touch targets
- body text at least equivalent to `16px`
- all miner states announced by text and icon, never color alone
- polite live region for new receipts and alerts
- full keyboard navigation on large-screen clients
- screen-reader landmarks for Home, Inbox, Agent, and Device
- reduced-motion fallback for every animated receipt or state change

## Architecture Diagrams

### System Architecture

```text
  Thin Mobile Client
          |
          | pair + observe + control + inbox
          v
   Zend Gateway Contract
       |           |
       |           +--> Zend Event Spine
       v
  Home Miner Daemon
    |        |          \
    |        |           +--> Pairing store / principal store / audit log
    |        |
    |        +--> Hermes Adapter
    |                   |
    |                   v
    |              Hermes Gateway / Agent
    |
    +--> Miner backend or simulator
                 |
                 v
            Zcash network

  Future adjacent system:
  richer encrypted inbox UX on the same event spine
```

### Pairing and Authority State Machine

```text
  UNPAIRED
     |
     | valid trust ceremony
     v
  PAIRED_OBSERVER
     |
     | explicit control grant
     v
  PAIRED_CONTROLLER
     | \
     |  \ revoke / expire / reset
     |   \
     v    v
  CONTROL_ACTION ---> REJECTED
     |
     v
  RECEIPT APPENDED TO EVENT SPINE
```

### Data Flow

```text
  INPUT ─────────────▶ VALIDATE ─────────────▶ TRANSFORM ──────────▶ APPEND
    |                      |                        |                   |
    ├─ nil pairing token   ├─ invalid capability    ├─ daemon offline   ├─ event append fail
    ├─ empty device name   ├─ expired token         ├─ stale snapshot   ├─ inbox decrypt fail
    ├─ no delegated agent  ├─ unauthorized action   ├─ control conflict ├─ Hermes summary reject
    ▼                      ▼                        ▼                   ▼
  REJECT                NAMED ERROR             RETRY/FAIL          USER RECEIPT / WARNING
```

### Recovery Sequence

```text
  Stop daemon
      |
      v
  Clear local state
      |
      v
  Refresh upstream pins
      |
      v
  Re-bootstrap Zend Home
      |
      v
  Re-pair client
      |
      v
  Re-run onboarding + inbox + control + audit proof
```

## Plan of Work

Start by creating the implementation directories that this plan assumes:
`apps/` for the thin client, `services/` for the home-miner daemon,
`scripts/` for repeatable operator and proof commands, `references/` for
contracts and storyboard notes, `upstream/` for pinned dependencies, and
`state/` for ignored local runtime data. Add a short `state/README.md` so a
novice knows that local miner state is disposable and intentionally untracked.

Before implementing any daemon or client flow, add `references/inbox-contract.md`
to define the minimal inbox architecture contract for milestone 1. That file
must introduce `PrincipalId`, describe how a gateway pairing record references
it, and explicitly state that future inbox metadata must reuse the same
identifier rather than inventing a new auth namespace.

Also add `references/event-spine.md` to define the append-only encrypted event
journal used by milestone 1. It must name the first event kinds: pairing
requested, pairing granted, capability revoked, miner alert, control receipt,
Hermes summary, and user message.

Add `references/design-checklist.md` as the implementation-ready translation of
this plan’s design requirements so frontend work can be checked against it file
by file.

Add `upstream/manifest.lock.json` as the single source of truth for external
repositories and pinned tags or commit SHAs. It must include the chosen
reference mobile client repos and the chosen miner backend or simulator. Add
`scripts/fetch_upstreams.sh` that reads this manifest and checks out each source
into `third_party/<name>`. The script must be idempotent: rerunning it should
update an existing checkout to the pinned revision instead of failing.

Create a local home-miner control service under `services/`. The first slice may
use a miner simulator if a real miner backend would slow down the command-center
proof, but the simulator must expose the same contract the real miner will use:
status, start, stop, mode selection, and health. Payout-target mutation is
explicitly out of scope for milestone 1.

The daemon must stay LAN-only in milestone 1. It must not open a public control
surface, a cloud relay path, or an internet-facing ingress. The plan should say
exactly which interface the daemon binds to in the first implementation slice.

Add a bootstrap script, `scripts/bootstrap_home_miner.sh`, that brings the
service up, prepares deterministic local state, and emits a pairing bundle or
token for a client named `alice-phone`.

Add a thin mobile-shaped command-center surface under `apps/` that is still
simple enough for milestone 1 but is unmistakably product-facing. It must
support named onboarding, trust ceremony, status dashboard, operations inbox,
and control action confirmations.

Add `scripts/pair_gateway_client.sh`, `scripts/read_miner_status.sh`, and
`scripts/set_mining_mode.sh`. The pair script must create a durable local client
record containing a `PrincipalId` and a `GatewayCapability` set. The status
script must print live miner state from a cached `MinerSnapshot`, including a
freshness timestamp. The mode script must change the miner from paused to
balanced or performance and print an explicit acknowledgement.

Control commands must be serialized. The plan must state how the daemon handles
two competing control requests so the system cannot acknowledge both as if they
were independently applied.

Add `scripts/no_local_hashing_audit.sh` as the off-device proof. It must inspect
the gateway client process and fail if hashing libraries, mining threads, or
unexpected CPU-bound worker loops are active on the client side.

All gateway scripts must be thin wrappers over one shared control client library
or CLI. Do not duplicate protocol parsing or auth logic across multiple shell
scripts.

Add `references/error-taxonomy.md` to define the named failure classes used by
the gateway plan. At minimum it must include `PairingTokenExpired`,
`PairingTokenReplay`, `GatewayUnauthorized`, `GatewayUnavailable`,
`MinerSnapshotStale`, `ControlCommandConflict`, `EventAppendFailed`, and
`LocalHashingDetected`.

Add `references/observability.md` that names the first structured log events,
metrics, and audit-log records required for bootstrap, pairing, status reads,
control actions, inbox appends, Hermes actions, and local-hashing audit
results.

Add `references/hermes-adapter.md` that defines how Hermes Gateway connects to
the Zend-native gateway contract, which capabilities can be delegated, and which
event-spine items Hermes may read or append.

Document every proof step in `references/gateway-proof.md` with concise,
copiable transcripts. Add `references/onboarding-storyboard.md` as a narrative
walkthrough for the Zend Home onboarding and trust ceremony.

## Concrete Steps

Run all commands from the repository root.

1. Prepare pinned upstreams.

       cd /home/r/coding/zend
       ./scripts/fetch_upstreams.sh

   Expected result: the directory `third_party/` appears and contains the
   pinned reference client and miner-backend sources recorded in
   `upstream/manifest.lock.json`.

2. Bootstrap the daemon, principal contract, and Zend Home onboarding state.

       cd /home/r/coding/zend
       ./scripts/bootstrap_home_miner.sh

   Expected result: the script starts the local service and prints a pairing
   bundle or token for `alice-phone`. It also creates deterministic local state
   for one `PrincipalId`.

3. Pair the gateway client through the trust ceremony.

       cd /home/r/coding/zend
       ./scripts/pair_gateway_client.sh --client alice-phone

   Expected result: the script records a paired client locally with `observe`
   capability, a human-readable device name, and a clear success message.

4. Read live miner status through the command-center surface.

       cd /home/r/coding/zend
       ./scripts/read_miner_status.sh --client alice-phone

   Expected result: the script prints current miner status, selected mode, a
   freshness timestamp, and a health summary. The status hero must visually
   distinguish fresh vs stale data and must place the active mode and next
   recommended action above all secondary details.

5. Change the mining mode and append a control receipt to the encrypted
   operations inbox.

       cd /home/r/coding/zend
       ./scripts/set_mining_mode.sh --client alice-phone --mode balanced

   Expected result: the script prints an explicit acknowledgement that the home
   miner, not the client device, accepted the mode change. If the client lacks
   `control`, the command must fail with a named authorization error.

6. Connect Hermes through the Zend adapter, append a summary to the encrypted
   operations inbox, and then audit the gateway client for local hashing.

       cd /home/r/coding/zend
       ./scripts/hermes_summary_smoke.sh --client alice-phone
       ./scripts/no_local_hashing_audit.sh --client alice-phone

   Expected result: the Hermes summary is visible in the same encrypted
   operations inbox as pairing and control receipts, and the client still proves
   it is only a control plane.

## Validation and Acceptance

The work is accepted only when a novice can run the six concrete steps above in
order and observe all of the following:

- the home-miner service starts locally and can be paired to a client
- the daemon is clearly LAN-only in milestone 1
- the onboarding flow names the device and makes trust legible
- the gateway client can read live miner state
- the gateway client can safely issue a control action
- a paired observer cannot issue a control action
- the status surface can distinguish a fresh snapshot from a stale one
- the app has explicit loading, empty, error, success, and partial states for
  every first-slice feature
- the operations inbox receives pairing approvals, control receipts, alerts, and
  Hermes summaries through one encrypted event spine
- Hermes can connect only through the Zend adapter and only with delegated
  authority
- the proof shows that mining happens off-device
- the plan contains the minimal shared `PrincipalId` contract for future inbox
  work

In addition to the end-to-end proof, add at least one automated test per new
script that validates argument parsing and expected failure behavior. Also add
explicit tests for replayed or expired pairing tokens, duplicate client names,
stale `MinerSnapshot` handling, conflicting control commands, daemon restart and
paired-client recovery, trust-ceremony state transitions, Hermes adapter
boundaries, event-spine routing, false positive or false negative audit
fixtures, empty inbox states, stale status warnings, reduced-motion transitions,
screen-reader announcement of new receipts, and control denial copy for
observe-only clients.

## Idempotence and Recovery

`scripts/fetch_upstreams.sh` must be safe to rerun. It should reset each local
upstream checkout to the pinned revision rather than assuming a clean clone.

`scripts/bootstrap_home_miner.sh` must either detect existing prepared state and
reuse it safely or wipe and recreate the named local service state in a
deterministic way.

If the local service state becomes corrupt or stale, the recovery path must be
documented and tested:

       cd /home/r/coding/zend
       rm -rf state/*
       ./scripts/fetch_upstreams.sh
       ./scripts/bootstrap_home_miner.sh

The recovery path is acceptable only if it produces the same proofable outcome
without requiring manual edits.

## Artifacts and Notes

Keep the most important proof transcript in `references/gateway-proof.md`.
When the milestone is complete, that file should contain a concise example like
this:

    $ ./scripts/bootstrap_home_miner.sh
    pairing_token=...

    $ ./scripts/pair_gateway_client.sh --client alice-phone
    paired alice-phone
    capability=observe
    device_name=Zend Home North

    $ ./scripts/read_miner_status.sh --client alice-phone
    status=running
    mode=balanced
    freshness=2026-03-19T23:59:00Z

    $ ./scripts/hermes_summary_smoke.sh --client alice-phone
    summary_appended_to_operations_inbox=true

    $ ./scripts/no_local_hashing_audit.sh --client alice-phone
    checked: client process tree
    checked: local CPU worker count
    result: no local hashing detected

## Test Diagram

```text
  NEW UX / OPERATOR FLOWS
  1. Zend Home onboarding
  2. Pair client
  3. Read miner status
  4. Change mining mode
  5. Review encrypted operations inbox
  6. Receive Hermes summary
  7. Prove no local hashing
  8. Bind future inbox identity to same principal

  NEW DATA FLOWS
  A. pairing token -> session -> capability-scoped client record
  B. daemon status -> MinerSnapshot -> client status view
  C. control request -> daemon -> miner backend -> ack/failure -> event spine
  D. Hermes delegated read/action -> adapter -> gateway contract
  E. event spine -> encrypted operations inbox
  F. audit probe -> client process inspection -> pass/fail
  G. PrincipalId -> gateway auth -> future inbox auth

  NEW BRANCHES / OUTCOMES
  i. valid vs expired vs replayed pairing token
  ii. paired vs unpaired status read
  iii. observer vs controller permissions
  iv. valid mode vs invalid mode
  v. daemon available vs unavailable
  vi. fresh snapshot vs stale snapshot
  vii. Hermes authorized vs unauthorized action
  viii. operations inbox append succeeds vs fails
  ix. local hashing absent vs detected
  x. single controller vs conflicting controllers
```

## Error and Rescue Registry

| Method / Codepath | What Can Go Wrong | Named Error | Rescue Action | User Sees |
| --- | --- | --- | --- | --- |
| `bootstrap_home_miner.sh` | bound port already in use | `GatewayUnavailable` | exit with context and recovery hint | clear bootstrap failure |
| `pair_gateway_client.sh` | token expired | `PairingTokenExpired` | reject pairing and request new token | clear pairing failure |
| `pair_gateway_client.sh` | token replayed | `PairingTokenReplay` | reject pairing and log audit event | clear pairing failure |
| `read_miner_status.sh` | daemon offline | `GatewayUnavailable` | return explicit unavailable state | clear status failure |
| `read_miner_status.sh` | snapshot too old | `MinerSnapshotStale` | return stale flag and warning | stale-data warning |
| `set_mining_mode.sh` | client lacks control scope | `GatewayUnauthorized` | reject command | authorization error |
| `set_mining_mode.sh` | competing in-flight command | `ControlCommandConflict` | reject or queue deterministically | conflict error |
| `hermes_summary_smoke.sh` | delegated authority missing | `GatewayUnauthorized` | reject summary/action request | authorization error |
| event spine append | encrypted write fails | `EventAppendFailed` | retry or surface failure | receipt or inbox warning |
| `no_local_hashing_audit.sh` | local hashing detected | `LocalHashingDetected` | fail non-zero | explicit audit failure |

## Failure Modes Registry

| Codepath | Failure Mode | Rescued? | Test? | User Sees? | Logged? |
| --- | --- | --- | --- | --- | --- |
| bootstrap | port already in use | yes | planned | explicit error | yes |
| pairing | replayed token | yes | planned | explicit error | yes |
| status | stale snapshot shown as fresh | no, must be prevented | planned | warning, never silent | yes |
| control | conflicting commands | yes | planned | explicit conflict | yes |
| inbox | event append fails silently | no, must be prevented | planned | explicit warning | yes |
| Hermes | unauthorized delegated action | yes | planned | explicit error | yes |
| audit | helper-process false negative | no, must be tested | planned | explicit failure in fixtures | yes |

## What Already Exists

- Existing encrypted memo behavior already exists in the reference Zodl/Zashi
  clients and should inform the inbox portion of milestone 1.
- `docs/designs/2026-03-19-zend-home-command-center.md` already defines the
  product storyboard and accepted scope expansions.
- `DESIGN.md` now defines the visual and interaction system and should be reused
  instead of inventing component styles during implementation.

## Observability

Milestone 1 must emit at least these structured events:

- `gateway.bootstrap.started`
- `gateway.bootstrap.failed`
- `gateway.pairing.succeeded`
- `gateway.pairing.rejected`
- `gateway.status.read`
- `gateway.status.stale`
- `gateway.control.accepted`
- `gateway.control.rejected`
- `gateway.inbox.appended`
- `gateway.inbox.append_failed`
- `gateway.hermes.summary_appended`
- `gateway.hermes.unauthorized`
- `gateway.audit.local_hashing_detected`

Milestone 1 must expose at least these metrics:

- pairing attempts by outcome
- status reads by freshness state
- control commands by outcome
- operations inbox append outcomes
- Hermes delegated actions by outcome
- audit failures by client

## NOT in Scope

- remote internet access to the gateway daemon: deferred because milestone 1 is
  LAN-only
- payout-target mutation: deferred because it has higher financial blast radius
- rich conversation UX beyond the operations inbox: deferred because milestone 1
  only proves the unified private command-center surface
- real miner backend if a simulator proves the contract faster: deferred unless
  needed for command-center proof
- dark-mode expansion beyond whatever falls out of the first design system:
  deferred until the command-center flow itself is stable
- complex charts, earnings analytics, or historical visualization dashboards:
  deferred because they would crowd the first-slice hierarchy

## Interfaces and Dependencies

`upstream/manifest.lock.json` must be a machine-readable manifest that records,
for each upstream, a stable repository URL plus a pinned tag or commit SHA. The
script `scripts/fetch_upstreams.sh` must consume this manifest directly instead
of duplicating pins internally.

Add `references/inbox-contract.md` defining:

    type PrincipalId = string

It must describe how the same `PrincipalId` is referenced by gateway pairing
metadata and future inbox metadata.

Add `references/event-spine.md` defining:

    type EventKind =
      | PairingRequested
      | PairingGranted
      | CapabilityRevoked
      | MinerAlert
      | ControlReceipt
      | HermesSummary
      | UserMessage

It must describe the encrypted append-only journal that feeds the operations
inbox.

Add `references/error-taxonomy.md` defining the named error classes used in
milestone 1.

`scripts/fetch_upstreams.sh` must accept no required arguments and must clone or
refresh all pinned upstreams under `third_party/`.

`scripts/bootstrap_home_miner.sh` must prepare local miner state needed for the
smoke test. Its output must include a pairing bundle or token that later scripts
can use. It must also record a deterministic `PrincipalId`.

`scripts/pair_gateway_client.sh` must expose this interface:

    ./scripts/pair_gateway_client.sh --client <name>

It must record a paired client, associated `PrincipalId`, and capability set,
and print a clear success acknowledgement plus a human-readable device name.

`scripts/read_miner_status.sh` must expose this interface:

    ./scripts/read_miner_status.sh --client <name>

It must print current miner status, selected mode, freshness timestamp, and
health.

`scripts/set_mining_mode.sh` must expose this interface:

    ./scripts/set_mining_mode.sh --client <name> --mode <paused|balanced|performance>

It must perform a safe control action on the home miner and print an explicit
acknowledgement. It must fail clearly when the client lacks `control`.

`scripts/no_local_hashing_audit.sh` must expose this interface:

    ./scripts/no_local_hashing_audit.sh --client <name>

It must exit non-zero when the gateway client appears to be doing hashing work.

`scripts/hermes_summary_smoke.sh` must expose this interface:

    ./scripts/hermes_summary_smoke.sh --client <name>

It must prove Hermes can connect through the Zend adapter and append one
delegated summary event into the encrypted operations inbox without bypassing
Zend capability checks.
