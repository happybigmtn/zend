# Contributor Guide

This guide gets a new contributor from a fresh clone to a running system and
the current verification workflow. It assumes no prior knowledge of the
repository beyond what is in this file.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or newer
- `bash`
- `curl`
- `git`

Zend's runtime uses only the Python standard library. If you want to run the
test command locally, create a virtual environment and install `pytest` there:

```
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip pytest
```

### Clone and Verify

```
git clone <repo-url>
cd zend
python3 --version   # should be 3.10 or higher
```

### Run the Quickstart

```
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: <number>)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "<timestamp>"
}
[INFO] Bootstrap complete
```

If you see `GatewayUnavailable` or a port error, see **Troubleshooting** below.

### Inspect the Command Center Shell

```
open apps/zend-home-gateway/index.html
# or on Linux:
xdg-open apps/zend-home-gateway/index.html
```

This lets you inspect the single-file UI shell, but most browsers will block
its fetches to the daemon when opened from `file://` because the daemon does
not emit CORS headers. Use the CLI commands below as the verified dev workflow
until the UI is served from the daemon.

## Project Structure

### `services/home-miner-daemon/`

This is the core of Zend. Everything else is a client of this service.

- **`daemon.py`** — `MinerSimulator` class holds miner state (status, mode,
  hashrate, temperature, uptime). `GatewayHandler` maps HTTP paths to miner
  operations. `run_server()` starts the threaded HTTP server. The daemon binds
  to `127.0.0.1:8080` in dev; set `ZEND_BIND_HOST` and `ZEND_BIND_PORT` env
  vars to change this.

- **`cli.py`** — `cmd_status`, `cmd_health`, `cmd_bootstrap`, `cmd_pair`,
  `cmd_control`, `cmd_events`. Each subcommand is a function. CLI calls the
  daemon over HTTP and prints JSON. Authorization checks happen here (observe vs
  control capability). Control commands append receipts to the event spine.

- **`store.py`** — `load_or_create_principal()` returns the stable `Principal`
  identity. `pair_client(device_name, capabilities)` creates a pairing record.
  `get_pairing_by_device(device_name)` looks up a paired client.
  `has_capability(device_name, capability)` checks permissions. All state lives
  in `state/` as JSON files.

- **`spine.py`** — append-only JSONL event journal. `append_event()` writes one
  JSON line to `state/event-spine.jsonl`. `get_events(kind, limit)` reads and
  filters. Event kinds: `pairing_requested`, `pairing_granted`,
  `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`,
  `user_message`. The spine is the source of truth; the inbox is a derived
  view.

### `apps/zend-home-gateway/`

- **`index.html`** — single-file HTML command center. No build step. Fetches
  `/status`, `/health`, and POSTs to `/miner/start`, `/miner/stop`,
  `/miner/set_mode`. Polls every 5 seconds. Has four screens: Home, Inbox,
  Agent, Device with a bottom tab bar.

### `scripts/`

Each script wraps one or more CLI subcommands. `bootstrap_home_miner.sh` is
safe to rerun; pairing commands reject duplicate device names instead of
silently overwriting them.

- **`bootstrap_home_miner.sh`** — starts the daemon, waits for it to be ready,
  then runs `cli.py bootstrap`. Creates `state/` directory and principal identity.
  `--daemon` starts without bootstrapping. `--stop` kills the daemon. `--status`
  prints current miner state.

- **`pair_gateway_client.sh`** — pairs a named client. `--client <name>` is
  required. `--capabilities observe,control` grants observe by default. Prints
  the paired device name and granted capabilities.

- **`read_miner_status.sh`** — reads current miner status for a paired client.
  Requires `--client <name>`. Prints JSON plus script-friendly `status=<value>`
  lines.

- **`set_mining_mode.sh`** — issues a control command. Requires `--client
  <name>`. Use `--mode <paused|balanced|performance>` or `--action
  <start|stop>`. Requires the client to have `control` capability.

- **`no_local_hashing_audit.sh`** — stub for the off-device mining proof.
  Currently exits 0 (pass). Replace with real process inspection for production.

### `references/`

Contracts and design notes. These define what the code must do.

- **`inbox-contract.md`** — defines `PrincipalId` as the stable identity owned
  by the user. Gateway pairing records and future inbox records both reference
  the same `PrincipalId`.

- **`event-spine.md`** — defines event kinds and the append-only journal
  contract. The spine is the source of truth; the inbox is a projection.

