# Documentation & Onboarding — Review

**Reviewer:** claude-opus-4-6
**Date:** 2026-03-22
**Verdict:** REVISE — documentation exists but contains factual errors, phantom endpoints, and a misleading security narrative that will break operator trust on first contact.

---

## Summary

The lane produced five Markdown files covering README, contributor guide, operator quickstart, API reference, and architecture. The writing is competent and well-structured. The problem is accuracy: several documented features do not exist in code, the security model described in docs is not enforced, and key quickstart paths will fail on a fresh clone.

The prior review in this file was a rubber stamp. It claimed "All code examples tested" and "Tests run ✅" — both are false. No test files exist. Phantom endpoints were marked as verified. This review replaces that assessment with findings derived from reading every source file.

---

## 1. Correctness — Documentation vs. Codebase

### FAIL: Phantom Endpoints

| Documented Endpoint | Exists in `daemon.py`? |
|---------------------|----------------------|
| `GET /health` | Yes |
| `GET /status` | Yes |
| `POST /miner/start` | Yes |
| `POST /miner/stop` | Yes |
| `POST /miner/set_mode` | Yes |
| **`GET /spine/events`** | **No** — `do_GET` only handles `/health` and `/status` |
| **`GET /gateway`** | **No** — no such route exists |

The API reference (`docs/api-reference.md:184-222`) documents `GET /spine/events` with query parameters, response format, and event kinds. This endpoint does not exist. The daemon will return `{"error": "not_found"}`.

The operator quickstart (`docs/operator-quickstart.md:111`) instructs operators to navigate to `http://<daemon-ip>:8080/gateway`. This route does not exist. The operator's first LAN access attempt will 404.

### FAIL: Broken Import Path

The contributor guide (`docs/contributor-guide.md:31`) includes:

```
python3 -c "import services.home_miner_daemon.store; print('OK')"
```

The directory is named `home-miner-daemon` (hyphens). Python cannot import modules with hyphens in the name. This command will fail with `ModuleNotFoundError`. The actual code in `cli.py:17` works around this by inserting the module directory directly into `sys.path`.

### FAIL: No Test Files Exist

The contributor guide (`docs/contributor-guide.md:38-44`) and README (`README.md:97-101`) instruct contributors to run `pytest services/home-miner-daemon/ -v` and reference a specific test file `test_spine.py`. No test files exist in the codebase. Running pytest will discover zero tests.

### FAIL: CLI `get_events` Kind Filter Bug

The CLI (`cli.py:190`) passes a raw string to `spine.get_events(kind=kind)`. The function (`spine.py:87`) calls `kind.value` — but strings don't have a `.value` attribute. Filtering events by kind via CLI will raise `AttributeError`. This bug is not documented and affects any documented `--kind` usage.

### WARN: `ZEND_TOKEN_TTL_HOURS` Does Not Exist

The operator quickstart (`docs/operator-quickstart.md:57`) documents `ZEND_TOKEN_TTL_HOURS` as a configuration variable. No code reads this variable. It has no effect.

### WARN: Spec Proof Text Claims `{"status": "ok"}`

The spec (`outputs/documentation-and-onboarding/spec.md:61`) says a reader should see `{"status": "ok"}` from the daemon. No endpoint returns this exact response. `/health` returns `{"healthy": true, ...}`, `/status` returns `{"status": "stopped", ...}`.

### WARN: CORS Will Block Gateway UI in Most Scenarios

The gateway UI hardcodes `API_BASE = 'http://127.0.0.1:8080'` (`index.html:632`). The daemon sends no CORS headers. Opening the HTML from `file://` creates a `null` origin, and modern browsers will block `fetch()` calls to `localhost`. The quickstart path of `open apps/zend-home-gateway/index.html` will silently fail in Chrome/Firefox/Safari. The API reference acknowledges this (`docs/api-reference.md:353`) but the README and contributor guide do not.

---

## 2. Milestone Fit

### Deliverable Inventory

| Artifact | Spec Requirement | Delivered | Accurate |
|----------|-----------------|-----------|----------|
| `README.md` | Quickstart, architecture, directory, links | Yes | Partially — quickstart has broken steps |
| `docs/contributor-guide.md` | Dev setup, project structure, conventions | Yes | Partially — import test and test commands fail |
| `docs/operator-quickstart.md` | Hardware, install, first boot, pairing | Yes | Partially — `/gateway` route and `TOKEN_TTL_HOURS` are phantom |
| `docs/api-reference.md` | All endpoints, examples, errors | Yes | No — documents phantom `/spine/events` endpoint |
| `docs/architecture.md` | System diagrams, module guide, auth model | Yes | Partially — auth model describes ideal, not actual |

### Spec Proof-of-Completeness Failures

The spec defines five proofs. Three fail:

1. "Follow README quickstart from fresh clone and see daemon return `{"status": "ok"}`" — No endpoint returns `{"status": "ok"}`.

2. "Set up dev environment and run tests following contributor guide" — No tests exist. `pytest` discovers nothing.

3. "Deploy on Raspberry Pi following operator guide" — Step 5 directs to `/gateway` which 404s.

---

## 3. Nemesis Pass 1 — First-Principles Trust Boundary Challenge

### CRITICAL: HTTP API Has Zero Authentication

The daemon (`daemon.py:168-200`) serves all endpoints to any caller. There is no pairing check, no capability check, no token validation, and no IP filtering at the HTTP layer.

The documentation creates a false narrative:
- API reference (`docs/api-reference.md:7`): "Access is controlled by device pairing and capabilities"
- Architecture (`docs/architecture.md:81`): "No authentication on endpoints (handled by pairing store)"
- Architecture auth flow (`docs/architecture.md:288-299`): Describes a check flow that does not exist in the daemon

