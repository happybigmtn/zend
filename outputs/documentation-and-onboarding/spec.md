# Documentation & Onboarding Lane — Spec

**Status:** In Progress
**Date:** 2026-03-22
**Inputs:** `README.md`, `SPEC.md`, `PLANS.md`, `DESIGN.md`, `specs/2026-03-19-zend-product-spec.md`, `plans/2026-03-19-build-zend-home-command-center.md`

## Purpose

Produce all documentation needed so a new contributor, operator, or API consumer can self-serve without reading source code or ExecPlan internals.

## System Overview

Zend is a private command center for a home miner. The phone (or script) is the control plane; the home miner does the actual hashing. Encrypted Zcash-family memo transport carries messages and receipts. The milestone 1 implementation consists of:

- **`services/home-miner-daemon/daemon.py`** — LAN-only HTTP server with `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints. Uses a `MinerSimulator` that exposes the same contract a real miner backend would use.
- **`services/home-miner-daemon/cli.py`** — CLI with `bootstrap`, `pair`, `status`, `control`, and `events` subcommands. Enforces capability checks (`observe`/`control`) at the CLI layer.
- **`services/home-miner-daemon/store.py`** — Principal and pairing store. Manages `PrincipalId` (stable user identity) and `GatewayPairing` records with `observe`/`control` capabilities.
- **`services/home-miner-daemon/spine.py`** — Append-only event journal (`event-spine.jsonl`). Event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`.
- **`apps/zend-home-gateway/index.html`** — Single-page gateway client with four destinations (Home, Inbox, Agent, Device). Mobile-first, uses `Space Grotesk` + `IBM Plex Sans` + `IBM Plex Mono`.
- **`scripts/`** — Shell wrappers: `bootstrap_home_miner.sh`, `pair_gateway_client.sh`, `read_miner_status.sh`, `set_mining_mode.sh`, `hermes_summary_smoke.sh`, `no_local_hashing_audit.sh`.

**Security posture (honest disclosure required in all docs):** The daemon has NO authentication at the HTTP layer. Capability enforcement exists only in `cli.py`, not in `daemon.py`. Pairing tokens never expire (expiration time is set to `now`). The event spine is plaintext JSONL, not encrypted. These are milestone 1 limitations.

## Required Artifacts

| File | Description |
|------|-------------|
| `README.md` | Front door: what Zend is, quickstart (5 steps), architecture overview, key facts |
| `docs/contributor-guide.md` | Dev setup: Python 3, stdlib only, directory layout, running scripts, running tests |
| `docs/operator-quickstart.md` | Home hardware deployment: hardware requirements, LAN binding, bootstrap, pairing, daemon management, security caveats |
| `docs/api-reference.md` | All daemon endpoints + CLI subcommands with request/response shapes and error codes |
| `docs/architecture.md` | System diagrams, module explanations, data flow, pairing state machine, security posture |
| `outputs/documentation-and-onboarding/spec.md` | This file |
| `outputs/documentation-and-onboarding/review.md` | Prior review documenting the silent failure of the specify stage |

## Quickstart (for README)

```
# 1. Start the daemon
./scripts/bootstrap_home_miner.sh

# 2. Pair a client (observe-only by default)
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# 3. Read miner status
./scripts/read_miner_status.sh --client alice-phone

# 4. Change mining mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 5. View the gateway UI (open in browser)
open apps/zend-home-gateway/index.html
```

## Acceptance Criteria

- README quickstart works on a clean machine with Python 3
- Contributor guide names every directory and script
- Operator guide discloses the LAN-only default, no-auth daemon, and plaintext spine
- API reference covers all 5 daemon endpoints and 6 CLI subcommands with JSON shapes
- Architecture doc has the three diagrams from the ExecPlan (system, pairing state machine, data flow)
- All docs use honest language about milestone 1 security limitations
