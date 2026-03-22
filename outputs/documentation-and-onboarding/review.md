# Documentation & Onboarding — Review

**Reviewer**: Claude Opus 4.6
**Date**: 2026-03-22
**Verdict**: **BLOCKED** — 2 missing artifacts, 7 correctness failures, 3 security concerns

---

## Deliverable Inventory

| Deliverable | Spec Requirement | Status |
|---|---|---|
| README.md rewrite | Quickstart, arch diagram, prereqs | **Exists, inaccurate** |
| docs/contributor-guide.md | Dev setup, conventions | **Exists, inaccurate** |
| docs/operator-quickstart.md | Hardware deployment | **Exists, inaccurate** |
| docs/api-reference.md | All endpoints documented | **Exists, inaccurate** |
| docs/architecture.md | System diagrams, modules | **MISSING** |

`docs/architecture.md` is linked from README line 118 and required by the spec. It does not exist.

---

## Correctness Failures

### C1. Ghost HTTP Endpoints

`docs/api-reference.md` documents two endpoints that do not exist in `daemon.py`:

- **GET /spine/events** (api-reference.md:105–158) — The daemon only handles `/health`, `/status`, and `/miner/*`. Spine events are read directly from the JSONL file by the CLI, not served over HTTP.
- **POST /pairing/refresh** (api-reference.md:288–336) — No such handler exists in daemon.py.

These curl examples will 404 against a running daemon, failing acceptance criterion 4.

### C2. Ghost Endpoints in README Diagram

README.md lines 41–42 show `/spine/*` and `/metrics` inside the daemon box. Neither endpoint exists.

### C3. Quickstart Capability Mismatch

