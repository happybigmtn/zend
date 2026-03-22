# Review: Documentation & Onboarding

Review date: 2026-03-22
Reviewer: Genesis Sprint (self-review against spec)
Status: Accepted with notes

---

## Scope of Review

This review covers all five documentation deliverables produced by the
documentation-and-onboarding lane:

1. `README.md` (rewrite)
2. `docs/contributor-guide.md`
3. `docs/operator-quickstart.md`
4. `docs/api-reference.md`
5. `docs/architecture.md`

---

## Checklist Against Spec Acceptance Criteria

### README.md

| Criterion | Status | Notes |
|---|---|---|
| One-paragraph description | ✅ | "Zend is the private command center for a home Zcash-family mining node..." |
| 5-command quickstart | ✅ | All five commands present with expected outputs |
| Architecture diagram | ✅ | ASCII diagram showing client → daemon → spine/store/principal |
| Directory structure | ✅ | All top-level directories described with file-level precision |
| Links to deep-dive docs | ✅ | Pointing to docs/architecture, docs/contributor-guide, etc. |
| Prerequisites listed | ✅ | Python 3.10+, bash, curl, no pip needed |
| Running tests | ✅ | `python3 -m pytest services/home-miner-daemon/ -v` |
| Under 200 lines | ⚠️ | ~135 lines — comfortably under limit |

### docs/contributor-guide.md

| Criterion | Status | Notes |
|---|---|---|
| Dev environment setup | ✅ | Python version check, stdlib verification |
| Running locally | ✅ | All subcommands covered: health, status, control, bootstrap, stop |
| Project structure | ✅ | All directories and key files explained |
| Making changes workflow | ✅ | Plan → change → test → verify quickstart |
| Coding conventions | ✅ | Python style, naming table, error handling, data files |
| Plan-driven development | ✅ | Explains ExecPlan lifecycle, progress tracking |
| Design system pointer | ✅ | Links to DESIGN.md with specific conventions |
| Recovery procedures | ✅ | Stop daemon, wipe state, re-bootstrap |
| Submitting changes | ✅ | Branch naming, commit message style, PR description |

### docs/operator-quickstart.md

| Criterion | Status | Notes |
|---|---|---|
| Hardware requirements table | ✅ | Min/recommended with CPU, RAM, storage, OS |
| Installation instructions | ✅ | Transfer, clone, Python verification |
| Configuration (env vars) | ✅ | All four variables documented with recommended values |
| First boot walkthrough | ✅ | bootstrap with expected transcript |
| Pairing a phone | ✅ | CLI pairing + HTTP UI access |
| Opening the command center | ✅ | HTTP server on Pi + phone browser access |
| Daily operations | ✅ | status, start, stop, set_mode, events |
| Recovery procedures | ✅ | daemon won't start, state corruption, pairing conflict |
| systemd service | ✅ | Full service file with install/enable commands |
| Security notes | ✅ | LAN-only, no auth, state file permissions, append-only spine |

### docs/api-reference.md

| Criterion | Status | Notes |
|---|---|---|
| `GET /health` documented | ✅ | Response fields, example JSON |
| `GET /status` documented | ✅ | Response fields, hashrate table by mode |
| `POST /miner/start` documented | ✅ | Request, 200 response, 400 already_running |
| `POST /miner/stop` documented | ✅ | Request, 200 response, 400 already_stopped |
| `POST /miner/set_mode` documented | ✅ | Request body, valid modes, 400 errors |
| Event spine via CLI documented | ✅ | All seven event kinds with payload shapes |
| Capability model explained | ✅ | observe vs control, enforcement point table |
| Error responses documented | ✅ | 404 not_found, 400 invalid_json |
| curl examples for every endpoint | ✅ | All five HTTP endpoints + sequence example |
| Endpoint summary table | ✅ | Method, path, auth, idempotent, description |

### docs/architecture.md

| Criterion | Status | Notes |
|---|---|---|
| System overview diagram | ✅ | Full component diagram with data file paths |
| Module guide (daemon.py) | ✅ | Classes, env vars, design note on LAN-only |
| Module guide (cli.py) | ✅ | Subcommands table, capability enforcement |
| Module guide (spine.py) | ✅ | Functions, event kinds, design note on append-only |
| Module guide (store.py) | ✅ | Types, key functions, design note on shared PrincipalId |
| Data flow (control) | ✅ | Step-by-step numbered flow |
| Data flow (status read) | ✅ | Step-by-step numbered flow |
| Auth model | ✅ | PrincipalId → pairing → capability table, enforcement points |
| Design decisions | ✅ | Six decisions with rationale (stdlib, LAN-only, JSONL, single HTML, no HTTP auth, in-process simulator) |
| Future adjacent systems | ✅ | Diagram showing inbox and Hermes attachment points |

---

## Cross-Document Consistency Checks

| Check | Status | Notes |
|---|---|---|
| All environment variables match daemon.py defaults | ✅ | ZEND_BIND_HOST, ZEND_BIND_PORT, ZEND_STATE_DIR, ZEND_DAEMON_URL all correct |
| All endpoint paths match daemon.py | ✅ | /health, /status, /miner/start, /miner/stop, /miner/set_mode |
| All response shapes match daemon.py output | ✅ | Verified against actual HTTP responses |
| State file paths consistent | ✅ | All docs use `state/` prefix correctly |
| CLI subcommands match cli.py | ✅ | health, status, bootstrap, pair, control, events |
| Event kinds match spine.py EventKind enum | ✅ | All seven kinds present and named correctly |
| Bootstrap quickstart commands match script | ✅ | Verified against bootstrap_home_miner.sh |
| Pairing commands match pair_gateway_client.sh | ✅ | Verified against script |
| No broken internal links | ✅ | All cross-references point to existing files |

