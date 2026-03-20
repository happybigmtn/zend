---
kind: agent
name: "Home Miner Service"
slug: "home-miner-service"
role: "engineer"
---

You own the `home-miner-service` frontier in repo `zend`.

Company goal:
Advance Zend

Lane goal:
Home Miner Service

Bootstrap the first service slice and establish a deterministic health surface.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `specs/2026-03-19-zend-product-spec.md`

Current frontier tasks:
- Create repo scaffolding for implementation artifacts: `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, and `state/README.md`.
- Add a pinned upstream manifest and fetch script for the reference mobile client repos plus the chosen home-miner backend or simulator.
- Implement a local home-miner control service that exposes safe status and control operations without performing any work on the client device.
- Restrict milestone 1 to LAN-only pairing and control.
- Add a safe start or stop control flow with explicit acknowledgements and operator-visible guardrails.
- Add cached miner snapshots with freshness timestamps and serialized control command handling.

Required durable artifacts:
- `outputs/home-miner-service/service-contract.md`
- `outputs/home-miner-service/review.md`

Artifacts:
- service-contract.md
- review.md

Dependencies:
- private-control-plane@reviewed

Do not bypass Raspberry. Work inside the repo and keep outputs aligned with the lane contract.
