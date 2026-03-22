# Contributor Guide

Welcome to Zend. This guide covers everything you need to set up a development environment, understand the codebase, and contribute changes.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- A terminal
- A web browser

No pip install required. Zend uses only the Python standard library.

### Clone and Enter the Repo

```bash
git clone <repo-url>
cd zend
```

### Verify Python Version

```bash
python3 --version
# Should be 3.10 or later
```

### Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/
```

If no tests exist yet, this command runs without error. Tests are added alongside new features.

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates the principal identity
4. Emits a pairing bundle for `alice-phone`

The daemon runs in the background. Its PID is saved to `state/daemon.pid`.

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Pair a New Client

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Change Mining Mode

```bash
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

### Open the Command Center

```bash
open apps/zend-home-gateway/index.html
```

Or navigate to `file:///path/to/zend/apps/zend-home-gateway/index.html` in your browser.

## Project Structure

### `services/home-miner-daemon/`

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server and `MinerSimulator`. Exposes the REST API. |
| `cli.py` | CLI wrapper for pairing, status, and control commands. |
| `spine.py` | Append-only event journal. Source of truth for the inbox. |
| `store.py` | Principal identity and pairing records. |

### `apps/zend-home-gateway/`

| File | Purpose |
|------|---------|
| `index.html` | Mobile-shaped command center UI. Single-file, no build step. |

### `scripts/`

Shell wrappers around the CLI. These are the operator-facing interface. The CLI is the programmatic interface.

### `state/`

Local runtime data. Created on first bootstrap. Safe to delete for recovery.

### `specs/`

Durable capability specs. These define product boundaries, not implementation.

### `plans/`

Executable implementation plans (ExecPlans). Living documents with progress tracking.

## Making Changes

### 1. Understand the Plan

Check `plans/` for the current ExecPlan. It describes what needs to be built and why.

### 2. Make the Change

- Edit Python files in `services/`
- Edit the HTML in `apps/`
- Add or update shell scripts in `scripts/`

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/
```

### 4. Verify the Quickstart Still Works

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status --client test-device
```

### 5. Commit

```bash
git add <changed-files>
git commit -m "Describe the change"
```

## Coding Conventions

### Python Style

- Use the standard library only. No external dependencies.
- Follow PEP 8 with 4-space indentation.
- Use `typing` for function signatures.
- Use `dataclasses` for structured data.

### Naming

- Classes: `CamelCase` (e.g., `MinerSimulator`)
- Functions and variables: `snake_case` (e.g., `get_snapshot`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BIND_PORT`)
- Private members: leading underscore (e.g., `_lock`)

### Error Handling

- Use named error classes defined in `references/error-taxonomy.md`.
- Return `{"success": false, "error": "error_name"}` for expected failures.
- Let exceptions propagate for unexpected failures.

### File Organization

- One module per file unless tightly coupled.
- Keep `daemon.py` focused on HTTP serving and miner simulation.
- Keep `spine.py` focused on event journal operations.
- Keep `store.py` focused on principal and pairing data.

## Plan-Driven Development

ExecPlans are living documents. When you make a decision while coding:

1. Update the `Decision Log` in the relevant ExecPlan.
2. Update the `Progress` checklist.
3. Add a `Surprises & Discoveries` entry if something unexpected came up.

The goal is that any future contributor can read the ExecPlan and understand not just what was built, but why each decision was made.

## Design System

The visual and interaction system is defined in `DESIGN.md` at the repo root. Key principles:

- **Calm, domestic feel**: Like a household control panel, not a crypto exchange.
- **Typography**: Space Grotesk for headings, IBM Plex Sans for body, IBM Plex Mono for data.
- **Mobile-first**: The default viewport is single-column with a bottom tab bar.
- **No AI slop**: No generic gradients, hero slogans, or dashboard widget grids.

When editing the HTML frontend, follow the design system. When in doubt, match the existing patterns in `index.html`.

## Submitting Changes

### Branch Naming

```
documentation/add-api-reference
feature/add-hermes-adapter
fix/pairing-token-expiry
```

### Commit Messages

Use imperative mood:

```
Add API reference documentation
Fix stale snapshot warning threshold
Update design system color palette
```

### Pull Request

Include:
1. What changed and why
2. How to verify the change works
3. Any new decisions or tradeoffs

## Architecture Decisions to Know

- **LAN-only in milestone 1**: The daemon binds to `127.0.0.1` by default. This is intentional.
- **Stdlib only**: No pip dependencies. This limits functionality but keeps the codebase auditable.
- **JSONL event spine**: Events are append-only lines in `state/event-spine.jsonl`. Not a database.
- **Simulator, not real miner**: `MinerSimulator` proves the API contract. A real miner backend is a later milestone.
- **Single HTML file**: The command center is one file with no build step. This keeps it simple and portable.

## Common Tasks

### Reset Local State

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Check Daemon Health

```bash
curl http://127.0.0.1:8080/health
```

### View Event Spine

```bash
cat state/event-spine.jsonl
```

### Pair with Different Capabilities

```bash
# Observe only (cannot control mining)
./scripts/pair_gateway_client.sh --client my-tablet --capabilities observe

# Full control
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Check What Devices Are Paired

```bash
python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted
```
