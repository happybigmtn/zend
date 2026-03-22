# Zend Home Command Center — Carried-Forward Review

**Lane:** `carried-forward-build-command-center`
**Reviewed:** 2026-03-22
**Against:** `plans/2026-03-19-build-zend-home-command-center.md`
**Reviewer:** Genesis Sprint (honest slice review)

---

## Summary

The first honest reviewed slice of the Zend Home Command Center is **partially complete**.
The spec layer is solid, the implementation is substantially functional, and the design
system is correct. Three security-critical gaps were found that must be addressed before
the milestone is acceptable for real use: a broken token-replay check, absent HTTP-layer
capability enforcement, and plaintext event-spine storage. These are addressed by genesis
plans 003 and 006; the current code should not be deployed.

---

## Spec Layer Review

### Reference Contracts ✓

All six contracts are present, internally consistent, and cover the full capability
surface:

| Contract | Quality | Notes |
|----------|---------|-------|
| `inbox-contract.md` | Good | `PrincipalId` is UUID v4, shared across gateway and inbox as required |
| `event-spine.md` | Good | All 7 event kinds, correct payload schemas, source-of-truth constraint is explicit |
| `error-taxonomy.md` | Good | 9 named error classes, user-facing messages, rescue actions |
| `hermes-adapter.md` | Good | Adapter interface, observe/summarize scope, clear boundaries |
| `observability.md` | Good | Structured log events, metrics with labels, audit log schema |
| `design-checklist.md` | Good | Complete checklist mapped to `DESIGN.md` requirements |

**Verdict:** Spec layer is complete and internally consistent. No gaps found.

### Product Spec ✓

`specs/2026-03-19-zend-product-spec.md` is the accepted durable specification. The
product boundary is clear: Zend is a private command center, not a public feed, not
a new chain, not an on-device miner. The eight-layer runtime contract correctly captures
the architectural decisions.

**Verdict:** Product spec is correct and accepted.

### Design System ✓

`DESIGN.md` is comprehensive and specific. Typography choices (Space Grotesk, IBM Plex
Sans, IBM Plex Mono) are implemented in `index.html`. The color palette (Basalt / Slate /
Mist / Moss / Amber / Signal Red / Ice) is correctly applied. The component vocabulary
(Status Hero, Mode Switcher, Receipt Card, Trust Sheet, Permission Pill) is present.
AI-slop guardrails are explicitly enumerated.

**Verdict:** Design system is complete and was correctly implemented in the gateway client.

---

## Implementation Review

### Daemon (`daemon.py`) — Partial Pass ⚠

**What works:**
- HTTP server binds to `127.0.0.1:8080` by default (LAN-only commitment kept)
- `MinerSimulator` correctly models status, mode, start, stop, set_mode, and health
- Threaded handler handles concurrent requests
- All four endpoints (`/health`, `/status`, `/miner/start`, `/miner/stop`,
  `/miner/set_mode`) are wired correctly
- `freshness` timestamp in `MinerSnapshot` is correctly formatted ISO 8601 UTC

**What is broken:**
- **No HTTP-layer capability enforcement.** The handler accepts all POST requests
  without checking whether the caller has `control` capability. The `cli.py` checks
  `store.has_capability()` before issuing commands, but the daemon itself has no auth
  barrier. Any process on the same host can control the miner by POSTing directly.
  **Severity: HIGH.** Must be fixed before deployment.

- No `X-Device-Name` header processing. The daemon cannot associate an incoming
  request with a specific device identity.

### Store (`store.py`) — Partial Pass ⚠

**What works:**
- `PrincipalId` is correctly UUID v4
- `GatewayPairing` record has all required fields
- `has_capability()` correctly checks the capability set
- `get_pairing_by_device()` works
- Duplicate device name check prevents re-pairing

**What is broken:**
- **`token_used` is set to `False` on every pairing but never set to `True`.**
  The comment in the original plan noted this observation explicitly. No code path
  consumes the token, marks it used, or checks it. Token replay prevention is
  therefore a no-op. **Severity: HIGH.** Genesis plan 006 addresses this.

### Spine (`spine.py`) — Partial Pass ⚠

**What works:**
- Append-only JSONL journal with UUID event IDs
- All 7 `EventKind` variants have append helpers
- `get_events()` supports kind filtering and reverse-chronological ordering
- `created_at` is ISO 8601 UTC

