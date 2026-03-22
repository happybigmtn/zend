All changes are complete. Let me provide a summary of what was found and fixed:

---

## Polish Summary

**Issues found and fixed across 4 files:**

### 1. `docs/operator-quickstart.md` — 4 fixes
- **`ZEND_TOKEN_TTL_HOURS`**: Documented with `720 (30 days)` but the code has no such env var and never checks `token_expires_at`. Changed to `_(not implemented)_`.
- **HTML gateway LAN access**: `index.html` hardcodes `http://127.0.0.1:8080` — it literally cannot work from a phone on LAN (the browser calls itself). Added explicit note with workaround (edit `API_BASE` or serve from same machine).
- **Security section**: Removed "30 days" claim about token expiry.
- **Recovery section**: Renamed "Pairing token expired or invalid" → "Re-pairing a device" with note that expiration enforcement is not yet active.

### 2. `docs/api-reference.md` — 1 fix
- Added `ZEND_TOKEN_TTL_HOURS` row with `_(not implemented)_` to prevent misleading operators.

### 3. `docs/architecture.md` — 1 addition
- Added **"HTML gateway LAN access"** section (before "Why the HTML gateway is a single file?") explaining the hardcoded `API_BASE` limitation and the edit workaround.

### 4. `outputs/documentation-and-onboarding/review.md` — 1 update
- Expanded coverage gaps to include: HTML gateway LAN limitation, token expiration not enforced, and event kind casing (uppercase enum names / lowercase string values — idiomatic Python, no functional mismatch).

**Durable artifacts remain accurate:** `spec.md` (unchanged — still correct) and `review.md` (updated coverage gaps).