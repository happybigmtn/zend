# Prove the Zend Home-Miner Gateway

This ExecPlan is a living document. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
be kept up to date as work proceeds.

`PLANS.md` at the repository root governs this ExecPlan. This document must be
maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

After this work, a new contributor should be able to start from a fresh clone
of this repository, run a local home-miner control service, pair a script or
mobile-gateway client to it, view live miner status, toggle mining safely, and
prove that no mining work happens on the phone or gateway client.

This milestone matters because it proves the hardest new product claim with
working behavior: Zend can make mining feel mobile-friendly without actually
doing mining on the phone. Once this gateway works, later inbox and messaging
work can compose on top of a real product posture instead of a vague idea.

## Progress

- [x] (2026-03-19 22:47Z) Initial ExecPlan authored for the renamed Zend repo.
- [x] (2026-03-19 23:45Z) Accepted engineering-review recommendations folded
  into the plan: shared principal contract, LAN-only milestone 1, capability
  scopes, deferred payout mutation, diagrams, failure registry, and TODO
  capture.
- [ ] Create repo scaffolding for implementation artifacts: `apps/`,
  `services/`, `scripts/`, `references/`, `upstream/`, and `state/README.md`.
- [ ] Add the minimal inbox architecture contract for milestone 1, including a
  shared `PrincipalId` that also owns future inbox access.
- [ ] Add a pinned upstream manifest and fetch script for the reference mobile
  client repos plus the chosen home-miner backend or simulator.
- [ ] Implement a local home-miner control service that exposes safe status and
  control operations without performing any work on the client device.
- [ ] Implement a script-first gateway client that pairs with the home miner and
  reads live miner state.
- [ ] Restrict milestone 1 to LAN-only pairing and control.
- [ ] Implement capability-scoped pairing records with `observe` and `control`
  permissions.
- [ ] Add a safe start or stop control flow with explicit acknowledgements and
  operator-visible guardrails.
- [ ] Add cached miner snapshots with freshness timestamps and serialized control
  command handling.
- [ ] Prove that the gateway client performs no hashing and only issues control
  requests to the home miner.
- [ ] Add automated tests for replayed pairing tokens, stale snapshots,
  controller conflicts, restart recovery, and audit false positives or negatives.
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

- Observation: The user explicitly rejected on-device mining and chain-fork
  work for this phase.
  Evidence: review feedback selected the off-device mobile-gateway approach and
  asked for no chain fork.

- Observation: Milestone 1 needs a shared identity contract even if inbox UX is
  deferred.
  Evidence: the engineering review found that shipping miner control without a
  shared principal would likely create a second auth system that the inbox would
  later need to unwind.

## Decision Log

- Decision: Rename the canonical planning repo and product to `Zend`.
  Rationale: the user rejected the previous name and wants all product-facing
  documents to use Zend instead.
  Date/Author: 2026-03-19 / Codex

- Decision: Do not fork the chain or mining algorithm in this phase.
  Rationale: the user chose the phone-as-control-plane approach, which avoids
  the consensus and app-store costs of on-device or mobile-friendly mining.
  Date/Author: 2026-03-19 / Codex

- Decision: Make the first implementation slice a home-miner gateway proof
  instead of a chain or transport proof.
  Rationale: encrypted transport already has strong reference implementations,
  but the home-miner gateway is the new product-defining unknown.
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
  inbox UX is deferred.
  Rationale: identity must be stable across miner control and future inbox work
  or the architecture will fork in the wrong place.
  Date/Author: 2026-03-19 / Codex

## Outcomes & Retrospective

At authoring time, this plan has not yet been executed. Its current outcome is
that the project now has a concrete, outcome-shaped first slice: prove a mobile
or script gateway into a home miner before taking on full inbox UX or deeper
automation.

## Context and Orientation

