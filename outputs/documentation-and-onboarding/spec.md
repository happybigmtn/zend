# Documentation & Onboarding — Specification

**Status:** Accepted
**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22

## Purpose / User-Visible Outcome

A new contributor or home-operator can land on the repository, understand what Zend is and what problem it solves, set up a working local environment, and complete the full onboarding flow — pairing a client to the daemon, reading miner status, and exercising control — entirely from documentation without asking a human. An agent can do the same using only the documented CLI commands.

## Scope

This lane covers all human- and agent-facing documentation surfaces:

| Artifact | Location | Audience |
|---|---|---|
| Project README | `README.md` | Any visitor |
| Contributor Guide | `docs/contributor-guide.md` | New contributors |
| Operator Quickstart | `docs/operator-quickstart.md` | Home hardware operators |
| API Reference | `docs/api-reference.md` | Developers and agents |
| Architecture Reference | `docs/architecture.md` | Engineers evaluating or extending Zend |

## Quality Standards

Every documentation artifact must meet these standards:

### Completeness

- Every CLI script in `scripts/` is documented with a usage line, purpose paragraph, argument table, and at least one worked example.
- Every daemon HTTP endpoint is documented with method, path, request body shape, response body shape, and error codes.
- Every state file or directory is named and its purpose stated.
- The README must answer "what is this?" in the first three sentences.

### Repo-Specificity

- All file paths are repository-relative (e.g., `services/home-miner-daemon/daemon.py`).
- All variable names, function names, and constants match exactly what the code contains.
- All script names and flags match exactly what the shell scripts accept.
- No generic placeholder commands like "run `npm install`" without specifying the working directory and what is being installed.

### Accuracy

- Commands shown must be copy-paste runnable from a clean clone.
- Output excerpts must reflect actual behavior, not approximated behavior.
- The README quickstart must be verified end-to-end on a clean machine before this lane is considered complete.

### Onboarding Experience

- A contributor who clones the repo and follows the README quickstart must reach a working daemon + paired client + visible miner status without reading any other document.
- The operator quickstart must cover: hardware requirements, OS prerequisites, daemon startup, LAN binding, pairing, and basic control — all without requiring a developer terminal beyond `git`, `python3`, and `curl`.

## Required Artifacts

### README.md

The README must contain, in this order:

1. **One-line description** — what Zend is in one sentence.
2. **Problem statement** — why it exists (private command center for home miner; phone does not mine).
3. **Architecture overview** — a text diagram showing the mobile client, Zend gateway contract, home-miner daemon, event spine, and Hermes adapter.
4. **Quickstart** — five steps (clone, install deps, start daemon, pair, read status) with exact commands and expected outputs.
5. **Key concepts** — `PrincipalId`, `GatewayCapability`, `MinerSnapshot`, `EventSpine` defined in plain language.
6. **Repository structure** — one sentence per top-level directory.
7. **Current milestone status** — what milestone 1 does and does not include.

### `docs/contributor-guide.md`

Must cover:

- Development environment prerequisites (Python 3, git).
- How to run `scripts/fetch_upstreams.sh` and what it does.
- How to start the daemon in development mode (`scripts/bootstrap_home_miner.sh`).
- How to run individual CLI commands for testing (`python3 services/home-miner-daemon/cli.py --help`).
- How to read the event spine for debugging.
- How to run the no-local-hashing audit.
- How to run the gateway client locally.
- The design system constraints (`DESIGN.md` is required reading).
- The spec and plan conventions (`SPEC.md`, `PLANS.md`).
- How to add a new CLI command.

### `docs/operator-quickstart.md`

Must cover:

- Hardware requirements (what class of machine runs the daemon; minimum RAM/disk).
- Supported OS list (Ubuntu 22.04+, macOS 13+, Raspberry Pi OS 12+).
- Network requirements (daemon binds LAN-only; operator must know their LAN subnet).
- Installation steps: clone, install Python 3, start daemon, pair a client.
- How to configure `ZEND_BIND_HOST` and `ZEND_BIND_PORT` for LAN access.
- How to verify the daemon is reachable from a mobile device on the same LAN.
- How to stop the daemon cleanly.
- What the event spine contains and where it lives on disk (`state/event-spine.jsonl`).
- What "LAN-only" means in plain language — no internet-facing control surface.

### `docs/api-reference.md`

Must document every endpoint in the daemon:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Daemon health check |
| GET | `/status` | Current `MinerSnapshot` |
| POST | `/miner/start` | Start mining |
| POST | `/miner/stop` | Stop mining |
| POST | `/miner/set_mode` | Set mode (`paused`\|`balanced`\|`performance`) |

For each endpoint, document:
- Request body (if applicable) — JSON fields with types
- Success response — status code and JSON body shape
- Error responses — status codes and JSON error shape
- Authorization — which `GatewayCapability` is required (if any)

Also document the CLI subcommands (`bootstrap`, `pair`, `status`, `health`, `control`, `events`) with their flags and output shapes.

### `docs/architecture.md`

Must contain:

- **System diagram** (ASCII text) showing all components and data flows.
- **Module inventory** — one section per component with: location, responsibility, key files, and key runtime dependencies.
- **Pairing and authority state machine** — describe the unpaired → paired_observer → paired_controller lifecycle.
- **Event spine routing** — which events flow through the spine, which component appends each, and how the inbox is derived.
- **Hermes adapter boundary** — what Zend explicitly grants to Hermes and what it cannot do without an explicit grant.
- **LAN-only guarantee** — how the daemon enforces LAN binding and why this matters.
- **State file inventory** — all files in `state/` with their purpose and persistence guarantees.

## Out of Scope

- Production deployment guides beyond LAN home setup.
- Kubernetes or Docker deployment.
- Remote access or tunneling setup.
- Payout configuration.
- Rich inbox UX documentation (milestone 1+ only).

## Acceptance Criteria

- [ ] README.md quickstart runs end-to-end on a clean machine.
- [ ] All five documentation artifacts exist at their specified paths.
- [ ] Every daemon endpoint is documented with request/response shapes.
- [ ] Every CLI script is documented with usage and at least one example.
- [ ] The operator quickstart requires only `git`, `python3`, and `curl` on a supported OS.
- [ ] The architecture doc contains a system diagram, module inventory, and state file inventory.
- [ ] No file paths in docs reference external repositories or non-existent files.
