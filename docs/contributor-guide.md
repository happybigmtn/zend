# Contributor Guide

This guide gets you from a fresh clone to a running test suite without tribal knowledge. Follow it in order.

---

## 1. Dev Environment Setup

### Prerequisites

- Python 3.10 or newer
- Git
- A terminal

No virtual environments are required for the daemon itself (stdlib only), but a virtual environment is recommended for running tests.

```bash
# Clone the repo
git clone <repo-url> && cd zend

# Create a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install pytest for running tests
pip install pytest
```

Verify Python version:

```bash
python3 --version
# Expected: Python 3.10.x or newer
```

### Directory Structure

```
apps/                          # Gateway client UI (single HTML file)
services/home-miner-daemon/   # Python daemon (stdlib only)
  daemon.py                   # HTTP server + MinerSimulator
  cli.py                      # CLI: status, control, pair, events
  spine.py                   # Append-only event journal (JSONL)
  store.py                   # Principal + pairing record store
scripts/                      # Shell scripts for operators and proofs
references/                    # Contracts, storyboards, checklists
upstream/                      # Pinned upstream manifest
state/                         # Runtime state (gitignored)
```

The daemon does not install as a package. You run it directly with `python3 daemon.py` from the `services/home-miner-daemon/` directory.

---

## 2. Running Locally

### Start the Daemon

```bash
cd services/home-miner-daemon/
python3 daemon.py
# Output: "Zend Home Miner Daemon starting on 127.0.0.1:8080"
#         "Press Ctrl+C to stop"
```

The daemon binds to `127.0.0.1:8080` by default (LAN-only in milestone 1). You can change the binding:

```bash
ZEND_BIND_HOST=0.0.0.0 ZEND_BIND_PORT=9000 python3 daemon.py
```

The daemon state lives in `state/` (gitignored). To start fresh:

```bash
rm -rf state/
mkdir state
python3 daemon.py
```

### Bootstrap Principal Identity

```bash
python3 cli.py bootstrap --device alice-phone
# Returns: principal_id, device_name, pairing_id, capabilities
```

This creates:
- `state/principal.json` — the `PrincipalId` for this installation
- `state/pairing-store.json` — the pairing record for `alice-phone`
- `state/event-spine.jsonl` — first entry (pairing granted)

### Read Miner Status

```bash
python3 cli.py status --client alice-phone
```

Requires the client to have `observe` or `control` capability. If the client has no pairing record, this returns an authorization error.

### Control the Miner

```bash
# Change mode
python3 cli.py control --client alice-phone --action set_mode --mode balanced

# Start mining
python3 cli.py control --client alice-phone --action start

# Stop mining
python3 cli.py control --client alice-phone --action stop
```

Requires the client to have `control` capability. Returns `{"error": "unauthorized"}` for observe-only clients.

### View Events

```bash
python3 cli.py events --client alice-phone --kind all --limit 20
```

Filters:

```bash
--kind pairing_requested
--kind pairing_granted
--kind control_receipt
--kind miner_alert
--kind hermes_summary
--kind user_message
```

### Use the Command Center UI

Open `apps/zend-home-gateway/index.html` in a browser. It polls `http://127.0.0.1:8080/status` every 5 seconds and displays the miner state. No build step is required.

For mobile preview, use browser DevTools device emulation at 375×812 (iPhone-sized).

---

## 3. Project Structure

### Why These Directories

| Directory | Purpose |
|---|---|
| `services/home-miner-daemon/` | The daemon. Contains all Python code. Stdlib only. |
| `apps/zend-home-gateway/` | The gateway client. Single HTML file. No build step. |
| `scripts/` | Shell scripts wrapping the CLI for operators and automated tests. |
| `state/` | Runtime state. PrincipalId, pairing records, event spine. Gitignored. |
| `references/` | Contracts and design artifacts that guide implementation. |
| `upstream/` | Pinned manifest for external dependencies (mobile clients, lightwalletd). |
| `specs/` | Durable specs defining what the system must do and why. |
| `plans/` | Executable plans for implementation slices. |

### Key Data Files

- **`state/principal.json`** — One `PrincipalId` per installation. Created by `bootstrap`. Stable across restarts.
- **`state/pairing-store.json`** — Maps device names to `PrincipalId` and capability sets. Written by `pair`.
- **`state/event-spine.jsonl`** — Append-only JSONL journal. One JSON object per line. Source of truth for the inbox.

### Key Python Modules

| Module | Purpose |
|---|---|
| `daemon.py` | `MinerSimulator` (status/start/stop/set_mode), `GatewayHandler` (HTTP API), `ThreadedHTTPServer` |
| `cli.py` | Command-line interface with subcommands: `status`, `health`, `bootstrap`, `pair`, `control`, `events` |
| `spine.py` | Append-only event journal. Functions: `append_event`, `get_events`, `append_pairing_requested`, `append_pairing_granted`, `append_control_receipt`, `append_miner_alert`, `append_hermes_summary` |
| `store.py` | Principal and pairing store. Functions: `load_or_create_principal`, `pair_client`, `get_pairing_by_device`, `has_capability`, `list_devices` |

---

## 4. Making Changes

### Edit Code