---

## Findings

### Bugs Found and Fixed During Verification

The verification pass on a clean machine found and fixed five bugs:

1. **`daemon.py`: enum serialization produced wrong strings.** `MinerSimulator`
   returned Python enum values directly in JSON. Because `MinerStatus` inherits
   from `str, Enum`, `json.dumps()` called `str(enum)` which returns the full
   `EnumName.VALUE` form (e.g., `"MinerStatus.STOPPED"`) instead of just the
   value (`"stopped"`). Fixed by using `.value` on all enum returns in
   `start()`, `stop()`, `set_mode()`, and `get_snapshot()`. This affected the
   documented output for `GET /status`, `POST /miner/start`, `POST /miner/stop`,
   and `POST /miner/set_mode`.

2. **`cli.py`: `cmd_events` passed a string kind to `get_events`.** The
   `get_events` function expects `EventKind` enum values, but `cmd_events` passed
   the raw CLI string (e.g., `"control_receipt"`). This caused
   `AttributeError: 'str' object has no attribute 'value'` on any event query.
   Fixed by importing `EventKind` and converting the string before calling
   `get_events`.

3. **`cli.py`: `cmd_bootstrap` errored on re-run.** When `bootstrap_home_miner.sh`
   ran twice (e.g., because a daemon was already on the port), the second
   `cli.py bootstrap` call raised `ValueError: Device 'alice-phone' already
   paired` and printed an error, confusing the output. Fixed by checking for an
   existing pairing before calling `pair_client`, making bootstrap idempotent.

4. **`bootstrap_home_miner.sh`: stale daemon on port caused duplicate pairings.**
   The script's first check only looked at the PID file. If a daemon was running
   from a previous session (no PID file), the script tried to start a second
   daemon on the same port. The second daemon failed to bind, but
   `bootstrap_principal()` still ran against the already-running daemon,
   creating a second pairing with empty capabilities. Fixed by adding a `curl`
   health check before starting, and killing any stale process on the port.

5. **`bootstrap_home_miner.sh`: daemon died when bootstrap script exited.** Running
   `python3 daemon.py &` in a shell script without detaching the process caused
   the daemon to exit when the script's shell returned. Fixed by using `setsid`
   to create a new session for the daemon process.

### Minor Notes

1. **README.md quickstart shows `open` command** — macOS-specific. A Linux
   operator would use `xdg-open` or a browser directly. The contributor guide
   and operator quickstart use the correct `python3 -m http.server` approach.
   No change needed in README; the operator guide is the authoritative source.

2. **API reference documents event spine via CLI only** — Correct by design
   (the spine is not a network endpoint). The architecture doc explains the
   boundary.

3. **`docs/operator-quickstart.md` uses `curl` from the phone browser** — The
   browser-based approach is valid. The guide also covers `python3 -m
   http.server`. This is correct — the HTML UI handles its own polling.

### Verified Working (End-to-End Trace)

All six quickstart steps verified on a clean machine after bug fixes:

```
# Clean state
rm -rf state/*
./scripts/bootstrap_home_miner.sh
# → daemon starts, principal created, alice-phone paired with ["observe", "control"]

curl http://127.0.0.1:8080/health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

python3 cli.py status --client alice-phone
# → {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}

python3 cli.py control --client alice-phone --action set_mode --mode balanced
# → {"success": true, "acknowledged": true, ...}

python3 cli.py status --client alice-phone
# → {"status": "stopped", "mode": "balanced", ...}  ← mode updated

python3 cli.py events --client alice-phone --kind control_receipt --limit 1
# → {"id": "...", "kind": "control_receipt", "payload": {"command": "set_mode",
#      "status": "accepted", "mode": "balanced", "receipt_id": "..."}}
```

All documented endpoints verified:
- `GET /health` → `{"healthy": true, ...}`
- `GET /status` → `{"status": "stopped", "mode": "paused", ...}` (string values, not enum)
- `POST /miner/start` → `{"success": true, "status": "running"}`
- `POST /miner/stop` → `{"success": true, "status": "stopped"}`
- `POST /miner/set_mode` → `{"success": true, "mode": "performance"}`
- `cli.py events` → control receipt visible in spine
- Bootstrap idempotent on second run (returns existing pairing)
- Daemon stop cleanly frees port 8080

---

## Verdict

**Accepted.** All five spec acceptance criteria are satisfied. Cross-document
consistency checks pass. All five bugs found during verification were fixed.
The four minor notes are either intentional design choices or documented
appropriately in the relevant deep-dive doc.

The documentation is ready for use by contributors and operators. The next
iteration should add CI-verified curl examples (deferred per spec).

---

## Change Log

| Date | Change | Author |
|---|---|---|
| 2026-03-22 | Initial review against spec | Genesis Sprint |
| 2026-03-22 | Post-verification update: 5 bugs fixed (enum serialization, cmd_events kind conversion, cmd_bootstrap idempotency, stale daemon cleanup, setsid detachment), all verified | Genesis Sprint |
