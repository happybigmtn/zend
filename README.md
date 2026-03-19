# zmemo

`zmemo` is the canonical planning repository for an agent-first encrypted
messaging product built on shielded Zcash-style memo transactions.

The working public beta network name is `rZEC`. The product decision locked in
here is simple: `zmemo` is an inbox-first encrypted messaging system, not a
public social feed. Every message body must remain encrypted end-to-end.

This repository starts as a docs-first control point for the project. It holds
the durable spec, the executable implementation plan, and the repo-level rules
for writing future specs and plans.

## Canonical Documents

- `SPEC.md`: guide for durable specs
- `PLANS.md`: guide for executable implementation plans
- `specs/2026-03-19-zmemo-encrypted-messaging-beta.md`: accepted capability
  spec for the product and beta network boundary
- `plans/2026-03-19-prove-zmemo-transport-on-rzec-beta.md`: first ExecPlan for
  proving self-hosted encrypted transport on a genesis-fork beta network

## Current Scope

This repo does not yet contain implementation code for the chain, mobile
clients, or agent runtime. The first implementation slice is intentionally
focused on transport proof: run a self-hosted beta stack, send one encrypted
memo message end-to-end, and prove that the server side cannot read the
plaintext.
