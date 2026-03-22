# Zend Home Command Center — Carried Forward Lane Review

**Lane:** `carried-forward-build-command-center`
**Review Date:** 2026-03-22
**Reviewer:** Genesis Sprint
**Status:** APPROVED — Bootstrap Complete

---

## Summary Judgment

The first honest reviewed slice of the Zend Home Command Center is **approved as a bootstrap artifact**. The codebase contains a working daemon, a paired client CLI, an event spine, and a mobile-shaped gateway client. The reference contracts are complete. The design system is correctly applied.

The remaining gaps are real and named. They are addressed by genesis plans 002–014, which decompose the remaining work into manageable, verifiable streams. No gap is hidden, minimized, or explained away.

---

## What Was Actually Built

### Working Artifacts

**1. Home Miner Daemon**
- Threaded HTTP server (`daemon.py`) with clean API contract: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`.
- `MinerSimulator` correctly models miner state (status, mode, hashrate, uptime, freshness) without any actual hashing.
- LAN-only binding by default (`127.0.0.1:8080`).
- Pairing and principal stores (`store.py`) with `PrincipalId` (UUID v4) correctly shared across gateway and event spine.
- Append-only event spine (`spine.py`) with 7 `EventKind` variants.
- CLI with `bootstrap`, `pair`, `status`, `control`, `events` subcommands.

**2. Gateway Client**
- Self-contained `index.html` — no build step, no dependencies beyond Google Fonts.
- Mobile-first single-column layout with bottom tab bar.
- Status Hero dominates the Home screen with correct state indicators.
- Mode Switcher with three modes (paused, balanced, performance).
- Start/Stop quick actions with capability checks.
- Alert banners for unauthorized actions.
- Correct typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono) and calm color palette.
- `44px` minimum touch targets.
- No crypto-dashboard aesthetics, no hero gradients, no three-card grids.

**3. Scripts**
- `bootstrap_home_miner.sh`: Complete with PID management, daemon startup, principal creation.
- `pair_gateway_client.sh`: Working pairing with capability output.
- `read_miner_status.sh`: Parses daemon output, re-emits shell-friendly fields.
- `set_mining_mode.sh`: Capability check, acknowledgment output, error handling.
- `hermes_summary_smoke.sh`: Appends a Hermes summary event to the spine.
- `no_local_hashing_audit.sh`: Grep-based audit stub.

**4. Reference Contracts**
- `inbox-contract.md`, `event-spine.md`, `hermes-adapter.md`, `error-taxonomy.md`, `observability.md`, `design-checklist.md` — all complete and internally consistent.

---

## Honest Gaps and Issues

### Gap 1: Token Replay Prevention Is Not Enforced
**Severity:** High (security)
**File:** `services/home-miner-daemon/store.py`

The `GatewayPairing` dataclass defines `token_used: bool = False`. The `create_pairing_token()` function generates tokens. But nothing in the codebase sets `token_used` to `True` after a token is consumed. A replayed pairing token would be accepted as a new pairing.

This is the most concrete security gap in the current codebase. It must be addressed before any production use.

**Evidence:**
```python
# store.py, create_pairing_token()
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()
    return token, expires  # token_used is never updated
```

**Fix:** `pair_client()` should mark the token as used before returning. A new `consume_token()` function should check `token_used` before creating a pairing.

---

### Gap 2: Daemon HTTP Endpoints Don't Enforce Authorization
**Severity:** High (security)
**File:** `services/home-miner-daemon/daemon.py`

The CLI (`cli.py`) checks `has_capability()` before issuing control commands. But the HTTP endpoints in `GatewayHandler` accept any request without checking the client's pairing record or capabilities. A client with only `observe` could directly `curl` the daemon's `/miner/start` endpoint and succeed.

**Evidence:**
```python
# daemon.py, GatewayHandler.do_POST()
def do_POST(self):
    # No capability check here
    if self.path == '/miner/start':
        result = miner.start()  # Anyone can call this
```

**Fix:** The daemon needs to validate a capability token in each request header, or the pairing store needs to be consulted per-request. The current architecture (CLI checks, daemon trusts) is insufficient for a real security boundary.

---

### Gap 3: The Inbox View Is Empty
**Severity:** Medium (UX)
**File:** `apps/zend-home-gateway/index.html`

The Inbox tab renders only an empty state:
```javascript
// screen-inbox div contains only:
<div class="empty-state">
    <div class="empty-state__icon">📬</div>
    <div class="empty-state__text">No messages yet</div>
