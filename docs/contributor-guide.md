# Contributor Guide

This guide helps new contributors set up a local development environment,
understand the codebase, run tests, and follow the project's conventions.

---

## Development Environment Setup

### System Requirements

- Python 3.10 or later
- Git
- Bash or a Bash-compatible shell (Linux, macOS, WSL2)
- a web browser for the gateway client UI
- optionally, `python3-venv` for isolated virtual environments

### 1 — Clone the Repository

```bash
git clone <repository-url> zend
cd zend
```

### 2 — Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3 — Install Python Dependencies

```bash
pip install -r requirements.txt   # if a requirements file exists
# Otherwise the daemon uses only the Python standard library.
```

The home-miner daemon is intentionally written with no external dependencies
beyond the standard library so it can run on a Raspberry Pi or minimal NAS
environment.

### 4 — Verify the Daemon Starts

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
bootstrap started
pairing_token=<TOKEN>
principal_id=<UUID>
daemon listening on 127.0.0.1:8080
```

Press `Ctrl+C` to stop the daemon, or run it in the background with `&`.

### 5 — Run the Gateway Client

Open `apps/zend-home-gateway/index.html` directly in a browser, or serve it:

```bash
cd apps/zend-home-gateway
python3 -m http.server 9000
# then open http://localhost:9000
```

### 6 — Run the Smoke Tests

```bash
./scripts/pair_gateway_client.sh --client test-device
./scripts/read_miner_status.sh --client test-device
./scripts/set_mining_mode.sh --client test-device --mode balanced
./scripts/hermes_summary_smoke.sh --client test-device
./scripts/no_local_hashing_audit.sh --client test-device
```

All five commands should complete without error.

---

## Repository Conventions

### Specs vs Plans

- **Specs** (`specs/`, `SPEC.md`) capture durable decisions, boundaries, and
  invariants. They are not living checklists.
- **Plans** (`plans/`, `PLANS.md`) capture the current implementation slice and
  stay live while work proceeds.

When in doubt: spec for architectural or migration work, plan for bounded
feature delivery.

### Writing Rules

1. Every document must be self-contained. Do not rely on chat history or adjacent
   repositories.
2. Define terms of art immediately. Do not assume the reader knows phrases like
   "control plane", "lane", or "PrincipalId".
3. Describe user-visible outcomes, not just file changes.
4. Prefer prose over giant taxonomies.
5. All new stable surfaces must name their first concrete consumer.

### Code Conventions

- Python: follow PEP 8. The daemon intentionally uses only the standard library.
- Shell scripts: use `set -euo pipefail` at the top. Prefer POSIX-compatible
  constructs.
- HTML/CSS/JS: the gateway client uses vanilla JS with no build step.
- Font faces are defined in `DESIGN.md`. Do not add Inter, Roboto, or Arial.

### Git Conventions

- Commit message format: `type: short description`
- Types: `spec`, `plan`, `impl`, `docs`, `fix`, `refactor`
- Keep commits atomic. One commit = one logical change.
- Do not commit secrets, credentials, or local state.

---

## Testing

### Unit Tests

The daemon has basic unit tests. Run them with:

```bash
cd services/home-miner-daemon
python3 -m pytest           # if pytest is installed
python3 -m unittest        # standard library only
```

### Smoke Tests

The `scripts/` directory contains end-to-end smoke tests. Run them in order:

```bash
./scripts/bootstrap_home_miner.sh &
DAEMON_PID=$!

./scripts/pair_gateway_client.sh --client smoke-test
./scripts/read_miner_status.sh --client smoke-test
./scripts/set_mining_mode.sh --client smoke-test --mode performance
./scripts/hermes_summary_smoke.sh --client smoke-test
./scripts/no_local_hashing_audit.sh --client smoke-test

kill $DAEMON_PID
```

### Adding Tests

When adding a new script or endpoint, add a corresponding smoke test in the
`scripts/` directory. Tests should:

- use `--client smoke-test` to avoid polluting real device names
- clean up after themselves (stop daemons, remove temp state)
- exit non-zero on failure with a named error code from `references/error-taxonomy.md`

---

## Architecture Decisions

When making an architectural decision:

1. Check if a spec already exists for this area (`specs/`).
2. If changing a durable boundary, write or update a spec first.
3. Record the decision in the relevant ExecPlan's `Decision Log`.
4. Update `references/` contracts if the change affects them.

Key contracts to maintain:

- `references/inbox-contract.md` — `PrincipalId` and pairing record
- `references/event-spine.md` — event kinds and routing
- `references/error-taxonomy.md` — named error classes
- `references/observability.md` — structured log events and metrics

---

## Troubleshooting

### Daemon port already in use

```
Error: DAEMON_PORT_IN_USE
```

Another process is using port 8080. Find and stop it:

```bash
lsof -ti:8080 | xargs kill -9
# then re-run bootstrap
./scripts/bootstrap_home_miner.sh
```

### Pairing token expired

```
Error: PAIRING_TOKEN_EXPIRED
```

Re-run bootstrap to get a fresh token:

```bash
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone
```

### Client cannot reach daemon

The daemon binds to `127.0.0.1:8080` by default (LAN-only milestone). Ensure
the client is on the same host, or for LAN testing, set `ZEND_HOST` to the
daemon machine's LAN IP before bootstrapping:

```bash
ZEND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

### State corruption

To reset all local state:

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone
```

---

## Design System Quick Reference

See `DESIGN.md` for the full system. Key points for contributors:

- **Fonts:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (status values and identifiers)
- **Colors:** Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`, Moss
  `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Touch targets:** minimum `44×44` logical pixels
- **Motion:** functional only; respect `prefers-reduced-motion`

Banned patterns (unless explicitly justified in a design review):

- hero sections with slogan + CTA over a generic gradient
- three-column feature grids
- glassmorphism control panels
- generic "clean modern dashboard" widgets
- "No items found" empty states without a next action