This repository currently contains planning documents only. `SPEC.md` explains
how durable specs should be written. `PLANS.md` explains how executable plans
must be authored and maintained. The accepted product boundary lives in
`specs/2026-03-19-zend-product-spec.md`.

For this plan, "upstream" means an external repository or dependency that this
repo depends on conceptually but does not yet vendor. The critical upstreams
are the reference mobile clients for encrypted memo behavior and the chosen home
miner backend or miner simulator.

A "home miner" means a long-running process on hardware the user controls that
does the actual mining work. A "gateway proof" means runnable evidence that a
client can pair with that home miner, observe live state, and control it
without performing hashing locally.

A `PrincipalId` is the stable identity Zend assigns to a user or agent account.
Milestone 1 must define it even though milestone 1 does not implement inbox UI.

A `MinerSnapshot` is the cached status object the daemon returns to clients.
Snapshots must carry a freshness timestamp so the client can tell "live" from
"stale".

A `GatewayCapability` is a named permission. Milestone 1 uses only
`observe` and `control`.

The first concrete consumer of the work in this plan is a script-first agent
surface. The scripts created here are intentionally designed so that a human can
run them from a terminal and an agent can call them as tools later without a
different code path.

## Architecture Diagrams

### System Architecture

```text
  Script Client / Mobile Gateway
              |
              | pair + observe + control
              v
       Zend Gateway Contract
              |
              v
       Home Miner Daemon
         |           |
         |           +--> Pairing store / audit log / principal store
         |
         +--> Miner backend or simulator
                     |
                     v
                Zcash network

  Future adjacent system:
  Client / Agent
        |
        v
   Encrypted Inbox
        |
        v
  lightwalletd / full node / chain
```

### Pairing and Authority State Machine

```text
  UNPAIRED
     |
     | valid pairing token
     v
  PAIRED_OBSERVER
     |
     | grant control capability
     v
  PAIRED_CONTROLLER
     | \
     |  \ revoke / expire / reset
     |   \
     v    v
  CONTROL_ACTION ---> REJECTED
     |
     v
  ACKED / FAILED
```

### Control Command Flow

```text
  Client Command
      |
      v
  Capability Check ---> reject if missing `control`
      |
      v
  Command Queue / Serializer
      |
      v
  Miner Backend
      |
      +--> success ack
      |
      +--> failure with named error
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
  Re-bootstrap daemon
      |
      v
  Re-pair client
      |
      v
  Re-run status + control + audit proof
```

## Plan of Work

Start by creating the implementation directories that this plan assumes:
`apps/` for gateway client surfaces, `services/` for the home-miner daemon,
`scripts/` for repeatable operator and proof commands, `references/` for miner
backend notes and pairing assumptions, `upstream/` for lockfiles that pin
external repos, and `state/` for ignored local runtime data. Add a short
`state/README.md` so a novice knows that local miner state is disposable and
intentionally untracked.

Before implementing any daemon or script flow, add `references/inbox-contract.md`
to define the minimal inbox architecture contract for milestone 1. That file
must introduce `PrincipalId`, describe how a gateway pairing record references
it, and explicitly state that future inbox metadata must reuse the same
identifier rather than inventing a new auth namespace.

Add `upstream/manifest.lock.json` as the single source of truth for external
repositories and pinned tags or commit SHAs. It must include the chosen
reference mobile client repos and the chosen miner backend or simulator. Add
`scripts/fetch_upstreams.sh` that reads this manifest and checks out each source
into `third_party/<name>`. The script must be idempotent: rerunning it should
update an existing checkout to the pinned revision instead of failing.

Create a local home-miner control service under `services/`. The first slice may
use a miner simulator if a real miner backend would slow down the control-plane
proof, but the simulator must expose the same contract the real miner will use:
status, start, stop, mode selection, and health. Payout-target mutation is
explicitly out of scope for milestone 1.

