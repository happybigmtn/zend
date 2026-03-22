# Contributor Guide

This guide covers everything you need to start developing Zend. By the end, you will have a working local environment and understand how to make and verify changes.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal

No pip install needed. The daemon uses only Python standard library.

### Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

## Project Structure

Understanding the codebase structure helps you navigate and make targeted changes.

### Top-Level Directories

| Directory | Purpose |
|-----------|---------|
| `apps/` | User-facing clients (gateway UI) |
| `services/` | Backend services (daemon, simulators) |
| `scripts/` | Operator and developer scripts |
| `docs/` | Documentation files |
| `references/` | Architecture contracts and design notes |
| `specs/` | Product and capability specifications |
| `plans/` | Implementation plans (ExecPlans) |
| `state/` | Local runtime data (gitignored) |

### Key Files

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/daemon.py` | HTTP API server and miner simulator |
| `services/home-miner-daemon/cli.py` | CLI tool for status and control |
| `services/home-miner-daemon/spine.py` | Append-only event journal |
| `services/home-miner-daemon/store.py` | Principal and pairing records |
| `apps/zend-home-gateway/index.html` | Mobile command center UI |

## Running Locally

### 1. Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
- Stops any existing daemon
- Creates the `state/` directory
- Starts the daemon on `127.0.0.1:8080`
- Bootstraps a principal identity
- Creates a default client pairing for `alice-phone`

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
```

### 2. Open the Command Center

```bash
# Option A: Open in browser directly
open apps/zend-home-gateway/index.html

# Option B: Serve via Python's http.server (for network access)
cd apps/zend-home-gateway && python3 -m http.server 8081
```

The command center connects to `http://127.0.0.1:8080` by default.

### 3. Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Expected output:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:02:00+00:00"
}
```

### 4. Control Mining

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Set mode to balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### 5. Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## CLI Reference

The CLI is the primary tool for scripting and automation.

### Commands

| Command | Description |
|---------|-------------|
| `cli.py status --client <name>` | Get miner status |
| `cli.py health` | Get daemon health |
| `cli.py bootstrap --device <name>` | Bootstrap principal and pair device |
| `cli.py pair --device <name> --capabilities <list>` | Pair a new device |
| `cli.py control --client <name> --action <action> [--mode <mode>]` | Control miner |
| `cli.py events --client <name> [--kind <kind>] [--limit <n>]` | List events |

### Capabilities

When pairing, specify capabilities as a comma-separated list:

```bash
# Observe-only
python3 cli.py pair --device my-tablet --capabilities observe

# Full control
python3 cli.py pair --device my-phone --capabilities observe,control
```

## Making Changes

### 1. Understand the Architecture

Read [docs/architecture.md](architecture.md) for system design and module explanations.

### 2. Find the Right File

- **UI changes**: `apps/zend-home-gateway/index.html`
- **API changes**: `services/home-miner-daemon/daemon.py`
- **CLI changes**: `services/home-miner-daemon/cli.py`
- **Data model changes**: `services/home-miner-daemon/store.py` or `spine.py`

### 3. Make Your Change

Edit the relevant file. Keep changes focused and testable.

### 4. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 5. Verify the Quickstart Works

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Restart and verify
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

## Coding Conventions

### Python Style

- Use Python standard library only (no `pip install`)
- Follow PEP 8 with 4-space indentation
- Use type hints for function signatures
- Document modules and classes with docstrings

### Naming

| Element | Convention | Example |
|---------|------------|---------|
| Modules | lowercase | `daemon.py` |
| Classes | CamelCase | `MinerSimulator` |
| Functions | snake_case | `get_snapshot` |
| Constants | UPPER_SNAKE | `BIND_PORT` |
| Private methods | _leading_underscore | `_send_json` |

### Error Handling

Use named errors for user-facing failures:

```python
if not has_capability(device, 'control'):
    return {"error": "unauthorized", "message": "This device lacks 'control' capability"}
```

See [references/error-taxonomy.md](../references/error-taxonomy.md) for the full list.

### State Management

- Use the `store` module for principal and pairing data
- Use the `spine` module for event appending
- Do not create separate feature-specific stores

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Plans live in `plans/` and follow the format in `PLANS.md`.

When working on a plan:
1. Read the plan from `plans/<plan-name>.md`
2. Check off completed items in the `Progress` section
3. Update `Surprises & Discoveries` with what you learned
4. Add decisions to `Decision Log`
5. Keep the plan current as you work

## Design System

Zend follows the design system in `DESIGN.md`. Key points:

- **Fonts**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- **Colors**: Basalt/Slate (dark surfaces), Moss (healthy), Amber (caution), Signal Red (error)
- **Motion**: Short fades and position shifts; respect `prefers-reduced-motion`
- **Touch targets**: Minimum 44x44 logical pixels

When adding UI components, follow the existing patterns in `apps/zend-home-gateway/index.html`.

## Submitting Changes

### Branch Naming

```
feature/<short-description>
fix/<issue-or-bug>
docs/<what-it-documents>
```

### Before Submitting

- [ ] Tests pass: `python3 -m pytest services/home-miner-daemon/ -v`
- [ ] Quickstart works: daemon starts, status returns OK
- [ ] No external dependencies added
- [ ] Documentation updated if behavior changed

### Commit Messages

Use clear, imperative commit messages:

```
Add set_mode endpoint to daemon API

Implement POST /miner/set_mode with mode validation.
Update CLI to support --action set_mode --mode <mode>.
Add control receipt to event spine.
```

## Troubleshooting

### Daemon Won't Start

```bash
# Check if something is using port 8080
lsof -i :8080

# Kill any existing process
./scripts/bootstrap_home_miner.sh --stop

# Try again
./scripts/bootstrap_home_miner.sh
```

### Permission Denied on Scripts

```bash
chmod +x scripts/*.sh
```

### State Corruption

If state becomes corrupted, reset:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### CLI Can't Connect to Daemon

```bash
# Check daemon is running
./scripts/bootstrap_home_miner.sh --status

# Check environment variable
echo $ZEND_DAEMON_URL
# Should be: http://127.0.0.1:8080
```

## Getting Help

- **Architecture**: [docs/architecture.md](architecture.md)
- **API Reference**: [docs/api-reference.md](api-reference.md)
- **Product Spec**: [specs/2026-03-19-zend-product-spec.md](../specs/2026-03-19-zend-product-spec.md)
- **Design System**: [DESIGN.md](../DESIGN.md)