- **`error-taxonomy.md`** — named failure classes: `PairingTokenExpired`,
  `PairingTokenReplay`, `GatewayUnauthorized`, `GatewayUnavailable`,
  `MinerSnapshotStale`, `ControlCommandConflict`, `EventAppendFailed`,
  `LocalHashingDetected`.

- **`hermes-adapter.md`** — defines how Hermes connects through the Zend adapter.
  Milestone 1 is Hermes observe-only plus summary append.

## Making Changes

### Edit Code

All modules live in `services/home-miner-daemon/`. Edit the Python files
directly. No type-checker, no linter, no formatter is configured; follow the
stdlib-only convention.

### Run Tests

```
python3 -m pytest services/home-miner-daemon/ -v
```

`pytest` is a dev-only tool; the daemon itself remains stdlib-only. At the
moment this repo does not contain collected tests under
`services/home-miner-daemon/`, so the command currently exits after collecting
zero tests. Add `test_<module>.py` files next to each module as coverage lands.

### Verify the Quickstart Still Works

```
./scripts/bootstrap_home_miner.sh --stop   # clean up any running daemon
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Expected: JSON with `"status": "stopped"` or `"running"`.

### Verify the HTML Command Center Limitation

1. Start the daemon: `./scripts/bootstrap_home_miner.sh`
2. Open `apps/zend-home-gateway/index.html` in a browser
3. Confirm the page renders the Zend Home shell
4. Expect the connection banner in current browsers unless you add a same-origin host for the UI and API
5. Use the CLI commands above to verify live status and control behavior

## Coding Conventions

### Stdlib Only

Do not add `pip install` dependencies. If you need something not in the
stdlib, open an issue first.

### Error Handling

Functions that can fail return `dict` with a `"success"` boolean or raise a
typed exception. Do not use bare `except Exception`. Handle specific cases.

### Naming

- Classes: `CamelCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Modules: `snake_case.py`

### Thread Safety

`MinerSimulator` uses `threading.Lock` around all state mutations. Any new
shared state in `daemon.py` must follow the same pattern.

### JSON

Use `json.dumps()` with default serialization. Dates are ISO 8601 strings.
Do not invent custom encoders.

### File Paths

State files are under `state/` (gitignored). Resolve paths relative to the
module file using `Path(__file__).resolve().parents[2]` to find the repo root,
so scripts work from any `cwd`.

## Plan-Driven Development

Work follows ExecPlans. Each plan lives in `plans/` and has a `Progress`
section that must be kept up to date as you code. See `PLANS.md` for the full
ExecPlan authoring rules.

When you make a key design decision while coding, record it in the plan's
`Decision Log` section immediately. Future contributors will thank you.

## Design System

See `DESIGN.md` for the visual and interaction language. Key points:

- Fonts: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- Colors: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`,
  Signal Red `#B44C42`
- No neon greens, exchange-red candlesticks, or purple SaaS gradients
- Touch targets: minimum `44x44` logical pixels
- WCAG AA contrast minimum
- `prefers-reduced-motion` respected

When editing `apps/zend-home-gateway/index.html`, follow the component
vocabulary in `DESIGN.md`.

## Submitting Changes

- Branch naming: `feat/<short-description>` or `fix/<short-description>`
- Keep commits atomic and message-ful
- Run `./scripts/bootstrap_home_miner.sh --stop` before committing to leave a
  clean daemon state

## Troubleshooting

### Daemon won't start (port in use)

```
fuser -k 8080/tcp
./scripts/bootstrap_home_miner.sh
```

### Bootstrap fails with `GatewayUnavailable`

The daemon may have crashed. Check `state/daemon.pid` and kill the stale PID,
then retry:

```
kill $(cat state/daemon.pid) 2>/dev/null || true
./scripts/bootstrap_home_miner.sh
```

### HTML command center shows "Unable to connect"

- Confirm the daemon is running: `python3 services/home-miner-daemon/cli.py health`
- Check the daemon is binding to the expected host: `echo $ZEND_BIND_HOST`
  (defaults to `127.0.0.1`)
- If accessing from a different machine, set `ZEND_BIND_HOST=0.0.0.0` and open
  the firewall on port 8080. See `docs/operator-quickstart.md` for the full
  LAN deployment guide.

### `control` action fails with `unauthorized`

The bootstrap client (`alice-phone`) is paired with `observe` only. Pair a
different device name with `control`:

```
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```
