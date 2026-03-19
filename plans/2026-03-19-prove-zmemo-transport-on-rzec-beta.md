# Prove zmemo Transport on the rZEC Beta Network

This ExecPlan is a living document. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
be kept up to date as work proceeds.

`PLANS.md` at the repository root governs this ExecPlan. This document must be
maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

After this work, a new contributor should be able to start from a fresh clone
of this repository, bring up a self-hosted `rZEC` beta stack, create two test
identities, send the message `hello zmemo` as an encrypted shielded memo, read
that message from the recipient side, and prove that the server side never
prints or stores the plaintext in its ordinary logs and inspection commands.

This milestone matters because it proves the hardest product claim with working
behavior: `zmemo` can carry encrypted messages over a public-beta-style chain
that we operate ourselves, without leaning on community `lightwalletd`
endpoints and without pretending that memo support alone already equals a full
messaging product.

## Progress

- [x] (2026-03-19 22:47Z) Initial ExecPlan authored in the new `zmemo` repo.
- [ ] Create repo scaffolding for implementation artifacts: `docker/`,
  `scripts/`, `references/`, `upstream/`, and `state/README.md`.
- [ ] Add pinned upstream manifest and fetch script for `ZcashFoundation/zebra`,
  `zcash/lightwalletd`, and the mobile-client reference repos.
- [ ] Add a single-node self-hosted beta stack that runs `zebrad` and
  `lightwalletd` against the `rZEC` chain identity.
- [ ] Add deterministic bootstrap scripts that create two test identities,
  fund them, and submit one encrypted memo-bearing transfer.
- [ ] Add recipient-side read tooling that decrypts and prints the memo.
- [ ] Add server-side audit tooling that searches ordinary logs and inspection
  outputs for the plaintext and fails if it is found.
- [ ] Document transport proof transcripts and exact rerun steps.

## Surprises & Discoveries

- Observation: The source repo used for bootstrapping this repo keeps the spec
  guide at `SPEC.md`, not `SPECS.md`.
  Evidence: `/home/r/coding/fabro/SPEC.md` exists; no `SPECS.md` file exists.

- Observation: Existing `rZEC` work already captures useful chain-fork context,
  but it is framed as a Zebra fork project rather than a messaging product.
  Evidence: `/home/r/coding/rZEC/README.md` describes upstream-pinned Zebra,
  chain identity, and mining workflows instead of inbox or transport proof.

- Observation: Current Zodl/Zashi clients expose memo send flows and show the
  total fee produced by the proposal API, but the checked code paths do not
  expose a user-selectable multi-lane delivery fee model yet.
  Evidence: the iOS and Android review paths display `totalFeeRequired()` and
  proposal-derived fee state rather than a free-form custom fee input.

## Decision Log

- Decision: Name the canonical planning repo `zmemo`.
  Rationale: the name starts with `z`, stays close to the memo-native transport
  model, and avoids feeling like a public-feed or generic wallet repo.
  Date/Author: 2026-03-19 / Codex

- Decision: Keep `rZEC` as the working beta network name while using `zmemo` as
  the product and repo name.
  Rationale: the chain identity and the messaging product are separate durable
  concepts; renaming both at once would add churn before transport is proven.
  Date/Author: 2026-03-19 / Codex

- Decision: Make the first implementation slice a transport proof instead of a
  mobile UX fork or inbox feature build.
  Rationale: the highest-risk dependency is end-to-end encrypted transport on a
  self-hosted genesis-fork beta stack. Once that works, inbox and client
  features become product work instead of protocol guesswork.
  Date/Author: 2026-03-19 / Codex

- Decision: Do not promise configurable delivery-priority fee lanes in this
  first slice.
  Rationale: the currently reviewed wallet paths surface proposal-derived fees
  honestly, but they do not prove a user-selectable network-fee market yet. The
  first slice must prove transport without inventing unsupported fee controls.
  Date/Author: 2026-03-19 / Codex

## Outcomes & Retrospective

At authoring time, this plan has not yet been executed. Its current outcome is
that the project now has a concrete, outcome-shaped first slice: prove one
encrypted message end-to-end on self-hosted beta infrastructure before taking on
mobile polish, attention-ranking policies, or fee-lane customization.

