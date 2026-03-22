## Review Complete — Verdict: PASS WITH FIXES APPLIED

### 4 bugs found and fixed

| # | File | Severity | Issue |
|---|------|----------|-------|
| 1 | `test_hermes.py:148` | Blocker | `TestDaemon()` — undefined class; should be `HermesTestDaemon()` |
| 2 | `daemon.py:177-212` | High | `_require_hermes_auth` error returns `(None, None)` — falsy sentinel causes handler to proceed with `conn=None` and crash after already sending 401 headers |
| 3 | `cli.py:327` | Blocker | Second `daemon_call` definition shadows the real HTTP caller; `main()` not defined; local `hermes` variable shadows module import |
| 4 | `hermes.py:299` | Security | No cross-validation of token's `principal_id` against pairing record — allows impersonation via forged token |

`★ Insight ─────────────────────────────────────`
**The `(None, self._send_json(...))` anti-pattern** is worth internalizing. When a void method is used as a return value expression, the sentinel is always `None`/falsy. This silently defeats any guard that checks truthiness of the error return. The fix pattern: call the side-effect first, then return an explicit truthy sentinel on a separate line.

**Principal cross-validation** is a defense-in-depth requirement whenever a token carries identity claims and a server-side record exists for the same entity. If both encode `principal_id`, they must agree — otherwise the token becomes a confused deputy that acts on behalf of whichever principal it claims.
`─────────────────────────────────────────────────`

### After fixes: 11/11 tests pass, CLI works, all artifacts written

**Artifacts produced:**
- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`

**Remaining non-blocking observations** (documented in review.md):
1. `POST /hermes/pair` doesn't return the authority token — non-CLI consumers can't authenticate
2. `references/hermes-adapter.md` line 74 contradicts the event filtering implementation (says "read-only access to user messages" but implementation correctly filters them out)
3. Token is not cryptographically signed (acceptable M1, must address before network exposure)
4. Smoke script bypasses the adapter (calls spine directly)