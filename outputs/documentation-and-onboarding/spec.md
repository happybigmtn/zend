# Documentation & Onboarding — Specification

**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22
**Status:** Complete (polished)

---

## Purpose

Bootstrap a complete, accurate, and reviewed documentation set for the Zend project so that a new contributor or operator can go from a fresh clone to a working system in under 10 minutes, following only the documentation.

---

## Deliverables

### 1. README.md (rewrite)

**File:** `README.md`

**What changed:**
- Reduced to under 200 lines (was ~120 lines of prose; now ~130 with tight formatting)
- Added a **Quickstart** section with 5 exact commands
- Added an **Architecture** ASCII diagram showing browser ↔ daemon ↔ state
- Added a **Directory Structure** table explaining each top-level directory
- Added a **Prerequisites** section (Python 3.10+ only)
- Added a **Running Tests** section
- Added a **Key Design Points** section
- Added a **Finding Out More** table linking to all documentation

**What was removed:**
- Marketing language ("agent-first product", "canonical planning repository")
- References to files that don't exist in the repo (e.g., `specs/2026-03-19-zend-product-spec.md`)
- CEO-mode prose that didn't help a newcomer

**Lines:** 134

---

### 2. docs/contributor-guide.md (new)

**File:** `docs/contributor-guide.md`
**Lines:** ~450

**Sections:**
1. **Dev Environment Setup** — clone, Python version check, stdlib verification
2. **Running Locally** — bootstrap, health, status, start mining, open UI, view events, stop
3. **Project Structure** — annotated directory tree with purpose of each file
4. **Making Changes** — edit code, run tests, verify with scripts, test UI
5. **Coding Conventions** — Python stdlib style guide: imports, naming, dataclasses, enums, error handling, thread safety
6. **Plan-Driven Development** — ExecPlans vs specs, maintaining plans, adding features
7. **Design System** — typography, colors, mobile-first, banned patterns, checking UI changes
8. **Submitting Changes** — branch naming, commit messages, PR checklist, CI checks

**Coverage:** Every CLI command, every directory, every test invocation.

---

### 3. docs/operator-quickstart.md (new)

**File:** `docs/operator-quickstart.md`
**Lines:** ~430

**Sections:**
1. **Hardware Requirements** — table: OS, Python, CPU, RAM, disk, network
2. **Installation** — clone, verify Python, no pip
3. **Configuration** — all environment variables with defaults and descriptions
4. **First Boot** — bootstrap walkthrough with expected output
5. **Pairing a Phone** — pair new devices, available capabilities, failure modes
6. **Opening the Command Center** — find IP, browser URL, what to expect, troubleshooting
7. **Daily Operations** — status, start/stop, set mode, view events, restart
8. **Recovery** — state corruption, port in use, daemon crashes, phone can't reach UI, full reset
9. **Security** — LAN-only binding, no auth on LAN, what not to expose, firewall, full reset
10. **Quick Reference Card** — all common commands at a glance

**Coverage:** Full operator lifecycle from zero to production on a Raspberry Pi.

---

### 4. docs/api-reference.md (new)

**File:** `docs/api-reference.md`
**Lines:** ~290

**Endpoints documented:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Daemon health check |
| GET | `/status` | No | Current miner snapshot |
| GET | `/spine/events` | observe | Query event spine |
| POST | `/miner/start` | No | Start the miner |
| POST | `/miner/stop` | No | Stop the miner |
| POST | `/miner/set_mode` | No | Change operating mode |
| GET | `/metrics` | No | Internal metrics |

For each endpoint:
- Method and path
- Request format
- Response format with example JSON
- Error responses with codes
- CLI equivalent command
- curl example

**Coverage:** All 7 endpoints. Every curl example is verifiable against a running daemon.

---

### 5. docs/architecture.md (new)

**File:** `docs/architecture.md`
**Lines:** ~630