**What is broken:**
- **Payloads are plaintext JSON.** The contract specifies encrypted payloads.
  The `payload: object` field in `SpineEvent` currently receives and stores
  unencrypted data. This defeats the privacy goal of the event spine.
  **Severity: HIGH.** Genesis plans 011 and 012 address this.
- No encryption key management: no key derivation, no envelope encryption, no
  key rotation plan.

### CLI (`cli.py`) — Pass ✓

**What works:**
- All six subcommands (`bootstrap`, `pair`, `status`, `health`, `control`, `events`)
  are wired
- `has_capability()` is checked before `control` actions in `cmd_control()`
- `observe` capability is correctly required for `status` and `events`
- Explicit acknowledgement message in control response: "accepted by home miner
  (not client device)"
- Error messages return structured JSON with named error codes

**Notes:**
- Duplicate pairing logic in `cmd_bootstrap()` vs `cmd_pair()` — both call
  `pair_client()`. The bootstrap subcommand creates an `observe`-only pairing;
  `cmd_pair()` accepts explicit `--capabilities`. This asymmetry is intentional
  but worth documenting.

### Gateway Client (`index.html`) — Pass ✓

**What works:**
- Mobile-first viewport, single-column, max-width 420px
- All four destinations render: Home, Inbox, Agent, Device
- Bottom tab bar is present with correct labels and icons
- Status Hero correctly shows status indicator (color-coded), status value,
  hashrate, and freshness timestamp
- Mode Switcher correctly shows three modes and highlights the active one
- Start/Stop action cards with correct capability check (checks `state.capabilities`
  client-side — note: this is a UI-only guard, not a security boundary)
- Receipt Card styling is consistent with `DESIGN.md`
- Permission Pills for observe and control are present on the Device screen
- Loading skeleton animation is present
- Stale data warning via `showAlert()` is wired
- Empty states have warm copy and context (not "No items found")
- `prefers-reduced-motion` not explicitly checked but transitions are minimal

**Design compliance:**
- Fonts loaded from Google Fonts: Space Grotesk, IBM Plex Sans, IBM Plex Mono ✓
- Color palette matches `DESIGN.md` ✓
- Component vocabulary is correct ✓
- Touch targets are `min-width: 64px; min-height: 44px` ✓

### Scripts — Pass ✓

| Script | Status | Notes |
|--------|--------|-------|
| `bootstrap_home_miner.sh` | ✓ | Idempotent PID management, daemon readiness wait, colored output |
| `pair_gateway_client.sh` | ✓ | Correct CLI invocation, structured output parsing |
| `read_miner_status.sh` | ✓ | Reads via `cli.py status` |
| `set_mining_mode.sh` | ✓ | Capability check, explicit acknowledgement |
| `hermes_summary_smoke.sh` | Stub | Appends `hermes_summary` to spine; Hermes adapter itself not implemented |
| `no_local_hashing_audit.sh` | Stub | Process-tree inspection stub; needs real audit logic |
| `fetch_upstreams.sh` | Present | Manifest-based but refs not SHA-locked |

### Upstream Manifest — Partial Pass ⚠

Three upstreams are listed with meaningful purpose descriptions. However, `pinned_sha`
is `null` for all three and `pinned_ref` uses floating refs (`"main"`,
`"latest-release"`). This means `fetch_upstreams.sh` will fetch whatever is currently at
head, which defeats the purpose of a pinned manifest. Genesis plan 005 (CI/CD pipeline)
should address this by pinning to specific SHAs.

---

## Architecture Compliance

