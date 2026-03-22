---

## Review Complete

Both `outputs/carried-forward-build-command-center/spec.md` and `outputs/carried-forward-build-command-center/review.md` have been updated.

### What the Review Found

**5 confirmed gaps** from the original lane spec — all verified present in code.

**5 new findings** that the lane spec missed:

| Finding | Severity | Description |
|---------|----------|-------------|
| Finding A | Critical | `create_pairing_token()` sets `expires = now` — every future `consume_token()` would immediately reject all tokens as expired |
| Finding B | High | Gateway client hardcodes `capabilities: ['observe', 'control']` — never fetches actual grants |
| Finding E | High | `consume_token()` interface references a `token` field that doesn't exist in `GatewayPairing` — the spec is unimplementable without adding it |
| Finding F | Medium | Event spine contract says "encrypted" but appends raw JSON |
| Finding C | Medium | Bootstrap path skips `pairing_requested` event, creating inconsistent spine |

**Security invariant violations:**

- **LAN-only enforcement**: VIOLATED — any HTTP client can POST `/miner/start` without credentials
- **Capability least-privilege**: VIOLATED — UI always claims `['observe', 'control']` regardless of what was granted
- **Token one-time use**: VIOLATED — no enforcement, function doesn't exist

**Spec task changes:**

- Added **Task 0** as a prerequisite (add `token` field + fix expiration to future time) before `consume_token()` is implementable
- Added **Task 2b** (gateway client must fetch actual capabilities, not hardcode)
- Added **Task 2c** (bootstrap must append `pairing_requested` event)
- Updated acceptance criteria with 4 new items covering the new findings