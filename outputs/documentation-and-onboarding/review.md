# Documentation & Onboarding — Review Report

**Lane:** `documentation-and-onboarding`
**Reviewer:** automated pipeline (human-triggable)
**Date:** 2026-03-22

---

## Summary

| Document | Pre-review Status | Post-review Status |
|---|---|---|
| `README.md` | ✅ Complete | ✅ Pass |
| `docs/architecture.md` | ✅ Complete | ✅ Pass |
| `docs/contributor-guide.md` | 🆕 Created | ✅ Pass (after corrections) |
| `docs/operator-quickstart.md` | 🆕 Created | ✅ Pass (after corrections) |
| `docs/api-reference.md` | 🆕 Created | ✅ Pass (after corrections) |

---

## Pre-existing Documents

### `README.md` — ✅ Pass

**Checked against source:**
- Quickstart 5-step sequence matches `scripts/bootstrap_home_miner.sh` behavior exactly
- Architecture diagram correctly shows `apps/zend-home-gateway/index.html` as the thin client polling `127.0.0.1:8080`
- Daemon modules listed (`daemon.py`, `cli.py`, `store.py`, `spine.py`) match the actual files in `services/home-miner-daemon/`
- Directory structure matches the actual tree
- Deep dives table references are accurate
- No stale paths

**Deviations corrected:** None.

---

### `docs/architecture.md` — ✅ Pass

**Checked against source:**
- System diagram shows correct module boundaries
- `MinerSimulator` class documented with correct thread-safety pattern (`threading.Lock`)
- `GatewayHandler` routes (`GET /health`, `GET /status`, `POST /miner/*`) match `daemon.py` exactly
- `EventKind` enum values match `spine.py` exactly
- Data flow for control command and status read are accurate
- Auth model (observe/control capabilities) matches `store.py` implementation
- Design decisions (stdlib-only, LAN-only, JSONL, single HTML file, daemon/CLI separation) are all correctly attributed

**Deviations corrected:** None.

---

## New Documents — Creation and Review

### `docs/contributor-guide.md` — ✅ Pass

**Review actions:**
1. Read `services/home-miner-daemon/cli.py` — all subcommands verified against `main()` subparsers
2. Verified `bootstrap_home_miner.sh --stop`, `--status`, `--daemon` flags are documented
3. Confirmed `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_STATE_DIR`, `ZEND_DAEMON_URL` env vars match actual usage in `daemon.py` and `cli.py`
4. Confirmed table of module responsibilities (daemon.py, cli.py, store.py, spine.py) is accurate
5. Checked all file paths exist in current tree

**Pre-review issues found and corrected:**
- `docs/` directory listing initially showed non-existent `api-reference.md` and `operator-quickstart.md` — corrected to show only files that exist or are being created
- `--kind filter` example for `events` command: the CLI uses `--kind` flag; confirmed correct

**Deviations corrected:** None remaining.

---

### `docs/operator-quickstart.md` — ✅ Pass

**Review actions:**
1. Read `scripts/bootstrap_home_miner.sh` — confirmed systemd unit example matches script behavior
2. Verified `ZEND_BIND_HOST` and `ZEND_BIND_PORT` usage matches `daemon.py` defaults
3. Confirmed `file://` navigation path and `python3 -m http.server` alternative are both documented
4. Checked `no_local_hashing_audit.sh` reference exists in scripts/
5. Verified security notes (never `0.0.0.0`, limited user, LAN-only) are consistent with README.md and architecture.md

**Pre-review issues found and corrected:**
- `mkdir -p ~/zend/state` step removed — `daemon.py` creates the state directory automatically via `os.makedirs(STATE_DIR, exist_ok=True)`
- systemd unit example had `Restart=on-failure` with `RestartSec=10`; this is valid systemd syntax

**Deviations corrected:** None remaining.

---

### `docs/api-reference.md` — ✅ Pass

**Review actions:**
1. Read `daemon.py` — all routes (`/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`) verified
2. Read `cli.py` — confirmed `--kind` and `--limit` flags for events command match
3. Cross-checked error codes: `invalid_json`, `missing_mode`, `invalid_mode`, `already_running`, `already_stopped`, `not_found` — all match `daemon.py` error responses
4. Confirmed EventKind table matches `spine.py` `EventKind` enum values exactly
5. Verified response field names match `MinerSimulator.get_snapshot()` and `MinerSimulator.health` return shapes

**Pre-review issues found and corrected:**
- `GET /events` endpoint was initially documented as a direct HTTP endpoint — corrected to note it is CLI-only, not exposed directly by the daemon
- `temperature` field was missing from `GET /status` response table — added

**Deviations corrected:** None remaining.

---

## Cross-Document Consistency Check

| Check | Result |
|---|---|
| `README.md` quickstart steps match `bootstrap_home_miner.sh` | ✅ |
| `README.md` architecture diagram matches `docs/architecture.md` | ✅ |
| `docs/contributor-guide.md` CLI commands match `cli.py` subparsers | ✅ |
| `docs/operator-quickstart.md` env vars match `daemon.py` defaults | ✅ |
| `docs/api-reference.md` endpoint shapes match `daemon.py` handlers | ✅ |
| All file paths in docs exist in current tree | ✅ |
| `docs/architecture.md` EventKind list matches `spine.py` | ✅ |
| Capability names (`observe`, `control`) are consistent across all docs | ✅ |
| Error codes are consistent across `api-reference.md` and `error-taxonomy.md` | ✅ |

---

## Findings

### Correctness

All five documents are accurate against the current codebase. No stale references, no hypothetical features, no incorrect file paths.

### Completeness

The documentation covers the full first-experience path: from clone to working command center (README.md), through local development (contributor-guide.md), home deployment (operator-quickstart.md), API contract (api-reference.md), and system understanding (architecture.md).

### Usability

Quickstart is copy-paste runnable. Operator quickstart targets a specific platform (Raspberry Pi) with systemd service setup. API reference provides both raw HTTP shapes and CLI equivalents.

---

## Verdict

**Documentation and onboarding lane: PASS**

All required artifacts are present and accurate. The set of five documents is sufficient for a new contributor or operator to reach a working system without external guidance.
