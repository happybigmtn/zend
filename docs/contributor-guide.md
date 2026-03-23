# Contributor Guide

This guide helps you set up a development environment, understand the codebase, and make changes to Zend. It assumes you are comfortable with the command line and have Python 3.10+ installed.

## Dev Environment Setup

### 1. Clone and Enter the Repo

```bash
git clone <repo-url> && cd zend
```

### 2. Verify Python Version

```bash
python3 --version  # Must be 3.10 or higher
```

### 3. No Virtual Environment Needed

Zend uses only Python standard library modules. No `pip install` required. You can work directly in the repo.

### 4. Verify the Setup

```bash
# Start the daemon
./scripts/bootstrap_home_miner.sh

# In another terminal, check health
curl http://127.0.0.1:8080/health

# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop
```

## Running Locally

### Starting the Daemon

```bash
# Full bootstrap: stop existing daemon, start fresh, create principal
./scripts/bootstrap_home_mining.sh

# Start daemon only
./scripts/bootstrap_home_miner.sh --daemon

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Check daemon status
./scripts/bootstrap_home_miner.sh --status
```

### Pairing a Client

```bash
# Pair with observe capability (default)
./scripts/pair_gateway_client.sh --client my-phone

# Pair with observe and control
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Reading Status

```bash
# Via script
./scripts/read_miner_status.sh --client my-phone

# Via CLI directly
python3 services/home-miner-daemon/cli.py status --client my-phone

# Via HTTP
curl http://127.0.0.1:8080/status
```

### Controlling the Miner

```bash
# Set mining mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Start mining
./scripts/set_mining_mode.sh --client my-phone --action start

# Stop mining
./scripts/set_mining_mode.sh --client my-phone --action stop
```

### Opening the Command Center

Open `apps/zend-home-gateway/index.html` in your browser. The command center connects to `http://127.0.0.1:8080` by default.

## Project Structure

### `services/home-miner-daemon/`

The daemon exposes the HTTP API and runs the miner simulator.

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server (`BaseHTTPRequestHandler`) and miner simulator. Handles `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. |
| `cli.py` | CLI for pairing, status, control, and event queries. Wraps daemon HTTP calls with local auth checks. |
| `spine.py` | Event spine: append-only JSONL journal. Functions: `append_event()`, `get_events()`, `append_pairing_*()`, `append_control_receipt()`. |
| `store.py` | Principal and pairing records. Functions: `load_or_create_principal()`, `pair_client()`, `has_capability()`. |

### `apps/zend-home-gateway/`

The HTML command center UI.

| File | Purpose |
|------|---------|
| `index.html` | Single-file mobile-first command center. Fetches status from daemon, renders Home/Inbox/Agent/Device screens, posts control actions. |

### `scripts/`

Operator and proof scripts.

| File | Purpose |
|------|---------|
| `bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing bundle. |
| `pair_gateway_client.sh` | Pairs a new gateway client with capabilities. |
| `read_miner_status.sh` | Reads live miner status with freshness timestamp. |
| `set_mining_mode.sh` | Changes mining mode or starts/stops mining. |
| `hermes_summary_smoke.sh` | Tests Hermes adapter connection. |
| `no_local_hashing_audit.sh` | Verifies off-device mining (process tree inspection). |

### `references/`

Architecture contracts that define the system.

| File | Purpose |
|------|---------|
| `event-spine.md` | Event spine contract: event kinds, schemas, routing rules. |
| `hermes-adapter.md` | Hermes adapter contract: authority scopes, adapter interface. |
| `error-taxonomy.md` | Named error classes with user messages and rescue actions. |
| `observability.md` | Structured log events, metrics, audit log format. |

## Making Changes

### 1. Understand the Plan

Read `plans/2026-03-19-build-zend-home-command-center.md` to understand the current milestone scope. Check `genesis/plans/` for future plans.

### 2. Make the Change

- Edit Python files in `services/home-miner-daemon/`
- Edit the HTML in `apps/zend-home-gateway/`
- Add or update scripts in `scripts/`
- Update references in `references/`

### 3. Run the Scripts

```bash
# Restart daemon
./scripts/bootstrap_home_miner.sh

# Verify health
curl http://127.0.0.1:8080/health

# Test your change
./scripts/read_miner_status.sh --client my-phone
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

### 4. Verify No Local Hashing

```bash
./scripts/no_local_hashing_audit.sh --client my-phone
```

### 5. Test Edge Cases

- What happens when the daemon is offline?
- What happens with an observe-only client trying to control?
- What happens when the mode is already set?

## Coding Conventions

### Python Style

- Use `snake_case` for functions and variables
- Use `PascalCase` for classes and enums
- Add docstrings to all public functions
- Keep functions short (under 50 lines when possible)

### Error Handling

- Use named error codes from `references/error-taxonomy.md`
- Return structured JSON errors with `{"error": "CODE", "message": "..."}`
- Log errors to stderr with context

### Imports

- Use only Python standard library modules
- Avoid external dependencies unless absolutely necessary
- Group imports: stdlib, then local (with a blank line between)

### State Management

- Use `STATE_DIR` environment variable for all file paths
- Never hardcode paths like `/tmp/zend` or `./state`
- The `default_state_dir()` function resolves paths relative to the repo root

## Plan-Driven Development

Zend uses ExecPlans (executable plans) to track work. Plans live in `plans/` and `genesis/plans/`.

When working on a plan:

1. Read the plan file completely before starting
2. Update the `Progress` section as you complete tasks
3. Record discoveries in `Surprises & Discoveries`
4. Log decisions in `Decision Log`
5. At completion, write `Outcomes & Retrospective`

Plans are living documents. Keep them accurate as you work.

## Design System

The visual and interaction design is in `DESIGN.md`. Key points:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors:** Basalt (`#16181B`), Slate (`#23272D`), Moss (`#486A57`) for healthy state, Amber (`#D59B3D`) for caution
- **Motion:** Functional, not ornamental. Short fades, subtle slides.
- **Touch targets:** Minimum 44x44 logical pixels

When editing the HTML UI, follow the existing CSS variables and component patterns. Avoid generic crypto-dashboard aesthetics.

## Submitting Changes

### Branch Naming

```
docs/add-api-reference
feat/add-hermes-summary
fix/pairing-token-replay
```

### Before Committing

- [ ] All scripts run without errors
- [ ] Daemon health check passes
- [ ] Command center renders in browser
- [ ] No local hashing detected
- [ ] Progress section updated in relevant plan

### Commit Message Format

```
<type>: <short description>

<optional body with context>

Refs: <plan or issue number>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Troubleshooting

### Daemon Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Kill existing process
./scripts/bootstrap_home_miner.sh --stop

# Clean state and restart
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Client Not Paired

```bash
# Re-pair
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### CLI Can't Connect

```bash
# Check daemon is running
curl http://127.0.0.1:8080/health

# Set explicit URL
export ZEND_DAEMON_URL=http://127.0.0.1:8080
python3 services/home-miner-daemon/cli.py status
```

### State Corruption

```bash
# Full reset (destroys all pairing and principal data)
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```
