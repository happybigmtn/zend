# Contributor Guide

This guide gets a new contributor from a fresh clone to a working, understood
local environment. Read it before reading source code.

## Repository Layout

```
/
├── README.md                          ← start here
├── SPEC.md                           ← how to write durable specs
├── PLANS.md                          ← how to write executable plans
├── DESIGN.md                         ← visual and interaction system
├── TODOS.md                          ← deliberate deferrals
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py                 ← LAN-only HTTP API (no auth)
│       ├── cli.py                    ← CLI with capability checks
│       ├── store.py                  ← principal + pairing records
│       └── spine.py                 ← append-only event journal (plaintext)
├── scripts/
│   ├── bootstrap_home_miner.sh       ← start daemon + bootstrap principal
│   ├── pair_gateway_client.sh        ← pair a named client
│   ├── read_miner_status.sh          ← read live miner snapshot
│   ├── set_mining_mode.sh            ← issue safe control action
│   ├── hermes_summary_smoke.sh       ← append Hermes event to spine
│   └── no_local_hashing_audit.sh     ← prove client does no hashing
├── specs/
│   └── 2026-03-19-zend-product-spec.md
├── plans/
│   └── 2026-03-19-build-zend-home-command-center.md
└── state/                            ← runtime state (gitignored)
    ├── principal.json                ← shared identity
    ├── pairing-store.json           ← device + capabilities
    ├── event-spine.jsonl            ← all operational events (plaintext)
    └── daemon.pid                   ← daemon process ID
```

## Prerequisites

- Python 3.10+
- `curl` (for health checks)
- `git`

No external services required. The daemon includes a miner simulator.

## Dev Setup

```bash
# Clone the repo
git clone <repo-url>
cd <repo-name>

# No dependencies to install — the daemon uses only stdlib
python3 --version   # should be 3.10 or higher
```

## Starting the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

What it does:
1. Stops any running daemon (from prior run).
2. Starts `daemon.py` on `127.0.0.1:8080` (LAN-only by default).
3. Creates `state/principal.json` (if absent).
4. Runs bootstrap via CLI to emit principal + pairing info.

**Not idempotent:** running it twice will fail at the pairing step because
`alice-phone` is already paired. To recover:

```bash
rm -f state/principal.json state/pairing-store.json state/event-spine.jsonl
./scripts/bootstrap_home_miner.sh
```

Or use `--stop` to shut down cleanly before re-bootstrapping:

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## CLI Reference

All commands run from the repo root, or from `services/home-miner-daemon/` with
`ZEND_STATE_DIR` set.

```bash
# Bootstrap principal identity (also done by bootstrap_home_miner.sh)
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone

# Pair a new client
python3 services/home-miner-daemon/cli.py pair --device bob-phone --capabilities observe
python3 services/home-miner-daemon/cli.py pair --device carol-phone --capabilities observe,control

# Read miner status (requires observe or control capability)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control the miner (requires control capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# List events from the spine
python3 services/home-miner-daemon/cli.py events --client alice-phone
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

## Capability Model

| Capability | Can read status | Can control miner |
|---|---|---|
| `observe` | ✅ | ❌ |
| `control` | ✅ | ✅ |

**Important:** Capability checks live in `cli.py`, not in `daemon.py`. The HTTP
daemon accepts all requests without authentication. Any process that can reach
`127.0.0.1:8080` (or whatever `ZEND_BIND_HOST` is set to) can issue control
commands without a capability check.

## Event Spine

The event spine (`state/event-spine.jsonl`) is the source of truth for all
operational events. It is an append-only JSONL file, **not encrypted**.

Event kinds:

| Kind | When it appears |
|---|---|
| `pairing_requested` | Client initiates pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed (not yet implemented) |
| `miner_alert` | Miner reports a warning or error |
| `control_receipt` | Control command accepted or rejected |
| `hermes_summary` | Hermes agent appends a summary |
| `user_message` | Encrypted user message (not yet implemented) |

## Testing the Off-Device Mining Claim

```bash
# After bootstrap and pairing:
./scripts/no_local_hashing_audit.sh --client alice-phone
```

This grep-searches the daemon Python files for unexpected hashing code and
inspects the process tree. It exits 0 when no local hashing is detected.

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `ZEND_STATE_DIR` | `$(pwd)/state` | Where principal, pairing, and spine live |
| `ZEND_BIND_HOST` | `127.0.0.1` | **Do not set to `0.0.0.0` in milestone 1** |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI uses this to reach daemon |

## Running Without Scripts (Direct Python)

```bash
# Start daemon directly
cd services/home-miner-daemon
ZEND_STATE_DIR=../../state python3 daemon.py

# In another terminal, use the CLI
cd services/home-miner-daemon
ZEND_STATE_DIR=../../state python3 cli.py status --client alice-phone
```

## Adding a Feature

1. Read `SPEC.md` and `PLANS.md` before adding any durable spec.
2. For architectural changes, write a spec first, then a plan.
3. For bug fixes or small changes, a plan is often enough.
4. Keep `plans/2026-03-19-build-zend-home-command-center.md` up to date
   as you work.
5. All scripts must be idempotent or clearly document their non-idempotence.
6. Every new CLI command must produce machine-parseable JSON on both success
   and failure.

## Known Gaps in Milestone 1

These are known honest gaps. Do not write documentation that claims behavior
that does not exist:

- **No HTTP authentication** — the daemon accepts all requests
- **Zero-TTL pairing tokens** — tokens expire at creation; no temporal validation
- **Plaintext event spine** — `event-spine.jsonl` is not encrypted
- **Bootstrap not idempotent** — re-running bootstrap fails on re-pairing
- **No replay protection** — control commands carry no nonce
- **State dir permissions** — default umask; other users may read state

See `docs/architecture.md` for the full system contract.
