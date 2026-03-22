# Contributor Guide

**For:** Engineers joining the Zend project
**Covers:** Dev environment setup, running the system, understanding the codebase

---

## Development Environment

### Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.9+ | Daemon, CLI, scripts |
| git | any recent | Version control |
| curl | any recent | HTTP testing |
| bash | 4.0+ | Scripts |

No package manager dependencies beyond Python's standard library — the daemon
uses only `socketserver`, `json`, `urllib`, and the Python 3 standard library.

### Clone and Verify

```bash
git clone <zend-repo-url>
cd zend
```

Verify the directory structure:

```bash
ls -la
# apps/  docs/  genesis/  plans/  references/  scripts/  services/  specs/  state/  upstream/
```

## Fetching Upstream Dependencies

Zend pins reference client sources in `upstream/manifest.lock.json`. To fetch
them:

```bash
./scripts/fetch_upstreams.sh
```

This populates `third_party/` with the pinned repositories. The script is
idempotent — rerunning it resets each checkout to the pinned revision.

## Starting the Daemon

The daemon is the LAN-only home-miner control service. It exposes the gateway
API and manages the event spine.

### Default (development binding — localhost only)

```bash
./scripts/bootstrap_home_miner.sh
```

This:
1. Stops any existing daemon.
2. Starts the daemon on `127.0.0.1:8080`.
3. Waits for the health endpoint to respond.
4. Bootstraps the `PrincipalId` and creates a default pairing for `alice-phone`.

Output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrap complete
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
```

### LAN binding (operator deployment)

```bash
ZEND_BIND_HOST=192.168.1.100 ZEND_BIND_PORT=8080 ./scripts/bootstrap_home_miner.sh
```

Replace `192.168.1.100` with your machine's LAN IP. The daemon binds only to
that interface — it will not accept connections from outside the LAN.

### Stop the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check status only (no restart)

```bash
./scripts/bootstrap_home_miner.sh --status
```

## Using the CLI Directly

The `cli.py` module exposes all daemon operations. You can call it directly:

```bash
python3 services/home-miner-daemon/cli.py --help
```

```
usage: cli.py [-h] {status,health,bootstrap,pair,control,events} ...
```

### Subcommands

#### `health` — Daemon health check

```bash
python3 services/home-miner-daemon/cli.py health
```

Returns daemon health including temperature and uptime.

#### `status` — Miner status snapshot

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Requires `observe` or `control` capability for the named client.

#### `bootstrap` — Create principal + default pairing

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

#### `pair` — Pair a new client with capabilities

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Valid capabilities: `observe`, `control` (comma-separated).

#### `control` — Issue a miner control command

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

Requires `control` capability. `--mode` values: `paused`, `balanced`,
`performance`.

#### `events` — Read the event spine

```bash
# All events (newest first)
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 20
```

Valid `--kind` values: `all`, `pairing_requested`, `pairing_granted`,
`capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`,
`user_message`.

## Running the Gateway Client

The gateway client is a single-file web UI at `apps/zend-home-gateway/index.html`.
Open it in a browser after starting the daemon:

```bash
# Daemon must be running first
open apps/zend-home-gateway/index.html
# or point your browser to:
# file://<repo-root>/apps/zend-home-gateway/index.html
```

The client polls the daemon every 5 seconds for status updates.

## Verifying No Local Hashing

The `no_local_hashing_audit.sh` script inspects the gateway client process tree
and fails if it detects hashing libraries or worker threads:

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Expected output (success):

```
checked: client process tree
checked: local CPU worker count
result: no local hashing detected
```

Exit code 0 means pass. Non-zero means the audit detected something that
resembles on-device mining.

## Reading and Debugging the Event Spine

The spine lives at `state/event-spine.jsonl`. It is a JSONL file — one
JSON object per line, newest events last.

```bash
# View raw spine
cat state/event-spine.jsonl

# Pretty-print all events
python3 -c "
import json
with open('state/event-spine.jsonl') as f:
    for line in f:
        print(json.dumps(json.loads(line), indent=2))
        print('---')
"
```

## State Files

All runtime state lives under `state/` and is **not tracked in git**:

| File | Purpose |
|---|---|
| `state/principal.json` | The `PrincipalId` for this installation |
| `state/pairing-store.json` | All paired clients and their capabilities |
| `state/event-spine.jsonl` | Append-only event journal |
| `state/daemon.pid` | PID of the running daemon process |

If state becomes corrupt, stop the daemon and remove `state/` to reset:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

## Design System

All visual and interaction decisions must follow `DESIGN.md`. Required reading
before touching any UI code. Key constraints:

- **Fonts:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (numbers and identifiers)
- **Colors:** Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber
  `#D59B3D`, Signal Red `#B44C42` — no neon greens or exchange aesthetics
- **Mobile-first:** Single-column layout, bottom tab bar, 44×44 minimum touch
  targets
- **No AI slop:** No hero gradients, no three-column feature grids, no generic
  "No items found" empty states

## Spec and Plan Conventions

When writing or updating specs and plans, follow these documents:

- `SPEC.md` — How to write durable specs (decision, migration, capability)
- `PLANS.md` — How to write executable plans (ExecPlans)
- `plans/2026-03-19-build-zend-home-command-center.md` — Current active ExecPlan

Key rules:
- Specs are **living documents** for durable decisions; plans are **living
  documents** for implementation progress.
- Every term of art must be defined on first use.
- All file paths must be repository-relative.
- Do not outsource key decisions to external links.

## Adding a New CLI Command

1. Add the subparser in `services/home-miner-daemon/cli.py` under `main()`.
2. Implement the handler function (follow the `cmd_status` pattern).
3. Add the wrapper script in `scripts/` following the existing naming convention.
4. Document the command in this guide and in `docs/api-reference.md`.
5. Add an acceptance test transcript to `references/gateway-proof.md`.

## Adding a New Daemon Endpoint

1. Add the route in `services/home-miner-daemon/daemon.py` under `GatewayHandler`.
2. Update `docs/api-reference.md` with method, path, request/response shapes, and
   required capability.
3. Add an error case in `references/error-taxonomy.md` if it introduces a new
   failure mode.
