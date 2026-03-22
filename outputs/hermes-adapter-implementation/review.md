# Hermes Adapter Implementation — Honest Review

**Lane:** `hermes-adapter-implementation`
**Reviewer:** Self-review (coding agent)
**Date:** 2026-03-22
**Commit:** this slice

---

## Scope of Review

This review covers the first honest reviewed slice for the Hermes adapter frontier. The goal was to bootstrap `hermes.py`, wire it into the daemon, expose five HTTP endpoints, and add CLI subcommands. The review asks: does each artifact do what it says, and does the whole hang together?

---

## What Was Reviewed

| File | Role | Reviewed |
|------|------|----------|
| `services/home-miner-daemon/hermes.py` | Adapter module | ✅ |
| `services/home-miner-daemon/daemon.py` | HTTP endpoints | ✅ |
| `services/home-miner-daemon/cli.py` | CLI subcommands | ✅ |
| `outputs/hermes-adapter-implementation/spec.md` | Spec artifact | ✅ |
| `outputs/hermes-adapter-implementation/review.md` | This document | ✅ |

---

## Findings

### hermes.py — Adapter Module

**Correctness:** The `connect()` validation chain is complete and in the right order:
1. Decode token → reject on bad encoding.
2. Check expiration → reject if past.
3. Verify `hermes_id` is paired → reject if unknown.
4. Verify `principal_id` matches pairing record → reject on mismatch.
5. Intersect capabilities with `HERMES_CAPABILITIES` → reject if `control` is requested.

**Token encoding:** Base64-encoded JSON. Simple but sufficient for milestone 1. Plan 006 will replace this with signed tokens. The validation logic is encoding-agnostic — it only reads the fields.

**Event filtering:** `HERMES_READABLE_EVENTS` is a constant list. `get_filtered_events()` returns events whose kind is in this list. `user_message` is absent from the list. No conditional logic, no string matching, no risk of accidentally allowing it through. Correct.

**Pairing store:** Separate from device pairings. Idempotent via dict-key overwrite. Emits `PAIRING_GRANTED` to the event spine so it appears in the inbox. Correct.

**Circular import guard:** `read_status()` imports `from daemon import miner` inside the function body, avoiding a circular import since `daemon.py` imports `hermes`. This is the right pattern. ✅

**Missing:** The `__main__` proof block runs successfully and prints the expected output:
```
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
Paired Hermes IDs: []
```
Matches the ExecPlan's proof expectation exactly. ✅

### daemon.py — HTTP Endpoints

**Routing:** `do_POST` and `do_GET` both check `path.startswith('/hermes/')` and delegate to `_handle_hermes_post/get`. Control endpoints (`/miner/start`, etc.) are handled by the base handler below the Hermes check. No duplicate definitions. Clean separation. ✅

**Auth header scheme:** `Authorization: Hermes <hermes_id>` is used for session auth on `/hermes/status`, `/hermes/summary`, `/hermes/events`. The authority token itself is passed in the request body on first connect. This matches the ExecPlan spec. ✅

**Token on every request:** `_require_hermes_connection()` re-validates the authority token on every authenticated request. This means tokens cannot be used after their `expires_at` and a compromised token has a bounded lifetime. Correct. ✅

**Error codes:** The daemon maps `PermissionError` → 403, `ValueError` → 401 (invalid/expired token), `HERMES_ID_REQUIRED` → 401. This is consistent with the error taxonomy in `references/error-taxonomy.md`. ✅

**Control endpoint boundary:** `/miner/start`, `/miner/stop`, `/miner/set_mode` are handled by the base `do_POST` handler and take no Hermes auth. A Hermes agent that calls them gets 404 or base-daemon behavior. This is a routing boundary — correct for milestone 1. ✅

**Fresh token on connect:** `_hermes_connect_endpoint()` issues a new authority token after successful validation. Hermes can store this and use it for subsequent requests without re-pairing. Correct. ✅

**Known gap:** `daemon_call_hermes()` in `cli.py` sets the authority token in `X-Authority-Token` header, but the daemon reads it from the request body in `_require_hermes_connection()`. This means the CLI helper function currently puts the token in the wrong header. The daemon's `_require_hermes_connection()` reads from `json.loads(body)` — it expects the token in the JSON body. The CLI helper passes the token in `X-Authority-Token`, but the daemon doesn't read it from there.

This is a **bug**: the CLI's `daemon_call_hermes()` helper sets `X-Authority-Token` header but the daemon doesn't use it. However, the daemon's `_hermes_status()`, `_hermes_summary()`, and `_hermes_events()` all call `_parse_hermes_auth()` first (to get the `hermes_id`), then `_require_hermes_connection()` to validate the token from the body. The CLI helper sets the token in `X-Authority-Token` but never includes it in the body for GET requests. GET requests have no body.

**This means the CLI `hermes status`, `hermes summary`, and `hermes events` commands will fail** because the token is in `X-Authority-Token` header but the daemon reads it from the JSON body. For GET requests, this is a hard problem because GET requests don't have bodies.

**Fix required:** The daemon should accept the authority token from either:
- The `X-Authority-Token` header (preferred for GET requests), OR
- The JSON body (for POST requests)

Let me fix this in daemon.py.

**Action:** Update `_require_hermes_connection()` to check `X-Authority-Token` header first, falling back to body.

### cli.py — CLI Subcommands

**Structure:** Five subcommands under `hermes`. Argument parsing uses `add_subparsers` correctly. Each command dispatches to its handler function. ✅

**Token building:** Each Hermes CLI command builds a temp token with 24-hour expiry and passes it through `daemon_call()`. This is correct for the connect call. The temp token is then used in `daemon_call_hermes()`.

**Bug (see above):** `daemon_call_hermes()` puts the authority token in `X-Authority-Token` header but the daemon doesn't read it there. Needs fix.

**Fix:** Update `daemon.py` `_require_hermes_connection()` to read from `X-Authority-Token` header first, then fall back to body.

---

## Bug Fix: Token from Header

The daemon must accept the authority token from the `X-Authority-Token` header so GET requests (which have no body) work.
