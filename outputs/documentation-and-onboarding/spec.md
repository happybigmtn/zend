# Spec: Documentation & Onboarding

## Purpose / User-Visible Outcome

A new contributor can go from `git clone` to a working Zend CLI flow in under
10 minutes following the repository documentation. The operator guide documents
home-hardware daemon deployment, but phone-browser control is not yet a
verified outcome because the daemon does not serve the UI and the checked-in
HTML hits browser origin restrictions. The API and architecture are documented
with the implemented surfaces clearly separated from target contracts.

## What Was Done

### 1. README.md (rewrite)

Rewrote `README.md` as a gateway, not a manual. Under 200 lines. Includes:

- One-paragraph description of Zend
- Five-command quickstart: clone → bootstrap → open HTML → status → control
- ASCII architecture diagram showing phone → HTML → daemon → state files
- Directory structure with per-directory descriptions
- Prerequisites (Python 3.10+, bash, curl, no pip needed)
- Test command (`python3 -m pytest services/home-miner-daemon/ -v`) plus a note
  that the repo currently collects zero tests
- Links to all four docs files, `DESIGN.md`, specs, and plans

### 2. docs/contributor-guide.md

Covers:

- Dev environment setup (Python 3.10+, clone, verify)
- Running the quickstart with expected output
- Inspecting the HTML command center shell and calling out the current browser
  origin limitation
- Project structure: all modules (`daemon.py`, `cli.py`, `store.py`, `spine.py`),
  scripts, references, and their responsibilities
- Making changes: editing, running tests, verifying quickstart
- Coding conventions: stdlib-only, error handling, naming, thread safety, JSON,
  file paths
- Plan-driven development: how ExecPlans work and how to update them
- Design system: pointer to `DESIGN.md` with key requirements
- Submitting changes: branch naming, clean daemon state
- Troubleshooting: port conflicts, daemon crashes, connection failures, auth errors

### 3. docs/operator-quickstart.md

Covers:

- Hardware requirements (any Linux box, Python 3.10+)
- Installation: clone, Python version check
- Bind address selection with `ZEND_BIND_HOST` and `ZEND_BIND_PORT`
- First boot: bootstrap script with expected output
- Verifying daemon (curl health from same machine and phone)
- Explicitly documenting that phone-browser command-center access is not yet a
  verified path in the current slice
- Pairing a phone with observe and control capability
- Daily operations: status, mode change, start/stop, viewing events, event spine
- Running as a systemd service (full unit file)
- Security: LAN-only model, milestone 1 limitations, TLS path forward
- Recovery: state wipe and re-bootstrap procedure
- Environment variables reference table
- Troubleshooting: firewall, HTML connectivity, bootstrap hangs

### 4. docs/api-reference.md

Documents every daemon endpoint:

- `GET /health` — daemon health, no auth required
- `GET /status` — miner snapshot with status/mode/hashrate/temperature/freshness
- `GET /spine/events` — append-only event journal (CLI equivalent available;
  HTTP endpoint noted as not yet implemented in daemon)
- `GET /metrics` — operational metrics (not yet implemented; CLI equivalent documented)
- `POST /miner/start` — start the miner
- `POST /miner/stop` — stop the miner
- `POST /miner/set_mode` — change mode (paused/balanced/performance)
- `POST /pairing/refresh` — refresh a pairing token (not yet implemented in daemon;
  documented for target contract)

Each endpoint includes: method and path, request format, full JSON response
examples with all fields documented in tables, all error responses with codes.

### 5. docs/architecture.md

Covers:

- System overview ASCII diagram with all components
- Module guide: `daemon.py` (MinerSimulator, GatewayHandler, ThreadedHTTPServer),
  `cli.py` (daemon_call, cmd_* functions), `store.py` (Principal, Pairing,
  has_capability), `spine.py` (append-only JSONL journal, EventKind enum)
- Module dependency graph
- State file layout (`state/daemon.pid`, `state/principal.json`,
  `state/pairing-store.json`, `state/event-spine.jsonl`)
- HTTP endpoint map
- Data flow: control command flow and status read flow
- Auth model: observe vs control capability enforcement in CLI
- Design decisions: stdlib-only, LAN-only, JSONL not SQLite, single HTML file,
  scriptable CLI, event spine as source of truth

### 6. Code Fix: Enum JSON Serialization

Fixed `daemon.py` to return `.value` on all `MinerStatus` and `MinerMode` enum
returns so JSON responses contain plain strings (`"stopped"`) instead of Python
repr format (`"MinerStatus.STOPPED"`). Affected methods: `start()`, `stop()`,
`set_mode()`, `get_snapshot()`.

## Verification Evidence

Clean verification run (all commands from README quickstart):

```
./scripts/bootstrap_home_miner.sh
→ Daemon started
→ principal_id created, alice-phone paired with observe capability

./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
→ {"success": true, "device_name": "my-phone", "capabilities": ["observe", "control"]}

python3 services/home-miner-daemon/cli.py status --client my-phone
→ {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}

cli.py control --client my-phone --action set_mode --mode balanced
→ {"success": true, "acknowledged": true, "message": "Miner set_mode accepted..."}

curl http://127.0.0.1:8080/
→ {"error": "not_found"}  ← daemon does not serve the HTML UI

Open apps/zend-home-gateway/index.html in a browser
→ UI shell renders, then shows "Unable to connect to Zend Home"
  (inferred cause: file-origin request to daemon without CORS support)
```

## Acceptance Criteria

- [x] README.md under 200 lines, includes a 5-command CLI quickstart
- [x] All four docs files created with accurate content
- [x] README CLI quickstart commands all work from fresh clone
- [x] API reference clearly distinguishes implemented daemon endpoints from target contracts
- [x] Architecture doc correctly describes current system
- [ ] Contributor guide enables meaningful test suite execution
- [ ] Operator guide covers full phone-browser deployment lifecycle
- [x] Code bug (enum serialization) fixed during verification
