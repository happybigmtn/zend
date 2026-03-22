# Zend Home Command Center — Nemesis Review

**Lane:** `carried-forward-build-command-center`
**Date:** 2026-03-22
**Reviewer:** Nemesis-style adversarial review (Opus 4.6)
**Prior Review:** Genesis Sprint Review (MiniMax-M2.7)

## Executive Summary

The prior review correctly identified surface gaps (token replay, no tests, Hermes adapter deferred) but understated the security posture. The capability model (observe vs control) is **not enforced** — it exists only in the CLI layer while the daemon HTTP API and gateway client bypass it entirely. The token-based pairing ceremony described in the contracts does not exist in the implementation. The event spine claims encryption it does not perform.

The architecture is sound. The design system is well-executed. The codebase is clean and readable. But the security boundary between "can observe" and "can control" is decorative, and the trust ceremony is vestigial.

**Overall Assessment:** Working demo with correct architecture, but the security model is not implemented — it is only sketched. The prior review's "Capability scoping: Implemented" is incorrect.

## Prior Review Corrections

The MiniMax-M2.7 review made these assessments that need correction:

| Prior Claim | Correction |
|-------------|------------|
| "Capability scoping: Implemented" | **Wrong.** Enforced in CLI only. Daemon HTTP API has zero auth. Gateway client hardcodes `['observe', 'control']`. |
| "Token replay prevention: Missing" | **Understated.** The token concept itself is vestigial — no token is issued, stored, or exchanged. `create_pairing_token()` generates a UUID that is immediately discarded. |
| "Token expiration: stored but never checked" | **Understated.** `token_expires_at` is set to `datetime.now()` — every token is born expired. Both the generation and the enforcement are broken. |
| "Overall Security: Adequate for prototype" | **Disagree.** Any localhost process can stop the miner. The demo path (gateway → daemon) has zero access control. "Adequate for prototype" implies the security model works but needs hardening — it does not work at all. |
| "Input validation: Basic" | **Incomplete.** The daemon validates JSON and mode enums, but `hermes_summary_smoke.sh` has a shell injection vector via unescaped Python string interpolation. |

## Pass 1 — First-Principles Challenge

### F1. Daemon has zero authentication (HIGH)

The daemon (`services/home-miner-daemon/daemon.py`) serves `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` with no authentication. No tokens, no headers, no capability checks.

The capability system in `store.py:has_capability` is checked only in `cli.py`. The gateway client (`apps/zend-home-gateway/index.html`) calls the daemon directly via `fetch()` with no credentials.

**Attack:** Any process on the same machine can `curl -X POST http://127.0.0.1:8080/miner/stop` and halt mining. The observe/control distinction does not exist at the API boundary.

**Evidence:** `daemon.py:168-200` — `do_GET` and `do_POST` have no auth checks.

### F2. Token lifecycle is completely broken (HIGH)

Three distinct bugs in `store.py:86-119`:

1. `create_pairing_token()` sets `expires = datetime.now()` — tokens are born expired (line 89)
2. The generated token UUID is never stored in `GatewayPairing` — there is no `token` field in the dataclass (line 41-49)
3. `token_used` is never set to `True` anywhere in the codebase

The pairing flow is: "register a device name, get capabilities." No challenge-response, no token exchange, no bearer credential. The contract's token model is not implemented.

**Evidence:** `store.py:86-91`, `store.py:41-49`

### F3. Gateway client hardcodes capabilities (HIGH)

`index.html:626`: `capabilities: ['observe', 'control']` is a hardcoded array. It is never fetched from the daemon or validated against the pairing record. Combined with F1, an observe-only paired device has full control in the browser.

**Evidence:** `index.html:626-628`

### F4. Shell injection in hermes_summary_smoke.sh (MEDIUM)

`scripts/hermes_summary_smoke.sh:45-55` interpolates `$SUMMARY_TEXT` directly into a Python string literal:
```bash
python3 -c "
...
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
..."
```

A summary containing a single quote breaks the Python string and allows arbitrary code execution.

**Evidence:** `hermes_summary_smoke.sh:51`

### F5. CORS prevents gateway→daemon communication (MEDIUM)

The daemon sends no `Access-Control-Allow-Origin` headers. The gateway client uses `fetch('http://127.0.0.1:8080/...')`. If `index.html` is opened from `file://` or a different origin, CORS blocks all requests. The demo path is broken in standards-compliant browsers.

