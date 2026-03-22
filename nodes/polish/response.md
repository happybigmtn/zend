Both artifacts are clean. Here's a summary of what was done in this polish pass:

---

## Changes Made

### `services/home-miner-daemon/daemon.py` — Bug Fix

**Problem identified in first review:** `daemon_call_hermes()` in the CLI sent the authority token in the `X-Authority-Token` HTTP header, but `_require_hermes_connection()` in the daemon read it only from the JSON request body. GET requests (`/hermes/status`, `/hermes/events`) have no body — so every authenticated GET would fail with a 400 "body required" error.

**Fix:** `_require_hermes_connection()` now checks `X-Authority-Token` header first (works for all requests), falling back to the JSON body only when the header is absent. This gives a uniform token-transport strategy across GET and POST without any CLI change.

---

### `outputs/hermes-adapter-implementation/spec.md` — Updated

- Added the `X-Authority-Token` header transport to the endpoint table (previously only noted body)
- Added a **Token transport** subsection explaining the header-first, body-fallback design decision
- Added decision log entry for the header transport choice

---

### `outputs/hermes-adapter-implementation/review.md` — Updated

- Changed stage to "Polish (second pass — fix applied)"
- Documented the bug and the fix with before/after code snippets
- Updated verdict to **APPROVED — ready for the supervisory plane**