## Context and Orientation

This repository currently contains planning documents only. `SPEC.md` explains
how durable specs should be written. `PLANS.md` explains how executable plans
must be authored and maintained. The accepted product boundary lives in
`specs/2026-03-19-zmemo-encrypted-messaging-beta.md`.

For this plan, "upstream" means an external repository that this repo depends
on conceptually but does not yet vendor. The critical upstreams are:
`ZcashFoundation/zebra` for the full node, `zcash/lightwalletd` for the light
client server, and the Zodl mobile client repos as reference consumers of memo
transport.

A "genesis fork" means a new public chain identity that starts from its own
first block rather than inheriting the history of Zcash mainnet. A "transport
proof" means runnable evidence that a sender can transmit an encrypted message
body through the beta stack and that only the intended recipient client can
read it.

The first concrete consumer of the work in this plan is a script-first agent
surface. The scripts created here are intentionally designed so that a human can
run them from a terminal and an agent can call them as tools later without a
different code path.

## Plan of Work

Start by creating the implementation directories that this plan assumes:
`docker/` for compose files and service configs, `scripts/` for repeatable
operator and proof commands, `references/` for chain identity notes and cost
assumptions, `upstream/` for lockfiles that pin external repos, and `state/`
for ignored local chain data. Add a short `state/README.md` so a novice knows
that local chain data is disposable and intentionally untracked.

Add `upstream/manifest.lock.json` as the single source of truth for external
repositories and pinned tags or commit SHAs. It must include `zebra`,
`lightwalletd`, `zodl-ios`, and `zodl-android`. Add
`scripts/fetch_upstreams.sh` that reads this manifest and checks out each source
into `third_party/<name>`. The script must be idempotent: rerunning it should
update an existing checkout to the pinned revision instead of failing.

Create a minimal single-node beta stack under `docker/`. The compose file should
run `zebrad` and `lightwalletd` on the `rZEC` chain identity using mounted data
directories under `state/`. This slice does not need a DNS seeder or
multi-region topology. It only needs enough infrastructure to sync, submit a
transaction, and let a light client consume compact blocks.

Add a bootstrap script, `scripts/bootstrap_public_beta.sh`, that brings the
stack up, waits for the services to report readiness, then prepares two test
identities named `alice` and `bob`. The script may use wallet SDK helpers, a
reference wallet CLI, or controlled fixtures, but it must leave the repo in a
state where later scripts can refer to those identities by name instead of by
opaque addresses.

Add `scripts/send_smoke_message.sh` and `scripts/read_smoke_message.sh`. The
send script must submit an encrypted memo-bearing transfer from `alice` to
`bob`, print the transaction ID, and print the fee that the stack actually used.
The read script must decrypt Bob's inbox and print the plaintext message body.
Both scripts must use the same transport boundary that future agent tools will
use.

Add `scripts/server_plaintext_audit.sh` as the privacy proof. It must accept a
search needle, scan ordinary service logs and server-side inspection commands,
and fail if the plaintext appears. It is acceptable for the script to document
which server surfaces it audits in this slice, but it must at minimum inspect
`docker compose logs`, `lightwalletd` output, and any node-level transaction
inspection command used during debugging.

Document every proof step in `references/transport-proof.md` with concise,
copiable transcripts. This document is not a replacement for the scripts. It is
the evidence that the scripts produced the expected outcome.

## Concrete Steps

Run all commands from the repository root.

1. Prepare pinned upstreams.

       cd /home/r/coding/zmemo
       ./scripts/fetch_upstreams.sh

   Expected result: the directory `third_party/` appears and contains checked
   out sources for Zebra, `lightwalletd`, and the reference client repos at the
   pinned revisions recorded in `upstream/manifest.lock.json`.

2. Start the beta stack.

       cd /home/r/coding/zmemo
       docker compose -f docker/compose.beta.yml up -d --build

   Expected result: `docker compose ps` shows healthy `zebrad` and
   `lightwalletd` services.

3. Bootstrap the test identities and initial funds.

       cd /home/r/coding/zmemo
       ./scripts/bootstrap_public_beta.sh

   Expected result: the script prints both test identities, records their local
   metadata under `state/`, and exits zero.

