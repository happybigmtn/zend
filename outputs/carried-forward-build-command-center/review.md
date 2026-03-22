# Zend Home Command Center — Adversarial Review

**Lane:** `carried-forward-build-command-center`
**Date:** 2026-03-22
**Reviewer:** Nemesis-style adversarial review (Opus 4.6)
**Prior Review:** Genesis Sprint Review (MiniMax-M2.7-highspeed)

---

## Executive Summary

The prior review correctly identified surface gaps — missing tests, deferred Hermes adapter, token replay prevention absent — but materially understated the security posture. The capability model (observe vs. control) is **decorative, not enforced**: it exists in `store.py:has_capability` and `cli.py` but is entirely absent from the daemon HTTP API and the gateway client. Any process on the same machine can halt mining with a single `curl` command. The token-based pairing ceremony described in the contracts does not exist in the implementation. The event spine reference document claims encryption the code does not perform.

The architecture is sound. The design system is well-executed. The codebase is clean and readable. But the security boundary is a sketch, not a wall.

**Overall:** Working demo with correct architecture and design. The security model is not implemented — it is documented. Do not expand the attack surface (Hermes, inbox, remote access) before the auth boundary is real.

---

## Prior Review Corrections

The MiniMax-M2.7 review made several assessments that need correction:

| Prior Claim | Correction |
|-------------|------------|
| "Capability scoping: Implemented" | **Wrong.** Enforced in `cli.py` only. The daemon HTTP API (`daemon.py:168-200`) has zero auth. The gateway client (`index.html:626`) hardcodes `['observe', 'control']`. |
| "Token replay prevention: Missing" | **Understated.** The token concept is vestigial. `create_pairing_token()` generates a UUID that is never stored in `GatewayPairing`. `token_used` is never set. `token_expires_at` is set to `datetime.now()` — every token is born expired. |
| "Overall Security: Adequate for prototype" | **Disagree.** Any localhost process can stop the miner. The observe/control distinction does not exist at the HTTP boundary. "Adequate for prototype" implies a working model needing hardening; this model does not work at all. |
| "Input validation: Basic" | **Incomplete.** `hermes_summary_smoke.sh:51` interpolates `$SUMMARY_TEXT` directly into a Python string literal — a single quote enables arbitrary code execution. |
| "Design System: Compliant" | **Partially wrong.** Color palette uses warm stone (#FAFAF9, #1C1917) not DESIGN.md Basalt/Slate/Mist. `prefers-reduced-motion` not implemented. No ARIA landmarks. Loading states CSS exists but JS never triggers it. |

---

## Findings

### Security

#### F1 — Daemon has zero authentication [HIGH]

The daemon (`daemon.py:168-200`) serves all endpoints — `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` — with no authentication. No tokens, no headers, no capability checks.

The capability system in `store.py:has_capability` is checked only in `cli.py`. The gateway client calls the daemon directly via `fetch()` with no credentials.

**Attack:** Any process on the same machine can `curl -X POST http://127.0.0.1:8080/miner/stop` and halt mining.

**Source:** `daemon.py:168-200` (`do_GET`, `do_POST`); `store.py:107-110` (`has_capability`); `index.html` (fetch calls)

#### F2 — Token lifecycle is completely broken [HIGH]

Three distinct bugs in `store.py:86-119`:

1. `create_pairing_token()` sets `expires = datetime.now(timezone.utc)` — every token is expired at birth (line 89)
2. The generated token UUID is never stored in `GatewayPairing` — there is no `token` field assigned in the pairing dataclass (lines 41-49, 91-100)
3. `token_used` is never set to `True` anywhere in the codebase

The pairing flow is: "register a device name, receive capabilities." No challenge-response, no token exchange, no bearer credential. The contract's token model is not implemented at all.

**Source:** `store.py:86-91` (generation); `store.py:41-49` (dataclass); grep for `token_used` across codebase returns zero assignments

#### F3 — Gateway client hardcodes capabilities [HIGH]

`index.html:626`: `capabilities: ['observe', 'control']` is a hardcoded array. It is never fetched from the daemon or validated against the pairing record. Combined with F1, a device that should only be observe-only has full control in the browser.

**Source:** `index.html:626-628`

#### F4 — Shell injection in `hermes_summary_smoke.sh` [MEDIUM]

`scripts/hermes_summary_smoke.sh:45-55` interpolates `$SUMMARY_TEXT` and `$AUTHORITY_SCOPE` directly into a Python string literal:

```bash
python3 -c "
...
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
..."
```

A summary containing a single quote (`'`) breaks the Python string delimiter and enables arbitrary code execution.

**Source:** `hermes_summary_smoke.sh:51`

#### F5 — `ZEND_BIND_HOST` is advisory, not enforced [MEDIUM]

`daemon.py:34`: `BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')`. No validation rejects non-private IP addresses. A single environment variable misconfiguration exposes the unauthenticated daemon to the network.

**Source:** `daemon.py:34`

#### F6 — `no_local_hashing_audit.sh` is security theater [LOW]

`scripts/no_local_hashing_audit.sh:60` greps Python source for `def.*hash`. This checks source code, not runtime behavior. The `--client` argument is accepted but unused. The audit proves nothing about actual hashing activity.

**Source:** `no_local_hashing_audit.sh:48-63`

---

### Functionality

#### F7 — CORS prevents gateway→daemon communication [MEDIUM]

The daemon sends no `Access-Control-Allow-Origin` headers. The gateway client uses `fetch('http://127.0.0.1:8080/...')`. If `index.html` is opened from `file://` or a non-matching origin, CORS blocks all requests. The demo path is broken in standards-compliant browsers.

**Source:** `daemon.py:162-166` (`_send_json` sends `Content-Type` only); `index.html` fetch calls

#### F8 — `cmd_events --kind <value>` crashes on non-default kinds [LOW]

`cli.py:190-191` passes a raw string to `spine.get_events(kind=...)`, which expects `Optional[EventKind]`. Inside `spine.py:87`, `kind.value` is called on the string, which raises `AttributeError`. The `--kind` filter is broken for any value except `all` (the default).

**Source:** `cli.py:190-191`; `spine.py:87`

#### F9 — Bootstrap skips `pairing_requested` event [MEDIUM]

`cli.py:cmd_bootstrap` (lines 73-95) creates a pairing and emits `pairing_granted` but never emits `pairing_requested`. The bootstrap device's grant has no corresponding request in the audit trail.

**Source:** `cli.py:73-95`

#### F10 — Miner state resets on daemon restart [LOW]

`MinerSimulator` state lives in a Python object. Daemon restart resets to `stopped`/`paused`. The event spine retains `control_receipt(start, accepted)` from before the restart. Post-restart, the audit trail says "running" but the miner is stopped.

**Source:** `daemon.py:51-69` (in-memory state); `spine.py` (persistent events)

---

### Data Integrity

#### F11 — Control receipts lack device attribution [LOW]

`cli.py:cmd_control:142` uses `load_or_create_principal()` for the event's `principal_id`. The event spine records which principal authorized the action but not which device issued it. With multiple paired devices, the audit trail cannot distinguish who acted.

**Source:** `cli.py:142`, `cli.py:157`

#### F12 — No file locking on store or spine [LOW]

`store.py:save_pairings` and `spine.py:_save_event` have no file locking. Concurrent writes can corrupt `pairing-store.json` or interleave `event-spine.jsonl` entries.

**Source:** `store.py:80-83`; `spine.py:62-65`

---

### Documentation

#### F13 — Event spine spec claims encryption the code does not perform [MEDIUM]

`references/event-spine.md:109` states: "All payloads are encrypted using the principal's identity key." The implementation (`spine.py:62-65`) writes plaintext JSON. The spec is dishonest about the current state.

**Source:** `references/event-spine.md:109`; `spine.py:62-65`

---

## Design System Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Typography (3 fonts) | ✓ | Space Grotesk, IBM Plex Sans, IBM Plex Mono all loaded |
| Color palette (exact hex from DESIGN.md) | ✗ | Uses warm stone (#FAFAF9, #1C1917) not Basalt/Slate/Mist |
| Mobile-first layout | ✓ | Single column, max-width 420px |
| Bottom tab navigation | ✓ | Home, Inbox, Agent, Device in correct order |
| Status Hero component | ✓ | State indicator, value, meta row |
| Mode Switcher | ✓ | 3-mode segmented control |
| Receipt Card | ✓ | Timestamp + outcome, styled correctly |
| Loading states | partial | Skeleton CSS present; JS never triggers it |
| Empty states | ✓ | Warm copy with contextual icons |
| Error banners | ✓ | AlertBanner with auto-dismiss |
| Touch targets 44×44 | ✓ | Applied to nav and buttons |
| WCAG AA contrast | ✓ | Color choices tested |
| `prefers-reduced-motion` | ✗ | Not implemented |
| ARIA landmarks | ✗ | No landmarks for Home, Inbox, Agent, Device sections |

---

## Severity Summary

| Severity | Count | Findings |
|----------|-------|---------|
| HIGH | 3 | F1 daemon no auth, F2 token lifecycle broken, F3 hardcoded capabilities |
| MEDIUM | 4 | F4 shell injection, F5 LAN-only advisory, F7 CORS blocks demo, F9 bootstrap skips request event, F13 spec claims false encryption |
| LOW | 5 | F6 audit theater, F8 EventKind crash, F10 restart divergence, F11 no device attribution, F12 no file locking |

---

## Recommendations (Priority Order)

### P0 — Prerequisites (before any genesis plan)

1. **Add daemon-level auth** to all mutation endpoints. The capability model must be enforced at the HTTP boundary, not only in the CLI. Without this, the observe/control distinction is fiction.
2. **Add CORS headers** to `daemon.py:_send_json`. Without this, the gateway demo is broken in real browsers.
3. **Fix the event-spine spec** — remove the encryption claim until encryption is implemented. The spec must be honest about the current state.

### P1 — Genesis plan 003 (Security hardening)

4. **Implement real token lifecycle** — add a `token` field to `GatewayPairing`, set expiration to a future time, check both expiration and `used` state before accepting pairing.
5. **Fix shell injection** in `hermes_summary_smoke.sh` — use `subprocess.run` with argument passing instead of string interpolation.
6. **Validate `ZEND_BIND_HOST`** — reject or warn when binding to a non-private IP.

### P2 — Genesis plan 004 (Tests)

7. **Test the HTTP API directly** — not just the CLI. Prove that an unauthorized client cannot issue control commands.
8. **Test store/spine consistency** — prove that a failed spine write does not leave orphaned pairing records.
9. **Fix and regression-test the EventKind filter** — `spine.get_events` should accept either `EventKind` enum or string, not crash on string input.

### P3 — Genesis plans 009 and beyond

10. **Bootstrap should emit `pairing_requested` before `pairing_granted`** for complete audit trail.
11. **Add `device_name` to control receipt payload** in `spine.py:append_control_receipt`.
12. **Wire loading states in gateway JS** — the CSS skeleton exists but is never triggered.

---

## Sign-Off

| Area | Status | Confidence | Prior Review Said |
|------|--------|------------|-------------------|
| Architecture | SOUND | High | Same |
| Design System | MOSTLY COMPLIANT | Medium | "Compliant" — missed color drift, ARIA, loading-state wiring |
| Error Handling | PARTIAL | Medium | Same |
| Security | NOT ENFORCED | Low | "Basic" — understated |
| Test Coverage | NONE | Low | Same |
| Documentation | DISHONEST ON ENCRYPTION | Medium | "Complete" — missed spec/impl mismatch |

**Recommendation:** Do not proceed to genesis plan 009 (Hermes), 011 (remote access), or 012 (inbox UX) until P0 (daemon auth + CORS + spec fix) is resolved. Expanding the surface area before the auth boundary is real makes each subsequent problem harder.
