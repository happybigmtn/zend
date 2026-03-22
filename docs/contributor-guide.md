# Contributor Guide

This guide helps you set up a development environment and understand the Zend codebase.

## Prerequisites

- Python 3.10 or higher
- Git
- A terminal

No external dependencies are required. The project uses only Python's standard library.

## Dev Environment Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### 3. Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

> **Note:** No test files exist yet in milestone 1. The command above returns
> zero tests until the test suite is added. Track this in the plan for the
> testing lane.

## Running Locally

### Start the Daemon

```bash
# Option 1: Using the bootstrap script (recommended)
./scripts/bootstrap_home_miner.sh

# Option 2: Start daemon only
./scripts/bootstrap_home_miner.sh --daemon

# Option 3: Start daemon manually
cd services/home-miner-daemon
python3 daemon.py
```

The daemon starts on `127.0.0.1:8080` by default.

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

### Get Miner Status

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
  "uptime_seconds": 0,
  "freshness": "2026-03-22T18:30:00.000000+00:00"
}
```

### Control the Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop
```

### Open the Command Center

```bash
# Option 1: Open directly in browser
open apps/zend-home-gateway/index.html

# Option 2: Serve via HTTP (required for some browsers)
cd apps/zend-home-gateway
python3 -m http.server 8081
# Then open http://localhost:8081/index.html
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
zend/
├── apps/zend-home-gateway/
│   └── index.html          # Mobile command center UI
├── services/home-miner-daemon/
│   ├── daemon.py           # HTTP API server
│   ├── cli.py              # CLI for pairing, status, control
│   ├── spine.py            # Append-only event journal
│   └── store.py            # Principal and pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh  # Daemon bootstrap
│   └── *.sh                    # Operational scripts
├── docs/
│   ├── architecture.md     # System design
│   ├── api-reference.md   # API documentation
│   ├── contributor-guide.md  # This file
│   └── operator-quickstart.md # Home deployment
├── specs/                 # Capability and decision specs
├── plans/                 # Execution plans
├── references/            # Reference contracts
├── state/                 # Runtime state (created at bootstrap)
├── outputs/               # Build artifacts
└── README.md              # Project overview
```

## Code Conventions

### Python Style

- Use Python standard library only (no external dependencies)
- Follow PEP 8 conventions
- Use type hints where beneficial
- Keep functions focused and small

### Naming

- Modules: lowercase with underscores (`spine.py`)
- Classes: CamelCase (`MinerSimulator`)
- Functions: lowercase with underscores (`get_events`)
- Constants: UPPERCASE_WITH_UNDERSCORES (`STATE_DIR`)

### Error Handling

- Return error dictionaries from functions
- Include error codes (`"error": "already_running"`)
- Log errors to stderr for debugging

### Testing

- Place tests in `services/home-miner-daemon/test_*.py` (convention, not yet enforced)
- Use `pytest` for running tests
- Test both success and failure paths

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test file (once added)
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Plans live in `plans/` and follow this format:

1. **Progress**: Checklist of tasks with timestamps
2. **Surprises & Discoveries**: Unexpected findings during implementation
3. **Decision Log**: Key decisions and rationale
4. **Outcomes & Retrospective**: Summary at completion

When working on a plan:
- Keep progress updated as you complete tasks
- Record any discoveries that changed your approach
- Update the plan file before committing

## Design System

See `DESIGN.md` for the visual design system:

- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- Color palette: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- Mobile-first design with bottom navigation
- Calm, domestic, trustworthy aesthetic

## Submitting Changes

### Branch Naming

```
feature/description
bugfix/description
docs/description
```

### Commit Messages

```
type: brief description

Detailed explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`

### Pull Request Template

```markdown
## Summary
Brief description of changes.

## Testing
How changes were tested.

## Checklist
- [ ] Tests pass
- [ ] Documentation updated (if applicable)
- [ ] Code follows conventions
```

## Troubleshooting

### Daemon won't start

```bash
# Check if already running
ps aux | grep daemon.py

# Kill existing process
./scripts/bootstrap_home_miner.sh --stop

# Check port availability
lsof -i :8080
```

### State corruption

```bash
# Backup and reset state
mv state state.backup
./scripts/bootstrap_home_miner.sh
```

### CLI can't connect

```bash
# Verify daemon is running
curl http://127.0.0.1:8080/health

# Check ZEND_DAEMON_URL
echo $ZEND_DAEMON_URL
```

## Getting Help

- Architecture: See `docs/architecture.md`
- API: See `docs/api-reference.md`
- Design: See `DESIGN.md`
- Specs: See `specs/`
- Plans: See `plans/`
