I now have a complete picture. Let me write the review.

---

# Carried Forward: Build the Zend Home Command Center — Lane Review

## Overall Verdict

**The review document is honest about what it found but materially understates the security posture.** The lane correctly identifies 5 gaps but misses the most critical one: the daemon HTTP layer has zero authentication. Every security property the review marks "✓" is enforced only in the CLI wrapper, not at the daemon boundary where HTTP callers (including the frontend) actually interact.

The spec is well-structured and the data model is sound. As a milestone 1 prototype with known gaps, this is reasonable. But the review's "APPROVED" framing overstates the security surface.

---

## Correctness

**What's actually correct:**

- PrincipalId flows consistently: `store.py` creates it, `spine.py` references it. The inbox-contract.md requirement that "the same PrincipalId MUST be referenced by gateway pairing records and event-spine items" is satisfied.
- Event kinds match the contract exactly (`spine.py:29-36` vs `event-spine.md:13-20`).
- The MinerSimulator thread safety is correct — lock held for all state mutations (`daemon.py:89,107,116,137`).
- Event spine is append-only by construction (`spine.py:64`, file opened in `'a'` mode).
- The four-tab UI, design system typography, colors, and touch targets match DESIGN.md.

**What's incorrect in the review:**

The review's "Security Properties" table (`review.md:49-57`) marks "Capability enforcement ✓" with evidence "alice-phone observe-only; control rejected." This was tested through the CLI only. The HTTP daemon enforces nothing.

---

## Nemesis Pass 1 — First-Principles Trust Boundary Challenge

### F1. The daemon HTTP layer has zero authentication (CRITICAL)

This is the single most important finding the review misses.

`daemon.py:168-200` — every HTTP endpoint is open. No pairing check, no capability check, no client identity. Compare:

| Endpoint | CLI enforcement | HTTP enforcement |
|----------|----------------|------------------|
| `/status` (GET) | `cli.py:47-54` checks observe capability | **None** — returns snapshot to anyone |
| `/miner/start` (POST) | `cli.py:134` checks control capability | **None** — anyone can start |
| `/miner/stop` (POST) | `cli.py:134` checks control capability | **None** — anyone can stop |
| `/miner/set_mode` (POST) | `cli.py:134` checks control capability | **None** — anyone can set mode |
| `/health` (GET) | None needed | None |

The frontend (`index.html:632-648`) calls HTTP directly. It hardcodes `capabilities: ['observe', 'control']` at line 626 — never checks pairing. Any browser tab, any LAN process, any script hitting `127.0.0.1:8080` has full control.

**The entire capability model is a CLI-only fiction.** The actual trust boundary (the HTTP server) enforces nothing.

`★ Insight ─────────────────────────────────────`
This is a classic pattern in prototype→production drift: the CLI is a convenience wrapper, the HTTP daemon is the actual authority boundary. When capability checks exist only in the convenience layer, they protect nothing against direct callers. In production systems, authorization must be enforced at the authority boundary (the daemon), not the client (the CLI).
`─────────────────────────────────────────────────`

### F2. Token model is completely vestigial

Three compounding problems:

1. **Token expiration is broken** — `store.py:89`: `expires = datetime.now(timezone.utc).isoformat()` sets expiration to *the moment of creation*. Every token is born expired.
2. **Token is never consumed** — `token_used` is set to `False` at creation (`store.py:113`) and never set to `True` anywhere.
3. **Token is never required** — No operation checks for or validates a token. `pair_client()` creates one but nothing consumes it.

The error-taxonomy.md defines `PAIRING_TOKEN_EXPIRED` and `PAIRING_TOKEN_REPLAY` as required error classes. Neither is implemented. The review notes #2 and #3 but misses #1 (the expiration itself is broken).

### F3. No CORS protection — DNS rebinding risk