1. Make your changes to the appropriate file in `services/home-miner-daemon/` or `apps/zend-home-gateway/`.
2. Restart the daemon if it is running.
3. Run the relevant tests.
4. Verify with a manual test if the change is user-visible.

### Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

For a single test file:

```bash
python3 -m pytest services/home-miner-daemon/test_store.py -v
```

The test suite currently covers the daemon, CLI, spine, and store modules.

### Verify a Change End-to-End

```bash
# 1. Start fresh
rm -rf state/
./scripts/bootstrap_home_miner.sh

# 2. Check health
python3 services/home-miner-daemon/cli.py health

# 3. Pair a client
./scripts/pair_gateway_client.sh --client test-phone --capabilities observe,control

# 4. Read status
./scripts/read_miner_status.sh --client test-phone

# 5. Set mode
./scripts/set_mining_mode.sh --client test-phone --mode balanced

# 6. View events
python3 services/home-miner-daemon/cli.py events --client test-phone
```

All six steps should complete without error. If a step fails, the output tells you why.

---

## 5. Coding Conventions

### Python Style

- **Stdlib only.** Do not add external dependencies to `services/home-miner-daemon/`.
- Use `from __future__ import annotations` for cleaner type hints.
- Docstrings on all public functions.
- Error messages are for humans: use plain language, not codes.

### Naming

| Thing | Convention | Example |
|---|---|---|
| Python module | `lowercase_with_underscores.py` | `spine.py` |
| Class | `CapWords` | `MinerSimulator`, `GatewayPairing` |
| Function | `lowercase_with_underscores` | `append_event`, `has_capability` |
| Constant | `UPPERCASE_WITH_UNDERSCORES` | `BIND_HOST`, `STATE_DIR` |
| Enum member | `UPPERCASE` | `MinerMode.PAUSED` |

### Error Handling

The daemon returns JSON error responses for all failure modes. Use named error fields, not raw HTTP status codes alone:

```json
{"error": "unauthorized", "message": "This device lacks 'control' capability"}
{"error": "daemon_unavailable", "details": "Connection refused"}
```

### CLI Patterns

All CLI subcommands follow this pattern:

```bash
python3 cli.py <subcommand> [options]
```

- `--client <name>` — identifies the paired device for authorization checks
- `--capabilities` — comma-separated list (`observe,control`)
- `--kind` — event kind filter for the events subcommand
- `--limit` — max number of events to return

Exit codes: `0` for success, `1` for error. The CLI never crashes; it prints a JSON error and exits cleanly.

---

## 6. Plan-Driven Development

This repo uses two document types:

**Specs** (in `specs/`) define durable behavior. They are not living documents. They capture decisions that should not change without a new spec.

**ExecPlans** (in `plans/`) are living documents that guide implementation. They must be followed to the letter. Key rules from `PLANS.md`:

- Every ExecPlan must be fully self-contained. A novice with only the ExecPlan file and the working tree must be able to implement the feature.
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date.
- Record every decision in the `Decision Log`.
- Validate as you go. Include test commands and expected outputs.

---

## 7. Design System

The Zend design system is defined in `DESIGN.md`. When working on the gateway UI (`apps/zend-home-gateway/index.html`), follow these rules:

### Typography
- Headings: `Space Grotesk` 600–700
- Body: `IBM Plex Sans` 400–500
- Operational data: `IBM Plex Mono` 500

### Color System
| Name | Hex | Use |
|---|---|---|
| Basalt | `#16181B` | Primary dark surface |
| Slate | `#23272D` | Elevated surfaces |
| Mist | `#EEF1F4` | Light backgrounds |
| Moss | `#486A57` | Healthy/stable state |
| Amber | `#D59B3D` | Caution/pending |
| Signal Red | `#B44C42` | Destructive/degraded |
| Ice | `#B8D7E8` | Informational highlight |

### Component Vocabulary
- **Status Hero** — large top block on Home showing miner state, mode, freshness
- **Mode Switcher** — segmented control for paused/balanced/performance
- **Receipt Card** — concise event entry with origin, time, outcome
- **Permission Pill** — observe or control chip
- **Trust Sheet** — modal for pairing and capability grants
- **Alert Banner** — short, high-signal warning

### AI Slop Guardrails
Avoid:
- Hero sections with gradients and marketing slogans
- Three-column feature grids
- Generic icon farms
- "No items found" empty states with no next action

Include:
- Warm empty states with a primary next action
- Loading skeletons
- Explicit error messages with recovery hints

### Accessibility
- Touch targets: minimum 44×44 logical pixels
- Body text: minimum 16px equivalent
- WCAG AA contrast for all text and controls
- `prefers-reduced-motion` fallback for every animation
- Screen-reader landmarks for Home, Inbox, Agent, Device

---

## 8. Submitting Changes

### Branch Naming

```
docs/description            # Documentation changes
feat/description           # New features
fix/description            # Bug fixes
refactor/description       # Code restructuring without behavior change
```

### Before Submitting

1. Run the full test suite: `python3 -m pytest services/home-miner-daemon/ -v`
2. Verify the end-to-end proof in §4 completes without errors
3. Check that new code follows the conventions in §5
4. Verify new UI components follow the design system in §7

### Commit Messages

```
type(scope): short description

Longer explanation if needed. Reference the ExecPlan or spec
by name if applicable.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
