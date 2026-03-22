# Documentation & Onboarding — Review

**Date:** 2026-03-22
**Reviewer:** Claude Opus 4.6 (post-polish verification)
**Lane:** documentation-and-onboarding
**Verdict:** PASS — all blocking issues from prior review have been addressed.

---

## Prior Review Findings (addressed)

The prior review identified several critical issues. This section confirms each was fixed.

### 1. Phantom HTTP Endpoints — FIXED

`GET /spine/events` and `POST /pairing/bootstrap` were documented as HTTP endpoints
but do not exist in `daemon.py`. Both are CLI-only commands.

**Resolution:** Both removed from the HTTP API section. Added "CLI-Only Commands"
section in `docs/api-reference.md` with correct `python3 cli.py ...` syntax and
note that these are not HTTP endpoints.

### 2. Auth Claims Were False — FIXED

`daemon.py` performs zero authorization checks. The HTTP daemon accepts every
request unconditionally. The CLI layer checks capabilities, but the daemon does not.

**Resolution:** All HTTP endpoints in `api-reference.md` now say "Auth: None".
Added dedicated "Security Model" section at the top of the API reference explaining
the honest threat model: network isolation is the only access control. Updated
`architecture.md` to show both the CLI path (auth+spine) and HTML gateway path
(no auth, no spine) with honest labels.

### 3. Quickstart Step 5 Would Fail — FIXED

Bootstrap creates `alice-phone` with only `['observe']` capability. The quickstart
used `--client my-phone` which didn't exist, and `control` requires `['control']`.

**Resolution:** Quickstart now has two steps for control:
1. Explicitly pair with `observe,control`: `python3 cli.py pair --device my-phone --capabilities observe,control`
2. Then issue the control command with the correct client name

Added inline note explaining why the pairing step is needed.

### 4. CLI `--kind` Filter Bug — KNOWN LIMITATION (not fixed in docs)

`cli.py:190` passes a raw string to `spine.get_events(kind=kind)` which calls
`kind.value`. Plain strings have no `.value` attribute. This is a **runtime bug**
in `cli.py`, not a documentation issue. The documentation accurately describes
the `--kind` interface; the bug prevents it from working.

**Status:** Bug in `cli.py` (not in scope for docs lane). Documented in
`architecture.md` Known Limitations table.

### 5. Bootstrap Non-Idempotency — DOCUMENTED

`bootstrap_home_miner.sh` raises `ValueError` if run twice with the same device
name. No "update or skip" behavior.

**Resolution:** Documented in `docs/operator-quickstart.md` Recovery section and
in `docs/api-reference.md` CLI-only commands section. Note added that `rm -rf state`
is required before re-bootstrapping.

### 6. Direct HTTP → No Spine Events — DOCUMENTED

When the HTML gateway calls `/miner/start`, the daemon updates miner state but
does not write a spine event. Only CLI-mediated commands write events.

**Resolution:** Documented in `docs/api-reference.md` (CLI-only commands section
note), `docs/architecture.md` (Data Flow section with both paths, Known Limitations
table), and `docs/operator-quickstart.md` (controls not working → spine note).

### 7. `ZEND_DAEMON_URL` Undocumented — FIXED

Added to README.md Daemon Controls section, api-reference.md Environment Variables
section, and architecture.md cli.py module section.

---

## What the Docs Now Correctly State

### HTTP Endpoints (daemon.py)

| Endpoint | Auth | Notes |
|----------|------|-------|
| `GET /health` | None | Always accessible |
| `GET /status` | None | Always accessible |
| `POST /miner/start` | None | Any HTTP client can start |
| `POST /miner/stop` | None | Any HTTP client can stop |
| `POST /miner/set_mode` | None | Any HTTP client can change mode |

### CLI Commands

| Command | Auth at CLI Layer |
|---------|-------------------|
| `bootstrap` | None (filesystem only) |
| `pair` | None (filesystem only) |
| `control --client X` | `has_capability(X, 'control')` |
| `events --client X` | `has_capability(X, 'observe')` or `'control'` |
| `status --client X` | `has_capability(X, 'observe')` or `'control'` |

### Honest Security Posture

- Daemon: unauthenticated, network isolation is the only gate
- CLI: capability checks against pairing store
- Pairing tokens: `token_expires_at` set to creation time (always expired), never enforced
- State files: world-readable by default
- Bootstrap: not idempotent

---

## What's Good

- README structure is excellent — under 200 lines, clear quickstart, honest security note
- Operator quickstart security section is now accurate and actionable
- API reference has a clear Security Model section that explains the threat model honestly
- Architecture doc correctly shows both control paths with their different properties
- Known Limitations table in architecture is comprehensive and honest
- The documentation suite as a whole is now trustworthy for milestone 1
