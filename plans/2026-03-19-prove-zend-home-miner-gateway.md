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
- [ ] Create repo scaffolding for implementation artifacts: `apps/`,
  `services/`, `scripts/`, `references/`, `upstream/`, and `state/README.md`.
- [ ] Add a pinned upstream manifest and fetch script for the reference mobile
  client repos plus the chosen home-miner backend or simulator.
- [ ] Implement a local home-miner control service that exposes safe status and
  control operations without performing any work on the client device.
- [ ] Implement a script-first gateway client that pairs with the home miner and
  reads live miner state.
- [ ] Add a safe start or stop control flow with explicit acknowledgements and
  operator-visible guardrails.
- [ ] Prove that the gateway client performs no hashing and only issues control
  requests to the home miner.
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

The first concrete consumer of the work in this plan is a script-first agent
surface. The scripts created here are intentionally designed so that a human can
run them from a terminal and an agent can call them as tools later without a
different code path.

## Plan of Work

Start by creating the implementation directories that this plan assumes:
`apps/` for gateway client surfaces, `services/` for the home-miner daemon,
`scripts/` for repeatable operator and proof commands, `references/` for miner
backend notes and pairing assumptions, `upstream/` for lockfiles that pin
external repos, and `state/` for ignored local runtime data. Add a short
`state/README.md` so a novice knows that local miner state is disposable and
intentionally untracked.

Add `upstream/manifest.lock.json` as the single source of truth for external
repositories and pinned tags or commit SHAs. It must include the chosen
reference mobile client repos and the chosen miner backend or simulator. Add
`scripts/fetch_upstreams.sh` that reads this manifest and checks out each source
into `third_party/<name>`. The script must be idempotent: rerunning it should
update an existing checkout to the pinned revision instead of failing.

Create a local home-miner control service under `services/`. The first slice may
use a miner simulator if a real miner backend would slow down the control-plane
proof, but the simulator must expose the same contract the real miner will use:
status, start, stop, mode selection, payout target, and health.

Add a bootstrap script, `scripts/bootstrap_home_miner.sh`, that brings the
service up, prepares deterministic local state, and emits a pairing bundle or
token for a client named `alice-phone`.

Add `scripts/pair_gateway_client.sh`, `scripts/read_miner_status.sh`, and
`scripts/set_mining_mode.sh`. The pair script must create a durable local client
record. The status script must print live miner state. The mode script must
change the miner from paused to balanced or performance and print an explicit
acknowledgement.

Add `scripts/no_local_hashing_audit.sh` as the off-device proof. It must inspect
the gateway client process and fail if hashing libraries, mining threads, or
unexpected CPU-bound worker loops are active on the client side.

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

2. Start the home-miner service.

       cd /home/r/coding/zend
       ./scripts/bootstrap_home_miner.sh

   Expected result: the script starts the local service and prints a pairing
   bundle or token for `alice-phone`.

3. Pair the gateway client.

       cd /home/r/coding/zend
       ./scripts/pair_gateway_client.sh --client alice-phone

   Expected result: the script records a paired client locally and prints a
   clear success message.

4. Read live miner status.

       cd /home/r/coding/zend
       ./scripts/read_miner_status.sh --client alice-phone

   Expected result: the script prints current miner status, selected mode,
   payout target, and a health summary.

5. Change the mining mode.

       cd /home/r/coding/zend
       ./scripts/set_mining_mode.sh --client alice-phone --mode balanced

   Expected result: the script prints an explicit acknowledgement that the home
   miner, not the client device, accepted the mode change.

6. Audit the gateway client for local hashing.

       cd /home/r/coding/zend
       ./scripts/no_local_hashing_audit.sh --client alice-phone

   Expected result: the script exits zero and reports that the gateway client is
   only a control plane and is not doing mining work itself.

## Validation and Acceptance

The work is accepted only when a novice can run the six concrete steps above in
order and observe all of the following:

- the home-miner service starts locally and can be paired to a client
- the gateway client can read live miner state
- the gateway client can safely issue a control action
- the proof shows that mining happens off-device
- the new control path is honest about what is and is not happening on the
  client

In addition to the end-to-end proof, add at least one automated test per new
script that validates argument parsing and expected failure behavior. For
example, `set_mining_mode.sh` must fail clearly if the client is unpaired, and
`no_local_hashing_audit.sh` must fail if given a known positive fixture.

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

    $ ./scripts/read_miner_status.sh --client alice-phone
    status=running
    mode=balanced

    $ ./scripts/no_local_hashing_audit.sh --client alice-phone
    checked: client process tree
    checked: local CPU worker count
    result: no local hashing detected

## Interfaces and Dependencies

The following files and interfaces must exist at the end of this milestone.

`upstream/manifest.lock.json` must be a machine-readable manifest that records,
for each upstream, a stable repository URL plus a pinned tag or commit SHA. The
script `scripts/fetch_upstreams.sh` must consume this manifest directly instead
of duplicating pins internally.

`scripts/fetch_upstreams.sh` must accept no required arguments and must clone or
refresh all pinned upstreams under `third_party/`.

`scripts/bootstrap_home_miner.sh` must prepare local miner state needed for the
smoke test. Its output must include a pairing bundle or token that later scripts
can use.

`scripts/pair_gateway_client.sh` must expose this interface:

    ./scripts/pair_gateway_client.sh --client <name>

It must record a paired client and print a clear success acknowledgement.

`scripts/read_miner_status.sh` must expose this interface:

    ./scripts/read_miner_status.sh --client <name>

It must print current miner status, selected mode, payout target, and health.

`scripts/set_mining_mode.sh` must expose this interface:

    ./scripts/set_mining_mode.sh --client <name> --mode <paused|balanced|performance>

It must perform a safe control action on the home miner and print an explicit
acknowledgement.

`scripts/no_local_hashing_audit.sh` must expose this interface:

    ./scripts/no_local_hashing_audit.sh --client <name>

It must exit non-zero when the gateway client appears to be doing hashing work.