**Reality:** The capability check (`has_capability()`) only runs inside the CLI process (`cli.py:47`, `cli.py:134`). The HTTP API — which is what the gateway UI, scripts, and any LAN device call — enforces nothing. Anyone who can reach port 8080 can start/stop mining and change modes.

This is the most dangerous documentation error. An operator who reads "access is controlled by device pairing" will believe their miner is protected. It is not.

### CRITICAL: Pairing Token Lifecycle Is Dead Code

`create_pairing_token()` (`store.py:86-90`) generates a token and sets `expires = datetime.now(timezone.utc).isoformat()` — the token expires at the instant of creation. But this doesn't matter because:

1. No code ever checks `token_expires_at`
2. No code ever sets `token_used = True`
3. No code ever validates a token against a request

The pairing store records capabilities, and the CLI checks them, but the token ceremony is pure theater.

### HIGH: LAN Boundary Is Not Enforced

The operator quickstart (`docs/operator-quickstart.md:247`) says the daemon "only accepts connections from your LAN". The code binds to `0.0.0.0` (as the operator quickstart recommends at line 50) with no IP filtering. If the machine has a public IP or is behind a misconfigured router, the daemon is internet-accessible. The "LAN-only" claim depends entirely on the operator's network configuration, not on any enforcement in the daemon.

### HIGH: Operator Revocation Is Broken

The revocation instructions (`docs/operator-quickstart.md:264-270`) tell operators to edit `pairing-store.json` to revoke access. Since the daemon never reads the pairing store, this only affects CLI-mediated access. HTTP API access is unaffected. The operator will believe they revoked access, but direct HTTP callers can still control the miner.

---

## 4. Nemesis Pass 2 — Coupled-State Review

### Pairing Store ↔ Daemon State: Decoupled and Inconsistent

The pairing store (`state/pairing-store.json`) and the daemon's miner state are two independent systems with no coupling:

- A device removed from the pairing store can still control the miner via HTTP
- A device with `observe` only can still call `POST /miner/start` directly
- The event spine records CLI-mediated operations but not direct HTTP operations

**Consequence:** The event spine is not a reliable audit trail. Operations performed directly against the HTTP API leave no trace in the spine.

### Event Spine Crash Safety: Overstated

The architecture doc (`docs/architecture.md:322`) claims "Appending to file is atomic on most filesystems." This is misleading. `_save_event()` (`spine.py:63-65`) writes via Python's `write()`. If the process crashes mid-write, a partial JSON line is written. The next `_load_events()` call will crash on `json.loads()` of the truncated line with no recovery path — no line validation, no skip-on-error, no fsync.

### Pairing Store File I/O: Not Atomic, Not Locked

`pair_client()` (`store.py:93-118`) performs a load-modify-save cycle with no file locking. Two concurrent pairing operations can lose data via a classic TOCTOU race.

### Principal Identity: No Integrity Protection

`principal.json` is plain JSON with no MAC, signature, or checksum. Any process with write access can replace the principal identity. All subsequent pairings and events will reference the attacker's principal ID.

---

## 5. Remaining Blockers

### Must Fix Before Merge

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 1 | Remove `GET /spine/events` from API reference — endpoint doesn't exist | Correctness | `docs/api-reference.md` |
| 2 | Remove `GET /gateway` from operator quickstart — route doesn't exist | Correctness | `docs/operator-quickstart.md` |
| 3 | Fix import test command (hyphens vs underscores) or remove it | Correctness | `docs/contributor-guide.md` |
| 4 | Remove or qualify test commands — no tests exist | Correctness | `docs/contributor-guide.md`, `README.md` |
| 5 | Remove `ZEND_TOKEN_TTL_HOURS` — not implemented | Correctness | `docs/operator-quickstart.md` |
| 6 | Fix auth narrative — state clearly that HTTP API is unauthenticated in milestone 1 | Security | `docs/api-reference.md`, `docs/architecture.md` |
| 7 | Fix spec proof text — no endpoint returns `{"status": "ok"}` | Spec | `outputs/documentation-and-onboarding/spec.md` |

### Should Fix

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 8 | Add CORS note to README quickstart (or add CORS headers to daemon) | UX | `README.md`, possibly `daemon.py` |
| 9 | Note that event spine is not a complete audit trail (HTTP bypasses CLI) | Accuracy | `docs/architecture.md` |
| 10 | Note crash-safety limitation of JSONL append | Accuracy | `docs/architecture.md` |
| 11 | Fix `get_events` kind filter bug (string vs EventKind) | Bug | `services/home-miner-daemon/cli.py` or `spine.py` |

### Out of Scope for This Lane (Track Separately)

| # | Issue | Severity |
|---|-------|----------|
| 12 | Daemon needs HTTP-level auth before any non-localhost binding | Security |
| 13 | Pairing token lifecycle needs actual implementation | Security |
| 14 | Pairing store needs file locking | Reliability |
| 15 | Event spine needs line-level error recovery | Reliability |
| 16 | Principal file needs integrity protection | Security |

---

## 6. What Went Right

- The five-doc structure (README, contributor guide, operator quickstart, API reference, architecture) is sound and follows the plan.
- Writing quality is clear and accessible. Tone is appropriate for the audience.
- Architecture diagrams and data flow sections are useful and mostly accurate.
- Design system references are correct and consistent with `DESIGN.md`.
- Troubleshooting sections in operator quickstart and contributor guide are practical.
- Decision documentation in `architecture.md` captures real trade-offs.

---

## Verdict

**REVISE.** The documentation shell is solid but ships with factual errors that will immediately fail on a fresh clone (phantom endpoints, broken import, nonexistent tests) and a security narrative that misrepresents the actual auth boundary. Items 1-7 must be fixed before this lane can close.
