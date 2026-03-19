# Zend

`Zend` is the canonical planning repository for an agent-first product that
combines encrypted Zcash-based messaging with a mobile gateway into a home miner.

The durable product decision locked in here is simple: the phone is the control
plane and the home miner is the workhorse. Mining does not happen on-device.
Encrypted messaging continues to rely on shielded Zcash-family memo transport.

This repository starts as a docs-first control point for the project. It holds
the durable spec, the executable implementation plan, and the repo-level rules
for writing future specs and plans.

## Canonical Documents

- `SPEC.md`: guide for durable specs
- `PLANS.md`: guide for executable implementation plans
- `specs/2026-03-19-zend-product-spec.md`: accepted capability spec for the
  product boundary
- `plans/2026-03-19-prove-zend-home-miner-gateway.md`: first ExecPlan for
  proving the mobile-to-home-miner control plane

## Current Scope

This repo does not yet contain implementation code for the mobile app, the home
miner service, or the agent runtime. The first implementation slice is focused
on proving the gateway model: pair a mobile or script client with a home miner,
surface live miner state, and control mining remotely without hashing on the
phone.