**Evidence:** `daemon.py:162-166` — `_send_json` sends `Content-Type` only, no CORS headers.

### F6. LAN-only is advisory, not enforced (MEDIUM)

`ZEND_BIND_HOST` env var overrides the default `127.0.0.1` binding. No validation rejects non-private IP addresses. No firewall rules or network checks exist. A single env var misconfiguration exposes the unauthenticated daemon to the network.

**Evidence:** `daemon.py:34`

### F7. No-local-hashing audit is security theater (LOW)

`scripts/no_local_hashing_audit.sh:60` greps Python source for `def.*hash`. This checks source code, not runtime behavior. The `--client` argument is accepted but unused. The audit proves nothing about actual hashing activity.

**Evidence:** `no_local_hashing_audit.sh:48-63`

### F8. PID file race condition (LOW)

`scripts/bootstrap_home_miner.sh:62-68` — TOCTOU race between checking if PID is alive and writing new PID. Concurrent bootstrap invocations can start duplicate daemons.

**Evidence:** `bootstrap_home_miner.sh:62-68`

## Pass 2 — Coupled-State Review

### F9. Pairing store and event spine diverge silently (MEDIUM)

`cli.py:cmd_pair` writes to `pairing-store.json` first, then appends `pairing_requested` and `pairing_granted` to the event spine. No transaction boundary — if the spine write fails, the pairing exists without an audit trail.

`cli.py:cmd_bootstrap` creates a pairing and emits `pairing_granted` but never emits `pairing_requested`. The bootstrap device's grant has no corresponding request in the audit trail.

**Evidence:** `cli.py:73-95` (bootstrap), `cli.py:98-129` (pair)

### F10. Event spine claims encryption it does not have (MEDIUM)

`references/event-spine.md:109` states: "All payloads are encrypted using the principal's identity key." The implementation (`spine.py`) writes plaintext JSON. The spec document is dishonest about the current state.

**Evidence:** `spine.py:62-65`, `references/event-spine.md:109`

### F11. EventKind type error in CLI events command (LOW)

`cli.py:190-191` passes a raw string to `spine.get_events(kind=...)`, which expects `Optional[EventKind]`. Inside `spine.py:87`, `kind.value` is called on the string, which raises `AttributeError`. The `--kind` filter is broken for any value except the default `all`.

**Evidence:** `cli.py:190-191`, `spine.py:87`

### F12. Miner state is memory-only — audit trail diverges on restart (LOW)

`MinerSimulator` state lives in a Python object. Daemon restart resets to stopped/paused. The event spine retains `control_receipt(start, accepted)` from before the restart. Post-restart, the audit trail says "running" but the miner is stopped.

**Evidence:** `daemon.py:51-69`

### F13. Control receipts lack device attribution (LOW)

`cli.py:cmd_control:142` uses `load_or_create_principal()` for the event's `principal_id`. The event spine records which principal authorized the action but not which device issued it. With multiple paired devices, the audit trail cannot distinguish who acted.

**Evidence:** `cli.py:142`, `cli.py:157`

### F14. File-based store has no locking (LOW)

`store.py:save_pairings` and `spine.py:_save_event` have no file locking. Concurrent writes can corrupt `pairing-store.json` or interleave `event-spine.jsonl` entries.

**Evidence:** `store.py:80-83`, `spine.py:62-65`

## Design System Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Typography (3 fonts) | PASS | All fonts loaded and applied correctly |
| Color palette (DESIGN.md) | DRIFT | `index.html` uses warm stone palette (`#FAFAF9`, `#1C1917`) not `DESIGN.md`'s Basalt/Slate/Mist (`#16181B`, `#23272D`, `#EEF1F4`). The aesthetic is correct but the exact hex values diverge from the spec. |
| Mobile-first layout | PASS | Single column, max-width 420px |
| Bottom tab navigation | PASS | 4 tabs in correct order (Home, Inbox, Agent, Device) |
| Status Hero | PASS | State indicator, value, meta row |
| Mode Switcher | PASS | 3-mode segmented control |
| Receipt Card | PASS | Component exists, styled correctly |
| Loading states | PARTIAL | Skeleton CSS exists but no loading state is triggered in JS |
| Empty states | PASS | Warm copy with contextual icons |
| Error banners | PASS | AlertBanner with auto-dismiss |
| Touch targets 44x44 | PASS | Applied to nav and buttons |
| prefers-reduced-motion | FAIL | Not implemented — DESIGN.md requires it |
| WCAG AA contrast | PASS | Color choices tested |
| Screen reader landmarks | FAIL | No ARIA landmarks for Home, Inbox, Agent, Device sections |