`daemon.py:162-166` sends no CORS headers. While binding to `127.0.0.1` prevents direct remote access, DNS rebinding attacks are a well-known threat to localhost services. A malicious website the user visits can resolve a domain to `127.0.0.1`, bypass same-origin policy, and send requests to the daemon with full control (since there's no auth).

This isn't theoretical for a mining control service — it's exactly the attack vector that matters.

---

## Nemesis Pass 2 — Coupled-State & Protocol Surface Review

### S1. Pairing store has no concurrency protection

`store.py:72-83` uses a load-all/modify/save-all pattern on `pairing-store.json` with no file locking. Two concurrent `pair_client()` calls (e.g., CLI + another script) can race: both read, both modify, last writer wins, first pairing is lost.

Same problem in `spine.py:62-65` — two concurrent `_save_event()` calls could interleave partial JSON lines in the JSONL file. The `'a'` mode provides OS-level atomicity only up to `PIPE_BUF` (~4KB on Linux), which is likely sufficient for single events, but there's no explicit fsync or locking.

### S2. Bootstrap creates a pairing with no pairing_requested event

`cli.py:73-95` — `cmd_bootstrap()` creates a pairing and emits `pairing_granted` but never emits `pairing_requested`. Compare with `cmd_pair()` at line 106 which correctly emits both. This creates an asymmetry in the event spine: bootstrap pairings have no request audit trail.

### S3. Control receipts record the wrong principal on daemon-unavailable

`cli.py:155-162` — when the daemon call fails (returns `{"error": "daemon_unavailable"}`), the code still appends a `control_receipt` event with `status='rejected'`. But `result.get('success')` returns `None` (not `False`) for the error dict, which is falsy, so `status` becomes `'rejected'`. This is semantically wrong — the command wasn't rejected by the miner; the daemon was unreachable. The receipt misrepresents what happened.

### S4. Event kind filter in CLI passes raw string, not EventKind

`cli.py:190-191`:
```python
kind = args.kind if args.kind != 'all' else None
events = spine.get_events(kind=kind, limit=args.limit)
```

But `spine.get_events()` at line 82 expects an `EventKind` enum (or `None`). Passing a raw string like `"control_receipt"` won't match because line 87 compares `e.kind == kind.value`, calling `.value` on a string, which works by coincidence in Python (strings have no `.value` attribute — this would actually crash). This is a latent bug.

**Edit:** Actually, I re-checked — `EventKind` inherits from `str, Enum`, so `kind.value` on a plain string would raise `AttributeError`. The CLI events command with `--kind` filtering would crash unless `kind` is `None`.

### S5. Frontend polls without backoff

`index.html:790`: `setInterval(fetchStatus, 5000)` — fixed 5-second polling with no backoff on failure. If the daemon is down, the client generates a continuous stream of failed requests and shows the alert banner every 5 seconds (dismissed after 5 seconds, then shown again).

### S6. No idempotence key on control commands

`daemon.py:88-104` — `miner.start()` is not idempotent (returns `{"success": False, "error": "already_running"}`), but there's no request ID or idempotence key. If a control receipt was lost in transit (CLI crashes after sending POST but before reading response), the user can't distinguish "my request succeeded" from "someone else started it."

The error-taxonomy defines `CONTROL_COMMAND_CONFLICT` but the daemon doesn't track in-flight commands.

---

## The "No Local Hashing" Audit Is Cosmetic

`no_local_hashing_audit.sh:60`:
```bash
grep -r "hash" "$DAEMON_DIR"/*.py 2>/dev/null | grep -v "hashrate" | grep -v "#" | grep -q "def.*hash"
```

This greps the *daemon* Python files for `def.*hash`. It proves nothing about the *client*. The script doesn't inspect the client process, doesn't check CPU load, doesn't trace syscalls, doesn't verify the frontend. The "proof" is: "we searched our own code for the word 'hash' and didn't find it." This is a tautology, not an audit.

The spec and review both mark "No local hashing ✓" based on this script. That claim needs a much stronger evidentiary basis for a product that differentiates on "mining doesn't happen on your phone."

---

## Milestone Fit

The genesis plan 015 maps remaining work to plans 002–014. This mapping is coherent:

| Gap | Plan | Fit |
|-----|------|-----|
| Tests | 004 | Good — tests will surface the bugs above |
| Token enforcement | 003/006 | Good — but must also fix expiration logic |
| Hermes adapter | 009 | Good — contract-first was the right call |
| Encryption | 011/012 | Good — deferred explicitly |
| CLI bug | 014 | Good — but the HTTP auth gap is more urgent |
| **HTTP auth (missing from map)** | **None** | **Not mapped to any genesis plan** |

The biggest risk: **daemon HTTP authentication is not tracked by any genesis plan.** Plans 003 and 006 address token enforcement and security hardening, but neither explicitly addresses "add auth to the HTTP daemon." This could slip through the entire genesis roadmap.

---

## Remaining Blockers for This Lane

1. **The review must acknowledge the HTTP auth gap.** Currently the security properties table claims capability enforcement works. It doesn't at the daemon boundary.

2. **A genesis plan must be assigned to HTTP daemon authentication.** This is a P0 for any LAN deployment. Plan 003 (security hardening) is the natural home.

3. **The event-kind CLI filter bug (`spine.get_events(kind=string)`)** will crash. Minor but should be fixed or acknowledged.

---

## Summary Table

| Finding | Severity | Review Caught? | Genesis Plan? |
|---------|----------|----------------|---------------|
| HTTP daemon has zero auth | **CRITICAL** | No | **None** |
| Token expiration broken (born expired) | HIGH | Partially (replay only) | 003 |
| Token replay not enforced | HIGH | Yes | 003 |
| DNS rebinding (no CORS) | MEDIUM | No | None |
| Pairing store race condition | MEDIUM | No | None |
| Bootstrap missing pairing_requested event | LOW | No | None |
| Control receipt on daemon-unavailable | LOW | No (CLI bug noted differently) | 014 |
| CLI event-kind filter would crash | LOW | No | None |
| No-hashing audit is cosmetic | LOW (credibility) | No | 008 |
| Frontend capabilities hardcoded | LOW | No | None |

`★ Insight ─────────────────────────────────────`
The carried-forward lane demonstrates a disciplined spec-first approach — 6 reference contracts, consistent data models, honest gap tracking. The main failure mode is a gap between where the review *tested* (CLI) and where real callers *interact* (HTTP). This is a common review blind spot: testing through the wrapper that has guardrails rather than through the raw interface that attackers (or bugs) will actually hit. Always test the authority boundary directly.
`─────────────────────────────────────────────────`