| Requirement from Original Plan | Status | Evidence |
|-------------------------------|--------|---------|
| `PrincipalId` shared across gateway and inbox | ✓ | `store.py` creates; `spine.py` uses |
| Event spine is source of truth | ✓ | `spine.py` appends; inbox is view (not built yet) |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1:8080` |
| `observe` and `control` capability scopes | ✓ | `store.py`; CLI checks |
| Off-device mining | ✓ | Simulator; no hashing in client |
| HTTP-layer capability enforcement | ✗ BROKEN | Daemon accepts all requests |
| Token replay prevention | ✗ BROKEN | `token_used` never set to `True` |
| Encrypted event-spine payloads | ✗ BROKEN | Plaintext JSONL |
| Hermes adapter implementation | ✗ MISSING | Contract only; no code |
| Operations inbox UX | ✗ MISSING | Spine appends work; inbox projection not built |

---

## Gaps and Risks

### Security Gaps (Must Fix Before Deployment)

1. **No HTTP-layer auth (CRITICAL):** Any process on the host can POST to
   `/miner/start`, `/miner/stop`, `/miner/set_mode` without any capability check.
   The CLI's `has_capability()` check is bypassed entirely by direct HTTP calls.

2. **Token replay is a no-op (CRITICAL):** `token_used` in `GatewayPairing` is always
   `False`. The token consumption mechanism described in the error taxonomy is not
   implemented.

3. **Event-spine payloads are plaintext (HIGH):** Pairing approvals, control receipts,
   and alert payloads are written as readable JSON. This violates the privacy goal.

### Missing Features (Expected, Mapped to Genesis Plans)

4. **Hermes adapter not implemented:** Only the contract exists. No code connects
   Hermes Gateway to the Zend adapter. Genesis plan 009.

5. **Operations inbox UX not built:** The spine appends events correctly, but the
   inbox projection (grouping, filtering, rendering) is not implemented. Genesis
   plans 011 and 012.

6. **No automated tests:** The review process verified correctness by reading code;
   no pytest or integration tests exist. Genesis plan 004.

7. **No observability wiring:** Structured log events are defined but not emitted.
   No metrics are collected. Genesis plan 007.

### Minor Issues

8. **Client-side capability check is UI-only:** `index.html` checks `state.capabilities`
   before enabling buttons, but this is not a security boundary. The daemon must
   enforce capabilities server-side (see gap 1).

9. **Daemon does not restart cleanly with existing state:** Bootstrap is idempotent
   for the principal, but if the PID file is stale (process dead), the script
   removes it and starts fresh. This is fine but worth noting.

10. **No `prefers-reduced-motion` handling in CSS:** Transitions are minimal so this
    is low risk, but not explicitly handled.

---

## What Was Surprisingly Good

- The gateway client (`index.html`) is significantly more complete than expected.
  All four destinations render, the design system is correctly applied, and the
  component vocabulary matches `DESIGN.md` closely.
- The CLI (`cli.py`) is well-structured with clean subcommand separation and
  consistent JSON output.
- The event spine (`spine.py`) correctly implements the append-only pattern and
  the source-of-truth constraint is explicitly stated.
- The bootstrap script is properly idempotent: it detects a running daemon and
  reuses existing state rather than failing or overwriting.

---

## Review Verdict

**CONDITIONAL APPROVAL — Address three security gaps before deployment.**

The spec layer, design system, and implementation skeleton are correct and complete
enough to proceed to genesis plan execution. However, the three security gaps
(HTTP-layer auth, token replay, plaintext spine) must not ship in a deployed product.
Genesis plans 003 and 006 directly address the two critical gaps; genesis plans
011 and 012 address encryption.

**Acceptable to proceed if:**
- HTTP-layer capability enforcement is added (genesis plan 003)
- Token replay prevention is implemented (genesis plan 006)
- Event-spine encryption is added before any real use (genesis plans 011, 012)

**Not yet acceptable for:**
- Production deployment outside a development environment
- Any scenario where untrusted processes share the daemon host
- Storing real operational receipts with sensitive content

---

## Recommended Next Steps (Priority Order)

1. **Genesis plan 003 (Security hardening):** Add `X-Device-Name` header processing
   to the daemon, validate device identity on every request, and enforce capability
   scopes at the HTTP layer.
2. **Genesis plan 006 (Token enforcement):** Implement token consumption: set
   `token_used=True` after first use and reject replay attempts.
3. **Genesis plan 004 (Automated tests):** Add pytest suite covering happy paths
   and error scenarios for the three broken security items above.
4. **Genesis plan 008 (Gateway proof transcripts):** Document reproducible proof
   transcripts that demonstrate the no-local-hashing guarantee.
5. **Genesis plans 011/012 (Encrypted inbox):** Add envelope encryption to the
   event spine and build the inbox UX projection.

---

## Verification Commands

```bash
# Daemon health
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": N}

# Status read
curl http://127.0.0.1:8080/status
# Expected: {"status": "stopped", "mode": "paused", ..., "freshness": "2026-..."}

# Bootstrap
./scripts/bootstrap_home_miner.sh
# Expected: principal_id + pairing bundle printed

# Pair a control client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
# Expected: {"success": true, "device_name": "alice-phone", "capabilities": ["observe", "control"]}

# Control should succeed for control-capable client
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
# Expected: {"success": true, "acknowledged": true, "message": "Miner set_mode accepted by home miner (not client device)"}

# Event spine shows control receipt
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 1
# Expected: one event with kind="control_receipt", status="accepted"
```