The daemon must stay LAN-only in milestone 1. It must not open a public control
surface, a cloud relay path, or an internet-facing ingress. The plan should say
exactly which interface the daemon binds to in the first implementation slice.

Add a bootstrap script, `scripts/bootstrap_home_miner.sh`, that brings the
service up, prepares deterministic local state, and emits a pairing bundle or
token for a client named `alice-phone`.

Add `scripts/pair_gateway_client.sh`, `scripts/read_miner_status.sh`, and
`scripts/set_mining_mode.sh`. The pair script must create a durable local client
record containing a `PrincipalId` and a `GatewayCapability` set. The status
script must print live miner state from a cached `MinerSnapshot`, including a
freshness timestamp. The mode script must
change the miner from paused to balanced or performance and print an explicit
acknowledgement.

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
`MinerSnapshotStale`, `ControlCommandConflict`, and `LocalHashingDetected`.

Add `references/observability.md` that names the first structured log events,
metrics, and audit-log records required for bootstrap, pairing, status reads,
control actions, and local-hashing audit results.

Document every proof step in `references/gateway-proof.md` with concise,
copiable transcripts. This document is not a replacement for the scripts. It is
the evidence that the scripts produced the expected outcome.

## Concrete Steps

Run all commands from the repository root.

1. Prepare pinned upstreams.

       cd /home/r/coding/zend
       ./scripts/fetch_upstreams.sh

   Expected result: the directory `third_party/` appears and contains the
   pinned reference client and miner-backend sources recorded in
   `upstream/manifest.lock.json`.

2. Bootstrap the daemon and principal contract.

       cd /home/r/coding/zend
       ./scripts/bootstrap_home_miner.sh

   Expected result: the script starts the local service and prints a pairing
   bundle or token for `alice-phone`. It also creates deterministic local state
   for one `PrincipalId`.

3. Pair the gateway client.

       cd /home/r/coding/zend
       ./scripts/pair_gateway_client.sh --client alice-phone

   Expected result: the script records a paired client locally with `observe`
   capability and prints a clear success message.

4. Read live miner status.

       cd /home/r/coding/zend
       ./scripts/read_miner_status.sh --client alice-phone

   Expected result: the script prints current miner status, selected mode, a
   freshness timestamp, and a health summary.

5. Change the mining mode.

       cd /home/r/coding/zend
       ./scripts/set_mining_mode.sh --client alice-phone --mode balanced

   Expected result: the script prints an explicit acknowledgement that the home
   miner, not the client device, accepted the mode change. If the client lacks
   `control`, the command must fail with a named authorization error.

6. Audit the gateway client for local hashing.

       cd /home/r/coding/zend
       ./scripts/no_local_hashing_audit.sh --client alice-phone

   Expected result: the script exits zero and reports that the gateway client is
   only a control plane and is not doing mining work itself.

## Validation and Acceptance

The work is accepted only when a novice can run the six concrete steps above in
order and observe all of the following:

- the home-miner service starts locally and can be paired to a client
- the daemon is clearly LAN-only in milestone 1
- the gateway client can read live miner state
- the gateway client can safely issue a control action
- a paired observer cannot issue a control action
- the status surface can distinguish a fresh snapshot from a stale one
- the proof shows that mining happens off-device
- the new control path is honest about what is and is not happening on the
  client
- the plan contains the minimal shared `PrincipalId` contract for future inbox
  work

In addition to the end-to-end proof, add at least one automated test per new
script that validates argument parsing and expected failure behavior. For
example, `set_mining_mode.sh` must fail clearly if the client is unpaired, and
`no_local_hashing_audit.sh` must fail if given a known positive fixture.

Also add explicit tests for:

- replayed or expired pairing tokens
- duplicate client names
- stale `MinerSnapshot` freshness handling
- conflicting control commands from two clients
- daemon restart and paired-client recovery
- false positive and false negative audit fixtures
- shared `PrincipalId` reuse between gateway pairing data and future inbox
  metadata fixtures

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
this, updated with the real transaction ID and audited surfaces:

    $ ./scripts/bootstrap_home_miner.sh
    pairing_token=...

    $ ./scripts/pair_gateway_client.sh --client alice-phone
    paired alice-phone
    capability=observe

    $ ./scripts/read_miner_status.sh --client alice-phone
    status=running
    mode=balanced
    freshness=2026-03-19T23:59:00Z

    $ ./scripts/no_local_hashing_audit.sh --client alice-phone
    checked: client process tree
    checked: local CPU worker count
    result: no local hashing detected

## Test Diagram

```text
  NEW UX / OPERATOR FLOWS
  1. Bootstrap daemon
  2. Pair client
  3. Read miner status
  4. Change mining mode
  5. Prove no local hashing
  6. Bind future inbox identity to same principal

  NEW DATA FLOWS
  A. pairing token -> session -> capability-scoped client record
  B. daemon status -> MinerSnapshot -> client status view
  C. control request -> daemon -> miner backend -> ack/failure
  D. audit probe -> client process inspection -> pass/fail
  E. PrincipalId -> gateway auth -> future inbox auth

  NEW BRANCHES / OUTCOMES
  i. valid vs expired vs replayed pairing token
  ii. paired vs unpaired status read
  iii. observer vs controller permissions
  iv. valid mode vs invalid mode
  v. daemon available vs unavailable
  vi. fresh snapshot vs stale snapshot
  vii. local hashing absent vs detected
  viii. single controller vs conflicting controllers
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
| `no_local_hashing_audit.sh` | local hashing detected | `LocalHashingDetected` | fail non-zero | explicit audit failure |

## Failure Modes Registry

| Codepath | Failure Mode | Rescued? | Test? | User Sees? | Logged? |
| --- | --- | --- | --- | --- | --- |
| bootstrap | port already in use | yes | planned | explicit error | yes |
| pairing | replayed token | yes | planned | explicit error | yes |
| status | stale snapshot shown as fresh | no, must be prevented | planned | warning, never silent | yes |
| control | conflicting commands | yes | planned | explicit conflict | yes |
| audit | helper-process false negative | no, must be tested | planned | explicit failure in fixtures | yes |

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
- `gateway.audit.local_hashing_detected`

Milestone 1 must expose at least these metrics:

- pairing attempts by outcome
- status reads by freshness state
- control commands by outcome
- audit failures by client

## NOT in Scope

- remote internet access to the gateway daemon: deferred because milestone 1 is
  LAN-only
- payout-target mutation: deferred because it has higher financial blast radius
- full inbox UX: deferred because milestone 1 only defines the shared identity
  contract
- real miner backend if a simulator proves the contract faster: deferred unless
  needed for gateway proof

## Interfaces and Dependencies

The following files and interfaces must exist at the end of this milestone.

`upstream/manifest.lock.json` must be a machine-readable manifest that records,
for each upstream, a stable repository URL plus a pinned tag or commit SHA. The
script `scripts/fetch_upstreams.sh` must consume this manifest directly instead
of duplicating pins internally.

Add `references/inbox-contract.md` defining:

    type PrincipalId = string

It must describe how the same `PrincipalId` is referenced by gateway pairing
state and future inbox metadata.

Add `references/error-taxonomy.md` defining the named error classes used in
milestone 1.

`scripts/fetch_upstreams.sh` must accept no required arguments and must clone or
refresh all pinned upstreams under `third_party/`.

`scripts/bootstrap_home_miner.sh` must prepare local miner state needed for the
smoke test. Its output must include a pairing bundle or token that later scripts
can use.

It must also record a deterministic `PrincipalId`.

`scripts/pair_gateway_client.sh` must expose this interface:

    ./scripts/pair_gateway_client.sh --client <name>

It must record a paired client, associated `PrincipalId`, and capability set,
and print a clear success acknowledgement.

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
