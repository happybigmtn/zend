# Contributor Guide

Welcome to Zend! This guide helps you set up your development environment and
understand how to contribute to the project.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal with bash compatibility

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

Zend uses only the Python standard library for runtime, but you'll need pytest
for testing:

```bash
pip install pytest
```

### 4. Verify Installation

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

All tests should pass.

## Running Locally

### Start the Daemon

The daemon exposes the home-miner gateway API. Start it with the bootstrap script:

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Starts the daemon on `127.0.0.1:8080`
2. Creates a principal identity in `state/`
3. Bootstraps a default client pairing for `alice-phone`

### Check Daemon Health

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
```

Expected output:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

### Control the Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Set mode to balanced
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop
```

### View Events

```bash
# List all events
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### Open the Command Center

Navigate to `apps/zend-home-gateway/index.html` in your browser. The command
center connects to `http://127.0.0.1:8080` and displays miner status, mode
controls, and recent receipts.

## Project Structure

### `services/home-miner-daemon/`

The backend service. This is where you'll spend most of your time.

| File | Purpose |
|---|---|
| `daemon.py` | HTTP server and miner simulator. Handles `/health`, `/status`, `/miner/*` endpoints. |
| `cli.py` | Command-line interface. Pairing, status, control, and event queries. |
| `spine.py` | Append-only JSONL event journal. Source of truth for receipts and events. |
| `store.py` | Principal and pairing records. Manages `PrincipalId` and `GatewayCapability` sets. |

### `apps/zend-home-gateway/`

The HTML command-center client. A single-file SPA that connects to the daemon.

### `scripts/`

Operator scripts for common tasks:

| Script | Purpose |
|---|---|
| `bootstrap_home_miner.sh` | Start daemon and bootstrap principal |
| `pair_gateway_client.sh` | Pair a new device |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Change mining mode |
| `no_local_hashing_audit.sh` | Prove no on-device mining |

### `specs/`

Product specifications. These define durable behavior and boundaries.

### `plans/`

Execution plans. These define implementation slices and track progress.

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

Branch naming convention: `feature/`, `fix/`, `docs/`, `refactor/`

### 2. Edit Code

Follow the coding conventions below.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify Your Changes

```bash
# Restart the daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh

# Test your changes
curl http://127.0.0.1:8080/health
python3 services/home-miner-daemon/cli.py status
```

### 5. Commit

```bash
git add -A
git commit -m "feat: add my new feature"
```

## Coding Conventions

### Python Style

- Use the Python standard library only (no external dependencies)
- Follow PEP 8 for code style
- Use type hints where they aid readability
- Keep functions focused and small (under 50 lines)

### Naming

| Thing | Convention | Example |
|---|---|---|
| Modules | lowercase, snake_case | `home_miner_daemon` |
| Classes | CamelCase | `MinerSimulator` |
| Functions | lowercase, snake_case | `get_pairing_by_device` |
| Constants | UPPERCASE_SNAKE | `BIND_PORT` |
| Private members | prefix `_` | `_status` |

### Error Handling

- Use explicit error types (ValueError, KeyError, etc.)
- Never swallow exceptions silently
- Return error dicts from functions that callers can handle
- Log errors at the appropriate level

Example:

```python
def set_mode(self, mode: str) -> dict:
    try:
        new_mode = MinerMode(mode)
    except ValueError:
        return {"success": False, "error": "invalid_mode"}
    
    self._mode = new_mode
    return {"success": True, "mode": self._mode}
```

### Module Organization

Each module should have:
1. A docstring explaining its purpose
2. Public functions/classes with docstrings
3. Private helpers prefixed with `_`

## Plan-Driven Development

Zend uses ExecPlans to track implementation work. Read `PLANS.md` for the
full specification.

### ExecPlan Structure

- **Purpose/Big Picture**: Why this work matters
- **Progress**: Checkbox list of completed and remaining tasks
- **Surprises & Discoveries**: Unexpected findings during implementation
- **Decision Log**: Key decisions and rationale
- **Context and Orientation**: What exists before this work
- **Plan of Work**: Narrative description of changes
- **Concrete Steps**: Exact commands to run
- **Validation and Acceptance**: How to verify the work

### Updating ExecPlans

When you complete a task:
1. Update the Progress checkbox with timestamp
2. Add any discoveries to Surprises & Discoveries
3. Record key decisions in Decision Log

## Submitting Changes

### Pull Request Template

```markdown
## Summary

Brief description of the change.

## Testing

How did you test this change?

## Checklist

- [ ] Tests pass
- [ ] Code follows conventions
- [ ] Documentation updated (if applicable)
```

### CI Checks

Before submitting:
1. All tests pass
2. No lint errors (flake8 if configured)
3. Documentation is accurate

## Getting Help

- Read the [Architecture](architecture.md) document
- Check the [API Reference](api-reference.md)
- Review the [Product Spec](../specs/2026-03-19-zend-product-spec.md)