</div>
```

No code fetches events from the daemon's `/events` endpoint or displays them. The event spine exists and events are being appended, but the user cannot see them.

**Fix:** The Inbox tab needs to fetch from `GET /events` (or a new `GET /inbox` endpoint) and render `ReceiptCard` components for each event kind.

---

### Gap 4: Hermes Integration Is a Stub
**Severity:** Medium (scope)
**File:** `scripts/hermes_summary_smoke.sh`, `apps/zend-home-gateway/index.html`

`hermes_summary_smoke.sh` appends a Hermes summary event directly via Python:
```bash
python3 -c "
from store import load_or_create_principal
from spine import append_hermes_summary
principal = load_or_create_principal()
event = append_hermes_summary('...', ['observe'], principal.id)
"
```

This proves the spine accepts Hermes summary events, but it does not prove Hermes can connect through the Zend adapter. The `references/hermes-adapter.md` contract is complete; the live implementation is not.

The Agent tab in the gateway client shows "Hermes not connected" unconditionally.

---

### Gap 5: Events Are Plaintext JSONL
**Severity:** Medium (security)
**File:** `services/home-miner-daemon/spine.py`

The event spine appends plaintext JSON lines to `state/event-spine.jsonl`. The contract in `references/event-spine.md` states "All payloads are encrypted using the principal's identity key," but no encryption is implemented. Any process with filesystem access to the `state/` directory can read all pairing approvals, control receipts, and alerts.

**Fix:** Event payloads should be encrypted with a principal-derived key before writing to the JSONL file. This is deferred to genesis plans 011/012.

---

### Gap 6: No Structured Logging or Metrics
**Severity:** Low (observability)
**File:** All daemon and script files

`references/observability.md` defines 14 structured log events and 6 metrics. None are wired to the code. All output goes to `print()` or is suppressed. There is no way to distinguish `gateway.status.read` from `gateway.status.stale` in production logs.

---

### Gap 7: No Automated Tests
**Severity:** Medium (reliability)
**File:** None

No test files exist in the repository. There is no `pytest`, no `unittest`, no test fixtures. The plan lists 12 automated test scenarios; none are implemented.

This is the most significant gap for long-term reliability. Genesis plan 004 addresses this.

---

### Gap 8: `fetch_upstreams.sh` Does Not Exist
**Severity:** Low (workflow)
**File:** Missing

The plan specifies `scripts/fetch_upstreams.sh`. It is not present. The upstream manifest (`upstream/manifest.lock.json`) exists but has never been used.

---

### Gap 9: Gateway Client Has No Live Principal Data
**Severity:** Low (UX)
**File:** `apps/zend-home-gateway/index.html`

The client hardcodes:
```javascript
state.principalId = localStorage.getItem('zend_principal_id') || '550e8400-e29b-41d4-a716-446655440000';
```

This default UUID is not fetched from the daemon. The Device tab shows a placeholder principal ID that doesn't match what `bootstrap_home_miner.sh` actually creates.

---

### Gap 10: Accessibility Is Partial
**Severity:** Low (a11y)
**File:** `apps/zend-home-gateway/index.html`

The design checklist specifies `aria-live` regions, `prefers-reduced-motion` fallback, and screen-reader landmarks. None are implemented. The current HTML has correct landmark elements but no ARIA live regions for new receipts.

---

## Verification Run

The following commands were executed to verify the current state:

```bash
# Daemon health
$ curl -s http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Status
$ curl -s http://127.0.0.1:8080/status
{"status": "stopped", "mode": "paused", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-22T..."}

# CLI bootstrap (after daemon started)
$ cd services/home-miner-daemon && python3 cli.py bootstrap --device alice-phone
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}

# Control command (with capability check)
$ python3 cli.py control --client alice-phone --action start
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}

# Event spine
$ python3 cli.py events --limit 5
{"id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "..."}
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token replay accepted as new pairing | High | High | Genesis plan 003 (token enforcement) |
| Unauthorized HTTP control requests | High | High | Genesis plan 006 (daemon-side auth) |
| User can't see inbox events | Medium | Medium | Genesis plan 012 (inbox UX) |
| Event spine plaintext readable | Medium | Medium | Genesis plans 011/012 (encryption) |
| No tests = regression risk | High | Medium | Genesis plan 004 (tests) |
| Hermes never connects live | Medium | Medium | Genesis plan 009 (Hermes adapter) |

---

## What Should Happen Next

The genesis plan decomposition (plans 002–014) should proceed in this recommended order:

1. **Plan 003** (Security hardening): Fix token replay prevention first. This is the most concrete security gap.
2. **Plan 006** (Token enforcement): Add daemon-side capability checks to HTTP endpoints.
3. **Plan 004** (Automated tests): Build the test suite around the existing code before further changes break things.
4. **Plan 012** (Inbox UX): Wire the Inbox tab to the event spine. This gives users visible value.
5. **Plan 009** (Hermes adapter): Implement the adapter contract. Agent integration is the next product differentiator.
6. **Plans 011/012** (Encrypted inbox): Add encryption to the event spine and complete the inbox UX.
7. **Plans 005/007/008**: CI/CD, observability, documentation — these are infrastructure and can proceed in parallel.

---

## Review Verdict

**APPROVED — Bootstrap Complete**

The first honest reviewed slice meets the bar for a reliable bootstrap artifact:

- The daemon works and exposes the correct API contract.
- The event spine correctly models the source-of-truth relationship.
- The gateway client correctly implements the design system and mobile-first layout.
- All reference contracts are complete and internally consistent.
- All gaps are named, evidenced, and mapped to genesis plans.
- No gap is hidden, rationalized, or deferred without acknowledgment.

The codebase is ready for genesis plan execution. The most urgent first action is addressing the token replay and daemon authorization gaps (plans 003 and 006) before any testing beyond the local environment.

**Review Sign-off:** Genesis Sprint — 2026-03-22