## Gap Analysis: What the Prior Review Missed

| Gap | Category | Prior Review |
|-----|----------|-------------|
| Daemon has zero auth | Security | Not mentioned |
| Gateway hardcodes capabilities | Security | Not mentioned |
| Shell injection in hermes_summary_smoke.sh | Security | Not mentioned |
| CORS blocks gateway→daemon | Functionality | Not mentioned |
| Color palette drifts from DESIGN.md | Design | Not mentioned |
| Bootstrap skips pairing_requested event | Consistency | Not mentioned |
| EventKind type error crashes --kind filter | Bug | Not mentioned |
| Loading states never trigger in JS | Design | Not mentioned |
| No ARIA landmarks | Accessibility | Not mentioned |
| Token is never issued or stored | Security | Partially noted (replay) but root cause missed |

## Severity Summary

| Severity | Count | Findings |
|----------|-------|----------|
| HIGH | 3 | F1 (daemon no auth), F2 (token lifecycle broken), F3 (hardcoded capabilities) |
| MEDIUM | 4 | F4 (shell injection), F5 (CORS), F6 (LAN advisory), F9 (store/spine divergence), F10 (encryption claim) |
| LOW | 5 | F7 (audit theater), F8 (PID race), F11 (EventKind type error), F12 (restart divergence), F13 (no device attribution), F14 (no file locking) |

## Recommendations (revised priority order)

### P0 — Before any other genesis plan

1. **Add daemon-level auth** — tokens or API keys on all mutation endpoints. The capability model must be enforced at the HTTP boundary, not just in the CLI. Without this, the observe/control distinction is fiction.

2. **Fix CORS** — add `Access-Control-Allow-Origin` for the gateway client origin. Without this, the gateway demo is broken in real browsers.

3. **Fix the spec** — `references/event-spine.md` must not claim encryption until encryption exists. Mark it as "plaintext in milestone 1, encrypted in milestone N."

### P1 — Genesis plan 003 (Security)

4. **Implement real token lifecycle** — add a `token` field to `GatewayPairing`, set expiration to future time, check both expiration and used-state before accepting pairing.

5. **Fix shell injection** — use `subprocess` with argument passing instead of string interpolation in `hermes_summary_smoke.sh`.

6. **Validate ZEND_BIND_HOST** — reject non-private IPs or at minimum warn when binding to a public interface.

### P2 — Genesis plan 004 (Tests)

7. **Test the HTTP API directly** — not just the CLI. Prove that an unauthorized client cannot issue control commands.

8. **Test store/spine consistency** — prove that a failed spine write doesn't leave orphaned pairings.

9. **Test EventKind filter** — fix the type error and add a regression test.

### P3 — Genesis plan 009 (Hermes) and beyond

10. **Bootstrap should emit pairing_requested** before pairing_granted for audit completeness.

11. **Add device_name to control receipts** in the event spine payload.

12. **Trigger loading states in the gateway JS** — the CSS exists but the JS never uses it.

## Sign-Off

| Review Area | Status | Confidence | Prior Review Said |
|------------|--------|------------|-------------------|
| Architecture | SOUND | High | Same |
| Design System | MOSTLY COMPLIANT | Medium | Said "Compliant" (missed color drift, ARIA, loading states) |
| Error Handling | PARTIAL | Medium | Same |
| Security | NOT ENFORCED | Low | Said "Basic" — understated |
| Test Coverage | NONE | Low | Same |
| Documentation | DISHONEST ON ENCRYPTION | Medium | Said "Complete" (missed spec/impl mismatch) |

**Recommendation:** Do not proceed to genesis plan 009 (Hermes) or 012 (Inbox) until daemon auth and CORS are fixed. The current architecture allows any localhost process to control the miner without credentials. Expanding the surface area before fixing the auth boundary makes the problem harder, not easier.