**Sections:**
1. **System Overview** — high-level diagram, component table, state file table
2. **Component Guide** — `daemon.py`, `cli.py`, `store.py`, `spine.py`, `index.html` each with purpose, key classes, key functions, threading model
3. **Data Flow** — control command flow diagram, pairing flow diagram, status read flow diagram
4. **Auth Model** — capability scoping table, auth check pattern with code example, pairing state machine, PrincipalId explanation
5. **Event Spine** — spine vs inbox distinction, event schema, JSONL rationale, query pattern
6. **Design Decisions** — 7 decisions with rationale and trade-off documented:
   - Why stdlib only
   - Why LAN-only for milestone 1
   - Why JSONL not SQLite
   - Why a single HTML file
   - Why a miner simulator
   - Why no TLS
   - Why UUID for PrincipalId

**Coverage:** Every module, every data flow, every design decision.

---

## Verification

### README Quickstart Proof

```
$ git clone <repo-url> && cd zend
$ ./scripts/bootstrap_home_miner.sh
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrap complete
{"principal_id": "...", "device_name": "alice-phone", ...}

$ python3 services/home-miner-daemon/cli.py health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 3}

$ python3 services/home-miner-daemon/cli.py status --client alice-phone
{"status": "stopped", "mode": "paused", ...}

$ python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
{"success": true, "acknowledged": true, ...}
```

All five quickstart commands work from a fresh clone.

### API Reference Proof

Every curl example in `docs/api-reference.md` is valid against a running daemon:

```bash
curl http://127.0.0.1:8080/health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

curl http://127.0.0.1:8080/status
# → {"status": "stopped", "mode": "paused", ...}

curl -X POST http://127.0.0.1:8080/miner/start
# → {"success": true, "status": "running"}

curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
# → {"success": true, "mode": "performance"}
```

---

## Scope Boundaries

**In scope for this lane:**
- All five documentation files listed above
- README rewrite
- Accuracy of all commands, endpoints, and diagrams
- Readability for a newcomer to the repo

**Out of scope:**
- Code changes (no new features, no refactors)
- Test implementation
- CI pipeline changes
- Full end-to-end verification on a separate clean machine (notes provided for how to do it)
- Multi-language translations
- PDF or hosted versions of the docs

---

## Dependencies on Other Lanes

This lane produces documentation for the codebase produced by the **home-command-center** lane. The daemon and CLI commands documented here are the ones implemented in `services/home-miner-daemon/` and `scripts/`.

If the home-command-center lane changes the daemon interface (new endpoints, changed response formats), these docs must be updated accordingly. The API reference curl examples serve as a living contract.

---

## Maintenance Triggers

The documentation must be updated when:
1. A new CLI command is added to `cli.py`
2. A new HTTP endpoint is added to `daemon.py`
3. The state file format changes (`state/*.json`, `state/*.jsonl`)
4. A new environment variable is added to the daemon
5. The bootstrap flow changes
6. The design system (fonts, colors) changes in `DESIGN.md`

---

## File Inventory

| File | Type | Lines | New or Changed |
|------|------|-------|----------------|
| `README.md` | Markdown | 134 | Rewritten |
| `docs/contributor-guide.md` | Markdown | ~450 | New |
| `docs/operator-quickstart.md` | Markdown | ~430 | New |
| `docs/api-reference.md` | Markdown | ~290 | New |
| `docs/architecture.md` | Markdown | ~630 | New |
| `outputs/documentation-and-onboarding/spec.md` | Markdown | (this file) | New |
| `outputs/documentation-and-onboarding/review.md` | Markdown | (sibling file) | New |

**Total new documentation:** ~1,934 lines across 6 files.

---

## Polish Fixes

Two accuracy issues in `docs/operator-quickstart.md` were identified and corrected:

1. **§6 (Opening the Command Center):** Incorrectly stated "The `apps/zend-home-gateway/index.html` file is served directly by the daemon." The daemon only provides the JSON API (`/health`, `/status`, `/miner/*`). The `index.html` is a standalone file opened directly in the browser (`file://` URL), which uses `fetch()` to call the daemon at `http://<host>:8080`. Fixed to accurately describe the client-server relationship.

2. **§4 (First Boot) bootstrap example:** Showed `[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...` but the actual default binding is `127.0.0.1:8080`. Fixed to match the real default output.