4. Send the smoke-test message.

       cd /home/r/coding/zmemo
       ./scripts/send_smoke_message.sh \
         --sender alice \
         --recipient bob \
         --message "hello zmemo"

   Expected result: the script prints a transaction ID and a real observed
   network fee. It must not claim multiple delivery lanes if the transport
   still exposes only one fee path.

5. Read the message on the recipient side.

       cd /home/r/coding/zmemo
       ./scripts/read_smoke_message.sh --recipient bob

   Expected result: the script prints `hello zmemo` as decrypted recipient-side
   content.

6. Audit the server side for plaintext leaks.

       cd /home/r/coding/zmemo
       ./scripts/server_plaintext_audit.sh --needle "hello zmemo"

   Expected result: the script exits zero and reports that the plaintext was not
   found in the audited server surfaces.

## Validation and Acceptance

The work is accepted only when a novice can run the six concrete steps above in
order and observe all of the following:

- the beta stack starts without using a shared public `lightwalletd` endpoint
- a real encrypted memo-bearing transfer is submitted through the self-hosted
  stack
- the recipient can decrypt and print the message body
- the sender receives a truthful observed network fee
- the server-side audit finds no plaintext copy of the message in normal logs or
  inspection output

In addition to the end-to-end proof, add at least one automated test per new
script that validates argument parsing and expected failure behavior. For
example, `send_smoke_message.sh` must fail clearly if either named test
identity is missing, and `server_plaintext_audit.sh` must fail if given a known
positive fixture log.

## Idempotence and Recovery

`scripts/fetch_upstreams.sh` must be safe to rerun. It should reset each local
upstream checkout to the pinned revision rather than assuming a clean clone.

`scripts/bootstrap_public_beta.sh` must either detect existing prepared state
and reuse it safely or wipe and recreate the named test identities in a
deterministic way.

If the local chain state becomes corrupt or stale, the recovery path must be
documented and tested:

       cd /home/r/coding/zmemo
       docker compose -f docker/compose.beta.yml down -v
       rm -rf state/*
       ./scripts/fetch_upstreams.sh
       docker compose -f docker/compose.beta.yml up -d --build
       ./scripts/bootstrap_public_beta.sh

The recovery path is acceptable only if it produces the same proofable outcome
without requiring manual edits.

## Artifacts and Notes

Keep the most important proof transcript in `references/transport-proof.md`.
When the milestone is complete, that file should contain a concise example like
this, updated with the real transaction ID and audited surfaces:

    $ ./scripts/send_smoke_message.sh --sender alice --recipient bob --message "hello zmemo"
    txid=0123abcd...
    fee=0.0001 rZEC

    $ ./scripts/read_smoke_message.sh --recipient bob
    hello zmemo

    $ ./scripts/server_plaintext_audit.sh --needle "hello zmemo"
    checked: docker compose logs zebrad
    checked: docker compose logs lightwalletd
    checked: node inspection surfaces
    result: plaintext not found

## Interfaces and Dependencies

The following files and interfaces must exist at the end of this milestone.

`upstream/manifest.lock.json` must be a machine-readable manifest that records,
for each upstream, a stable repository URL plus a pinned tag or commit SHA. The
script `scripts/fetch_upstreams.sh` must consume this manifest directly instead
of duplicating pins internally.

`scripts/fetch_upstreams.sh` must accept no required arguments and must clone or
refresh all pinned upstreams under `third_party/`.

`scripts/bootstrap_public_beta.sh` must prepare named identities and any local
state needed for the smoke test. Its output must include the resolved sender and
recipient addresses.

`scripts/send_smoke_message.sh` must expose this interface:

    ./scripts/send_smoke_message.sh \
      --sender <name> \
      --recipient <name> \
      --message <plaintext>

It must print both the submitted transaction ID and the actual fee used.

`scripts/read_smoke_message.sh` must expose this interface:

    ./scripts/read_smoke_message.sh --recipient <name>

It must print decrypted plaintext for the most recent unread message in the
recipient test inbox.

`scripts/server_plaintext_audit.sh` must expose this interface:

    ./scripts/server_plaintext_audit.sh --needle <plaintext>

It must exit non-zero when the plaintext is found on any audited server surface.
