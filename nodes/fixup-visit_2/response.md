**Fixup Complete — Verification PASS**

Two deterministic failures were resolved:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| fuser parsing | `tr -s ' ' '\n'` doesn't parse `port/tcp: PID` format — passed entire string to `kill` | Use `sed 's/.*://'` to extract PIDs after the colon |
| Non-idempotent bootstrap | `pair_client()` throws `ValueError` on duplicate device — fails with exit 1 under `set -e` | Check if device exists first; return existing pairing if so |

`★ Insight ─────────────────────────────────────`
**fuser output format**: fuser uses `port/tcp: PID1 PID2` format (colon-separated), not space-separated PIDs. The original `tr -s ' ' '\n'` only collapses spaces — it leaves colons and slashes untouched, so `8080/tcp: 1419386` was passed whole to `kill` and silently failed.

**Idempotency under strict mode**: `set -e` causes any non-zero exit to terminate the script immediately. A command that "mostly works but fails on re-run" is not safe in strict mode — bootstrap must be idempotent to survive `set -e`.
`─────────────────────────────────────────────────`