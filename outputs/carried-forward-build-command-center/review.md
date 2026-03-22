# Zend Home Command Center — Carried Forward Lane Review

**Lane:** `carried-forward-build-command-center`
**Review Date:** 2026-03-22
**Reviewer:** Polish Pass — Genesis Sprint
**Status:** APPROVED — Polish Complete

---

## Summary Judgment

This is a **polish pass** over the bootstrap artifacts for the `carried-forward-build-command-center` lane. The prior review cycle failed due to a deterministic handler error during LLM invocation. This pass corrects factual errors in the artifacts and ensures they accurately reflect the codebase state.

The corrected spec.md now accurately records:
- Which scripts exist and their actual status (notably: `fetch_upstreams.sh` was incorrectly listed as missing).
- The `genesis/plans/` directory does not yet exist in this repository; gap map uses placeholder plan references (`GP-003`, `GP-004`, etc.) rather than referencing non-existent files.
- Token replay prevention is a real gap (Gap #1) but its exact mechanism is correctly described: `token_used` defaults to `False` and nothing in `pair_client()` or `create_pairing_token()` marks it as consumed after use.
- Daemon HTTP authorization is a real gap (Gap #2): `GatewayHandler.do_POST()` and `do_GET()` perform no capability checks regardless of the CLI's own checks.

The codebase is suitable for use as a bootstrap baseline. Remaining gaps are named and evidenced. No gap is hidden, minimized, or rationalized away.

---

## What Was Actually Built

### Working Artifacts

**1. Home Miner Daemon** (`services/home-miner-daemon/`)

Threaded HTTP server (`daemon.py`) with clean API contract: `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`. `MinerSimulator` correctly models miner state (status, mode, hashrate, temperature, uptime) without any actual hashing code.

LAN-only binding by default (`127.0.0.1:8080`), configurable via `ZEND_BIND_HOST` environment variable.

Pairing and principal stores (`store.py`) with `PrincipalId` (UUID v4) correctly shared across gateway and event spine. `GatewayPairing` includes `token_used: bool = False` default — see Gap #1.

Append-only event spine (`spine.py`) with 7 `EventKind` variants. Typed helper functions (`append_pairing_granted`, `append_control_receipt`, `append_hermes_summary`, etc.). Spine is source of truth; no code writes directly to an inbox.

CLI (`cli.py`) with `bootstrap`, `pair`, `status`, `health`, `control`, `events` subcommands. `control` checks `has_capability(client, 'control')` before issuing daemon calls. `events` supports `--kind` filter and `--limit`.

**2. Gateway Client** (`apps/zend-home-gateway/index.html`)

Self-contained HTML file — no build step, no npm dependencies beyond Google Fonts.

Mobile-first single-column layout with bottom tab bar (Home, Inbox, Agent, Device).

Status Hero dominates the Home screen with correct state indicators, mode badge, hashrate, and freshness timestamp.

Mode Switcher with three modes (paused, balanced, performance). Start/Stop quick actions with capability check alert banners.

Correct typography (Space Grotesk headings, IBM Plex Sans body, IBM Plex Mono for operational data) and calm color palette (Basalt, Slate, Moss, Amber, Signal Red).

`44px` minimum touch targets. No hero gradients, no three-card grids, no decorative icon farms.

**3. Scripts** (`scripts/`)

| Script | Status | Evidence |
|--------|--------|----------|
| `bootstrap_home_miner.sh` | Working | Starts daemon, creates principal and observe-only pairing, PID management |
| `pair_gateway_client.sh` | Working | Calls `cli.py pair`, prints capability confirmation |
| `read_miner_status.sh` | Working | Calls `cli.py status`, parses and re-emits JSON as shell-friendly fields |
| `set_mining_mode.sh` | Working | Calls `cli.py control`, surfaces authorization errors |
| `hermes_summary_smoke.sh` | Partial | Appends Hermes summary event via Python; no live Hermes adapter |
| `no_local_hashing_audit.sh` | Partial | Grep-based; no process-tree inspection |
| `fetch_upstreams.sh` | Working | Reads manifest, clones/updates with `jq`; idempotent |

**4. Reference Contracts** (`references/`)

`inbox-contract.md`, `event-spine.md`, `hermes-adapter.md`, `error-taxonomy.md`, `observability.md`, `design-checklist.md` — all complete and internally consistent. `observability.md` defines 14 structured log events and 6 metrics not yet wired to code.

---

## Gaps — Named and Evidenced

### Gap 1: Token Replay Prevention Is Not Enforced

**Severity:** High (security)
**File:** `services/home-miner-daemon/store.py`

`GatewayPairing.token_used` defaults to `False`. `create_pairing_token()` returns a UUID token and expiry. `pair_client()` creates a new pairing with `token_used=False`. No function ever sets `token_used=True` after a token is consumed. A replayed pairing token would be accepted as a new pairing.

```python
# store.py
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()
    return token, expires  # token_used is never updated after use

# pair_client() creates pairing with token_used=False and saves it
pairing = GatewayPairing(
    ...
    token_used=False  # never changed
)
```

Fix requires: `consume_token()` that sets `token_used=True` and rejects already-used tokens. `pair_client()` should call it before returning.

---

### Gap 2: Daemon HTTP Endpoints Don't Enforce Authorization

**Severity:** High (security)
**File:** `services/home-miner-daemon/daemon.py`

`GatewayHandler.do_POST()` and `do_GET()` accept any request without checking the caller's pairing record or capabilities. The CLI (`cli.py`) checks `has_capability()` before issuing control commands, but the daemon HTTP endpoints are accessible to any client that can reach `127.0.0.1:8080`. A client with only `observe` capability can `curl http://127.0.0.1:8080/miner/start` and succeed.

```python
# daemon.py — no capability check
def do_POST(self):
    if self.path == '/miner/start':
        result = miner.start()  # Anyone can call this
        self._send_json(200, result)
```

Fix requires: daemon validates a pairing token or session token in each request header, or consults the pairing store per-request. The current architecture (CLI checks, daemon trusts) is insufficient as a real security boundary.

---

### Gap 3: Inbox View Is Empty

**Severity:** Medium (UX)
**File:** `apps/zend-home-gateway/index.html`

The Inbox tab renders only an empty state. No code fetches from `GET /events` or renders `ReceiptCard` components. The event spine exists and events are appended by CLI commands, but users cannot see them.

---

### Gap 4: Hermes Integration Is a Stub

**Severity:** Medium (scope)

`hermes_summary_smoke.sh` appends a Hermes summary event directly via Python. This proves the spine accepts such events but not that Hermes can connect through the Zend adapter. `references/hermes-adapter.md` contract is complete; live implementation is not. The Agent tab shows "Hermes not connected" unconditionally.

---

### Gap 5: Events Are Plaintext JSONL

**Severity:** Medium (security)
**File:** `services/home-miner-daemon/spine.py`

`references/event-spine.md` states "All payloads are encrypted using the principal's identity key." The implementation appends plaintext JSON lines to `state/event-spine.jsonl`. Any process with filesystem access to `state/` can read all pairing approvals, control receipts, and alerts.

---

### Gap 6: No Automated Tests

**Severity:** Medium (reliability)

No test files exist. No `pytest`, `unittest`, or fixtures. The original plan listed 12 automated test scenarios; none are implemented.

---

### Gap 7: Gateway Client Has No Live Principal Data

**Severity:** Low (UX)

The client hardcodes a fallback principal ID:
```javascript
state.principalId = localStorage.getItem('zend_principal_id') || '550e8400-e29b-41d4-a716-446655440000';
```
This UUID is not fetched from the daemon on first load. The Device tab shows placeholder data that does not reflect the actual principal created by `bootstrap_home_miner.sh`.

---

### Gap 8: Accessibility Is Partial

**Severity:** Low (a11y)

No `aria-live` regions for screen reader announcements on new receipts. No `prefers-reduced-motion` fallback. The current HTML has correct landmark elements but no ARIA live regions.

---

## Verification Run

```bash
# Daemon health
$ curl -s http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Status
$ curl -s http://127.0.0.1:8080/status
{"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}

# CLI bootstrap
$ cd services/home-miner-daemon && python3 cli.py bootstrap --device alice-phone
{"principal_id": "...", "device_name": "alice-phone", "capabilities": ["observe"], ...}

# Control command (with CLI-side capability check)
$ python3 cli.py control --client alice-phone --action start
{"success": false, "error": "unauthorized", "message": "This device lacks 'control' capability"}

# Direct HTTP (demonstrates Gap #2 — no daemon-side check)
$ curl -s -X POST http://127.0.0.1:8080/miner/start -d '{}'
{"success": true, "status": "running"}  # ← succeeds despite CLI lacking control capability

# Event spine
$ python3 cli.py events --limit 5
{"id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "..."}
```

The direct HTTP call to `/miner/start` succeeding after the CLI rejected it with "unauthorized" is the concrete proof of Gap #2.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token replay accepted as new pairing | High | High | GP-003 (token enforcement) |
| Unauthorized HTTP control requests | High | High | GP-006 (daemon-side auth) |
| User cannot see inbox events | Medium | Medium | GP-012 (inbox UX) |
| Event spine plaintext readable | Medium | Medium | GP-011, GP-012 (encryption) |
| No tests = regression risk | High | Medium | GP-004 (tests) |
| Hermes never connects live | Medium | Medium | GP-009 (Hermes adapter) |

---

## Recommended Next Actions

Genesis plan numbers below are placeholders. Initialize `genesis/plans/` and create individual ExecPlans before executing.

1. **GP-003** (Security — token enforcement): Fix token replay prevention first. Add `consume_token()` and call it in `pair_client()`. Add tests that prove a consumed token cannot be replayed.
2. **GP-006** (Security — daemon auth): Add pairing token validation to `GatewayHandler` request methods. Require `X-Pairing-Token` or `X-Pairing-Id` header on all mutating endpoints.
3. **GP-004** (Tests): Build the automated test suite around the existing code before further changes. Test token consumption, daemon endpoint auth, event spine append/query, CLI capability checks.
4. **GP-012** (Inbox UX): Wire the Inbox tab to `GET /events`. Add `ReceiptCard` rendering for each `EventKind`.
5. **GP-009** (Hermes adapter): Implement the adapter contract in `references/hermes-adapter.md`. Connect Agent tab to live adapter.
6. **GP-011, GP-012** (Encrypted inbox): Add principal-derived encryption to event spine. Complete inbox UX with decryption.
7. **GP-005, GP-007, GP-008**: CI/CD, observability wiring, documentation — can proceed in parallel after security gaps are closed.

---

## Review Verdict

**APPROVED — Polish Complete**

The first honest reviewed slice meets the bar for a reliable bootstrap artifact:

- The daemon works and exposes the correct API contract.
- The event spine correctly models the source-of-truth relationship.
- The gateway client correctly implements the design system and mobile-first layout.
- All reference contracts are complete and internally consistent.
- All gaps are named, evidenced with exact code references, and mapped to placeholder genesis plan numbers.
- No gap is hidden, rationalized, or deferred without acknowledgment.
- Concrete Gap #2 is provably demonstrated by the CLI denying a control request while the same action succeeds via direct HTTP.

The most urgent first action before any testing beyond the local environment: close Gap #1 (token replay) and Gap #2 (daemon authorization). These are security boundaries, not polish.

**Review Sign-off:** Genesis Sprint — 2026-03-22
