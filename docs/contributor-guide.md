# Contributor Guide

This guide gets you from a fresh clone to a running local system and teaches
you the directory layout. No external dependencies beyond Python 3.

## Prerequisites

- Python 3.8+
- No pip packages required — the daemon and CLI use only the Python standard
  library
- A browser to open the gateway client UI

## Repository Layout

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Gateway client (no build step)
├── docs/
│   ├── architecture.md          # System diagrams and module explanations
│   ├── contributor-guide.md     # This file
│   ├── operator-quickstart.md    # Home hardware deployment guide
│   ├── api-reference.md         # Daemon + CLI reference
│   └── designs/                 # Design reviews and storyboards
├── plans/
│   └── 2026-03-19-build-zend-home-command-center.md  # ExecPlan
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon + bootstrap principal
│   ├── pair_gateway_client.sh   # Pair a named client
│   ├── read_miner_status.sh     # Read miner status snapshot
│   ├── set_mining_mode.sh       # Issue a control action
│   ├── hermes_summary_smoke.sh  # Test Hermes summary append
│   └── no_local_hashing_audit.sh  # Verify no local hashing
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py
│       ├── daemon.py            # LAN-only HTTP server + MinerSimulator
│       ├── cli.py               # CLI: bootstrap, pair, status, control, events
│       ├── store.py             # PrincipalId + GatewayPairing store
│       └── spine.py             # Append-only event journal
├── specs/
│   └── 2026-03-19-zend-product-spec.md  # Durable product spec
├── state/                       # Runtime state (gitignored)
│   ├── principal.json           # PrincipalId
│   ├── pairing-store.json      # Paired clients + capabilities
│   ├── event-spine.jsonl       # Append-only event journal
│   └── daemon.pid              # Daemon process ID
├── DESIGN.md                    # Visual + interaction design system
├── SPEC.md                      # Spec authoring guide
└── PLANS.md                     # ExecPlan authoring guide
```

## Dev Setup

```bash
# Clone the repo
git clone <repo-url>
cd zend

# Verify Python 3 is available
python3 --version

# No pip install needed — stdlib only

# Check that scripts are executable
ls -la scripts/*.sh
```

## Running the System

All commands run from the repository root.

### 1. Bootstrap the daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This:
- Creates `state/` if it doesn't exist
- Starts the daemon on `127.0.0.1:8080` (configurable via `ZEND_BIND_HOST`,
  `ZEND_BIND_PORT`)
- Writes a daemon PID to `state/daemon.pid`
- Creates `state/principal.json` with a `PrincipalId`
- Emits a pairing bundle for `alice-phone` with `observe` capability

Output looks like:
```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
```

### 2. Pair a client with control capability

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

Capability options: `observe` (read status), `control` (issue start/stop/mode
commands). Separate with commas.

### 3. Read status

```bash
./scripts/read_miner_status.sh --client alice-phone
```

If the client lacks `observe`, prints an authorization error.

### 4. Issue a control action

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop
```

If the client lacks `control`, prints an authorization error.

### 5. View the gateway UI

Open `apps/zend-home-gateway/index.html` in a browser. The UI polls
`http://127.0.0.1:8080/status` every 5 seconds.

Or serve it with a local server:

```bash
python3 -m http.server 9000 --directory apps/zend-home-gateway
# Then open http://localhost:9000
```

### 6. View the event spine

```bash
cd services/home-miner-daemon
python3 cli.py events --client alice-phone --kind all --limit 20
```

### 7. Stop the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Where state files live |
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI → daemon URL |

## Recovery

If state gets corrupted or you want a clean start:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Restart fresh
./scripts/bootstrap_home_miner.sh
```

## Code Map

### `daemon.py`

The `MinerSimulator` class is the milestone 1 miner backend. It exposes:
- `status` — `MinerStatus` enum: `RUNNING`, `STOPPED`, `OFFLINE`, `ERROR`
- `mode` — `MinerMode` enum: `PAUSED`, `BALANCED`, `PERFORMANCE`
- `start()`, `stop()`, `set_mode(mode)` — control operations, each
  protected by `threading.Lock()`
- `get_snapshot()` — returns a `MinerSnapshot` dict with freshness timestamp

The `GatewayHandler` class maps HTTP paths to `MinerSimulator` methods.
No authentication is performed here.

### `cli.py`

Each subcommand maps to one file operation or one daemon HTTP call:
- `bootstrap` → `store.load_or_create_principal()` + `spine.append_pairing_granted()`
- `pair` → `store.pair_client()` + spine events
- `status` → `daemon_call('GET', '/status')` with capability check
- `control` → `daemon_call('POST', '/miner/...')` with capability check
- `events` → `spine.get_events()`

### `store.py`

`Principal` (one per installation) and `GatewayPairing` (one per paired device)
are stored as JSON files. `has_capability(device_name, cap)` checks the
pairing store.

### `spine.py`

`EventKind` enum names all event types. `_load_events()` reads JSONL;
`_save_event()` appends. `get_events()` returns most-recent-first with
optional kind filter.

## Running Tests

No formal test suite exists yet. Validate the system by running the quickstart
scripts in sequence:

```bash
./scripts/bootstrap_home_miner.sh --stop 2>/dev/null || true
rm -rf state/*
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/hermes_summary_smoke.sh --client alice-phone
./scripts/no_local_hashing_audit.sh --client alice-phone
./scripts/bootstrap_home_miner.sh --stop
```

All commands should exit 0.

## Adding a New Daemon Endpoint

1. Add the route to `GatewayHandler.do_GET` or `do_POST` in `daemon.py`
2. Add the corresponding method to `MinerSimulator`
3. Add a CLI subcommand or wrapper script in `cli.py` or `scripts/`
4. Add the event kind to `EventKind` in `spine.py` if the action should be
   recorded in the spine
5. Document in `docs/api-reference.md`

## Security Notes for Contributors

The daemon has no authentication. Any process on the same machine (or LAN, if
bound externally) can issue start/stop/mode commands. This is the milestone 1
design. Do not present the daemon as secure in documentation or comments.

The event spine is plaintext JSONL. PrincipalIds, device names, control
commands, and capability grants are all readable in `state/event-spine.jsonl`.

Pairing tokens never expire. The `token_expires_at` field in the pairing store
is set to the current time, not a future time.

Capability enforcement lives only in `cli.py`. Calling the daemon directly with
`curl` bypasses all capability checks.
