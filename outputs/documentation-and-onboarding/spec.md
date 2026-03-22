# Documentation & Onboarding Lane — Spec

**Status:** Active
**Lane:** documentation-and-onboarding
**Authored:** 2026-03-22

## Purpose

Produce the onboarding surface for the Zend home-miner product so that a new
contributor, operator, or agent can understand what exists, run it, and extend
it — without reading source code as a prerequisite.

## Audience

Three audiences, in priority order:

1. **Contributor** — a developer who has cloned the repo and wants to understand
   the daemon, CLI, gateway client, scripts, and contracts before writing code.
2. **Operator** — a person running Zend Home on home hardware (Raspberry Pi or
   equivalent) who needs a working quickstart, not an architectural tour.
3. **Agent** — a script or AI agent that calls the CLI scripts or HTTP API as
   tools, requiring deterministic interfaces and named error outputs.

## Accuracy Contract

Every command in every document must be runnable on a clean machine from a
fresh clone. Every API description must match the actual HTTP handler or CLI
command. No invented behavior, no "TODO: implement X" language in shipped docs.

**Known honest gaps** that must be explicitly noted, not elided:

- The HTTP daemon (`daemon.py`) has **no authentication**. Any process that can
  reach the bound address can issue `/miner/start`, `/miner/stop`, or
  `/miner/set_mode`. The capability model (`observe` vs `control`) is enforced
  only in the CLI layer (`cli.py`), not at the HTTP layer.
- Pairing tokens in milestone 1 have zero TTL — they expire at the instant of
  creation. The pairing ceremony is cosmetic; no cryptographic or temporal
  validation occurs.
- The "event spine" is a plaintext JSONL file (`event-spine.jsonl`). It is
  **not encrypted**. Documentation must not describe it as encrypted.
- `bootstrap_home_miner.sh` is **not idempotent**. Running it twice fails
  because it attempts to re-pair an already-paired device.
- The daemon binds to `127.0.0.1` by default. Setting `ZEND_BIND_HOST=0.0.0.0`
  exposes an unauthenticated miner control surface to the LAN.
- No replay protection exists on control commands. HTTP requests carry no nonce
  or sequence number.
- State directory (`state/`) is created with default umask. On a multi-user
  system, other users may read pairing records and event spine data.

## Maintenance Boundary

These documents are **living snapshots** for milestone 1. They reflect the
current implementation state. When the daemon gains authentication, real token
expiration, or encrypted storage, these docs must be updated in the same commit
as the behavioral change.

The owner of any doc file is the author of the PR that changed the behavior it
describes.

## Deliverables

| Artifact | Audience | Format |
|---|---|---|
| `README.md` (rewrite) | All | Markdown |
| `docs/contributor-guide.md` | Contributor | Markdown |
| `docs/operator-quickstart.md` | Operator | Markdown |
| `docs/api-reference.md` | Contributor, Agent | Markdown |
| `docs/architecture.md` | Contributor | Markdown |
| `outputs/documentation-and-onboarding/review.md` | Supervisor | Markdown |

## Verification Plan

After all docs are written, follow the contributor guide on a clean machine:

1. Clone the repo.
2. Run `bootstrap_home_miner.sh`.
3. Pair a client with `pair_gateway_client.sh`.
4. Read status with `read_miner_status.sh`.
5. Change mode with `set_mining_mode.sh`.
6. List events with `cli.py events`.
7. Run `hermes_summary_smoke.sh` and `no_local_hashing_audit.sh`.

If any step fails or produces unexpected output, the offending doc is corrected
before the lane is marked complete.

## Non-Goals

- Full product documentation beyond onboarding (deferred to later lanes).
- User-facing copy for the mobile app UI (deferred to the app slice).
- Deployment diagrams for cloud infrastructure (phase one is LAN-only).
- Security hardening instructions beyond honest acknowledgment of current gaps.