README.md quickstart step 5:
```
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

`cmd_bootstrap` (cli.py:78) grants only `['observe']`. The `control` command checks `has_capability(args.client, 'control')` and will print `{"error": "unauthorized"}`. The quickstart is broken on a clean clone.

### C4. Phantom Auth on HTTP Endpoints

api-reference.md lines 25–28 state `/status` requires `observe` capability and `/miner/*` requires `control`. In reality, `daemon.py` performs zero authentication. The GatewayHandler checks no tokens, no headers, no capabilities. All auth lives in the CLI layer only. Any process on the LAN can POST `/miner/start` directly via curl.

This is not just a docs bug — it creates a false security model that operators will trust.

### C5. Gateway URL Fabrication

Both `docs/operator-quickstart.md:155` and `docs/contributor-guide.md:105` reference:
```
http://localhost:8080/apps/zend-home-gateway/index.html
```

The daemon does not serve static files. It returns 404 for any path not in `{/health, /status, /miner/*}`. The gateway HTML is a local file meant to be opened with `file://` or served by a separate mechanism.

### C6. Test Suite Claims Without Tests

README.md:106 and contributor-guide.md:31 both instruct:
```
python3 -m pytest services/home-miner-daemon/ -v
```

No test files exist under `services/home-miner-daemon/`. This command will discover zero tests or error. Acceptance criterion 2 (contributor can run test suite) fails.

### C7. Dead Reference in Contributor Guide

contributor-guide.md:276 references `docs/design-checklist.md`. This file does not exist.

---

## Milestone Fit

| Acceptance Criterion (from spec) | Pass? | Reason |
|---|---|---|
| Quickstart works clone→`{"status":"ok"}` in <10 min | **FAIL** | Step 5 unauthorized; pytest finds no tests |
| Contributor guide enables test execution | **FAIL** | No tests exist |
| Operator guide covers full deployment | **PARTIAL** | Gateway URL incorrect; auth model misleading |
| API curl examples all work | **FAIL** | 2 ghost endpoints return 404 |
| Architecture doc correct | **FAIL** | Doc missing entirely |

---

## Nemesis Security Review

### Pass 1 — Trust Boundaries & Authority Assumptions

**S1. No HTTP authentication (CRITICAL)**

The daemon exposes `/miner/start`, `/miner/stop`, `/miner/set_mode` with zero authentication. The capability model (`has_capability` in store.py) is checked only by the CLI, which is a local process that then calls the daemon over HTTP. Any device on the LAN can control the miner by curling the daemon directly.

The documentation describes capability-scoped access on HTTP endpoints. This is fiction. An operator reading the docs would believe that unpaired devices cannot control the miner. They can.

**Recommendation**: Either implement HTTP-level auth (bearer token derived from pairing token) or prominently document that the daemon has no auth and relies entirely on network isolation.

**S2. Token expiry is immediate and unchecked**

`store.py:88-89`:
```python
token = str(uuid.uuid4())
expires = datetime.now(timezone.utc).isoformat()  # expires NOW
```

Every pairing token expires at creation time. No code ever checks `token_expires_at`. The documented `/pairing/refresh` endpoint doesn't exist. The token concept is dead code — it exists in the data model but has no runtime effect.

**S3. No CORS headers**

The daemon sets no CORS headers. In a LAN deployment, a malicious website opened in any browser on the network could make cross-origin requests to the daemon and control the miner. Since there's no auth, there's no defense.

**S4. State file permissions**

`principal.json` and `pairing-store.json` are created with default umask. On a shared system (or a Pi with multiple users), other users can read the principal identity and all pairing records. These files should be created with 0600 permissions.

### Pass 2 — Coupled State & Consistency

**S5. Pairing store vs. spine split-brain**

`cmd_bootstrap` (cli.py:74-93) and `cmd_pair` (cli.py:98-128) perform two independent writes:
1. `pair_client()` → writes to `pairing-store.json` (full-file overwrite)
2. `spine.append_pairing_granted()` → appends to `event-spine.jsonl`

If the process dies between step 1 and step 2, the pairing exists in the store but no event was recorded. The spine (documented as "source of truth") disagrees with the store. There is no reconciliation path.

**S6. Pairing store is not crash-safe**

`save_pairings()` (store.py:80-83) does `json.dump` which truncates and rewrites the file. A crash or power loss during write corrupts all pairing records. Compare with the spine which is append-only and crash-tolerant by design. The store should use write-to-temp-then-rename.

**S7. Bootstrap is not idempotent**

`pair_client()` raises `ValueError("Device 'X' already paired")` if the device exists. Running `./scripts/bootstrap_home_miner.sh` twice fails on the second run (unless you `rm -rf state/*` first). The operator quickstart doesn't mention this. The spec says "idempotent and safe."

**S8. PID file race condition**

`bootstrap_home_miner.sh:47-57` reads a PID file and sends `kill`. Between reading the PID and sending the signal, the PID could be recycled by the OS. The script also sends `kill -9` after only 1 second, which doesn't give the Python process time for graceful shutdown. On a Pi under load, this is a real risk.

### Pass 3 — Functional Bugs Found During Review

**S9. CLI events filter crashes**

`cli.py:190` passes a raw string to `spine.get_events(kind=kind)`. Inside `get_events` (spine.py:87), the code does `e.kind == kind.value`. If `kind` is a plain string (not an `EventKind` enum), `.value` raises `AttributeError`. The documented command `cli.py events --kind pairing_granted` will crash.

---

## Remaining Blockers (Ordered by Priority)

| # | Blocker | Severity |
|---|---|---|
| 1 | Create `docs/architecture.md` | **Missing artifact** |
| 2 | Remove or label ghost endpoints (`/spine/events`, `/pairing/refresh`, `/metrics`) from docs | **Correctness** |
| 3 | Fix quickstart: bootstrap must grant `control` or step 5 must use `observe`-only commands | **Correctness** |
| 4 | Fix or remove gateway URL references (daemon doesn't serve static files) | **Correctness** |
| 5 | Remove pytest instructions or create actual tests | **Correctness** |
| 6 | Fix README architecture diagram (remove `/spine/*`, `/metrics`) | **Correctness** |
| 7 | Rewrite auth description — document that daemon has NO auth, only network isolation | **Security/Correctness** |
| 8 | Remove dead `docs/design-checklist.md` reference from contributor guide | **Correctness** |
| 9 | Fix `get_events` kind parameter bug (string vs EventKind) | **Functional bug** |
| 10 | Fix `create_pairing_token` expiry (expires at creation time) | **Security** |
| 11 | Make bootstrap idempotent (re-pair existing device instead of raising) | **Operator safety** |

---

## What's Good

The documentation *structure* is solid. The spec correctly identified the five deliverables. The three docs that exist are well-organized, have consistent formatting, and cover the right topics. The contributor guide's section on plan-driven development is a genuine value-add. The operator quickstart's troubleshooting table is practical.

The problem is not effort or organization — it's that the docs were written speculatively from the spec's endpoint table rather than verified against the running code. The fix is mechanical: run every curl example, remove what 404s, and correct what's wrong.
