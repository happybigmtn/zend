I've now read every implementation file, reference contract, and shell script. Here's my Nemesis-style review.

---

# Lane Review: `carried-forward-build-command-center`

## Verdict: CONDITIONALLY APPROVED — spec honest, code functional, but security model is structurally incomplete

The spec and review artifacts are well-written and refreshingly candid about known gaps. The codebase delivers a coherent milestone-1 prototype with clean separation (daemon/store/spine/cli). The acceptance criteria honestly track what's done vs. not.

But the auto-generated review misses the most dangerous finding, and several other issues that a Nemesis pass should surface.

---

## Pass 1 — First-Principles Challenge: Trust Boundaries & Authority

### CRITICAL: Daemon HTTP API has zero authentication

This is the single biggest gap between what the spec implies and what the code delivers.

`★ Insight ─────────────────────────────────────`
The spec says "Capability enforcement: `store.py` exports `has_capability()` used by `cli.py` before any control action is dispatched to the daemon." This creates the impression that capability checks gate all control paths. In reality, the daemon's HTTP layer (`daemon.py:186-200`) accepts POST requests from **any process** that can reach the port — no token, no principal, no capability check. The CLI is one client; the HTTP API is the actual trust boundary, and it's wide open.

Any process on localhost can `curl -X POST http://127.0.0.1:8080/miner/stop` and halt mining. If `ZEND_BIND_HOST` is ever set to a LAN address, any device on the network gets the same power. The gateway client (`index.html:743`) also bypasses `cli.py` entirely — it calls the daemon API directly with no auth headers.
`─────────────────────────────────────────────────`

**Impact:** Anyone on localhost (or LAN if misconfigured) can control the miner without pairing. The capability model is cosmetic — it only works if everyone agrees to use `cli.py`.

**Recommendation:** Genesis plan 003 (security hardening) must add bearer-token auth to the daemon HTTP layer before any real use. This is not "nice to have" — it's the difference between "capability scoping" and "honor system."

### HIGH: `ZEND_BIND_HOST` allows public binding without guardrail

`daemon.py:34` — The spec says "`0.0.0.0` is not acceptable" but the code will happily bind `0.0.0.0` if the env var says so. No runtime validation.

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
```

**Recommendation:** Whitelist `127.0.0.1` and private-range addresses. Reject `0.0.0.0` with an explicit error until genesis plan 011 formalizes remote access.

### HIGH: Gateway client hardcodes capabilities — no server verification

`index.html:626`:
```javascript
capabilities: ['observe', 'control'],
```

The client trusts itself to have both capabilities. It never checks the pairing store. Since the daemon API has no auth anyway, this is internally consistent but means the capability model is entirely decorative end-to-end.

### MEDIUM: Shell injection in `hermes_summary_smoke.sh`

Line 51-53:
```bash
python3 -c "
...
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
"
```

`$SUMMARY_TEXT` is interpolated directly into a Python string literal. A single quote in the summary text breaks out of the Python string. This is a milestone-1 smoke test, not production, but it demonstrates the pattern risk.

### MEDIUM: No CORS on daemon — any website can control the miner

The daemon sends no `Access-Control-Allow-Origin` headers. Browsers may block cross-origin requests from the gateway client (which loads from `file://`). But conversely, browsers that *do* allow the request (or any same-origin context) give every open webpage implicit control. There's no preflight rejection to distinguish the Zend client from a malicious page.

---

## Pass 2 — Coupled-State Review

### Pairing store ↔ Event spine: not atomic

`cli.py:cmd_pair` (lines 102-115) writes to the pairing store first, then appends two spine events (`pairing_requested`, `pairing_granted`). If `spine.append_pairing_granted()` fails (disk full, permission error), the pairing exists without a spine record. The audit trail is incomplete but the capability is active.

Same issue in `cmd_bootstrap` (lines 74-93): pairing is created, then spine event appended non-atomically.

**Recommendation:** At minimum, wrap both operations in a try/except that rolls back the pairing if spine append fails. Or accept the asymmetry and document it as a known M1 gap.

### Daemon state ↔ Spine receipts: fire-and-forget

`cli.py:cmd_control` (lines 131-176) calls the daemon HTTP API, gets a result, then appends a `control_receipt` to the spine. If spine append fails, the action happened but has no receipt trail. The receipt status (`accepted`/`rejected`) is derived from the daemon response but there's no reconciliation if the two disagree later.

### MinerSimulator: single global, no principal scoping

`daemon.py:152` — One global `miner` instance. All paired clients share it. Start/stop from one client affects all clients with no notification to others. The spec doesn't claim multi-tenant, but this means "alice-phone starts mining" silently affects "bob-tablet" if both are paired.

### Client optimistic updates ↔ server state

`index.html:748-749` — After a successful start, the client sets `state.status = 'running'` locally before the next poll confirms it. If the daemon crashes between action and poll, the client shows incorrect state for up to 5 seconds.

`★ Insight ─────────────────────────────────────`
This is a common pattern in mobile-shaped UIs: optimistic updates make the interface feel responsive, but they create a window where client state and server state diverge. The 5-second poll interval means up to 5 seconds of potential inconsistency. For a "calm trust" product, the freshness display helps — but the stale-detection logic from the error taxonomy (`MinerSnapshotStale`) is not actually implemented in the client. The client never marks freshness as "stale."
`─────────────────────────────────────────────────`

---

## State Transitions: Replayability, Idempotence, Recovery

### Token expires at creation time

`store.py:88-89`:
```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()
    return token, expires
```

The expiration timestamp is the creation timestamp. Every token is expired the instant it's created. This means:
- Token expiry checking would reject every token if implemented
- The `PairingTokenExpired` error from the taxonomy can never be correctly raised because there's no valid window

This is worse than "not enforced" — it's structurally broken. Genesis plan 003 needs to add a validity window (e.g., `+ timedelta(minutes=10)`).

### Token replay: scaffolded dead code

`store.py:49` sets `token_used=False` but no code path ever reads or mutates this field. The `pair_client` function at line 93 creates the pairing and saves it — `token_used` stays `False` forever. The existing review correctly identifies this, but underrates it: the token is the pairing record's UUID, not a separate challenge token. The current design confuses "pairing record ID" with "pairing challenge token."

### Bootstrap is not idempotent for pairing

`bootstrap_home_miner.sh` calls `cli.py bootstrap --device alice-phone`. If run twice, the second run fails with `ValueError: Device 'alice-phone' already paired` (from `store.py:101`). The script doesn't handle this gracefully — it reports bootstrap failure. The spec says "Idempotent bootstrap: detects already-running daemon and reuses state safely" but this only applies to the daemon process, not the pairing state.

### Spine file append is not crash-safe

`spine.py:64` opens the file in append mode and writes a JSON line. If the process crashes mid-write, the JSONL file gets a partial line. The next `_load_events()` at line 57 calls `json.loads(line)` which will raise `JSONDecodeError` on the corrupted line and crash. No recovery logic.

---

## Secret Handling & Privilege Escalation

### No authentication secret exists

There are no secrets in the system. PrincipalId is a UUID v4 — it's an identifier, not a credential. Pairing records have no shared secret. The daemon API has no auth mechanism. The client stores `principalId` in `localStorage` but never sends it to the daemon.

The spec's language about "encrypted operations inbox" and "principal's identity key" implies a key hierarchy that doesn't exist. The only encryption mentioned in `references/event-spine.md` is "handled by the underlying memo transport layer" — which isn't implemented.

### Capability escalation is trivial

Since the daemon API has no auth, any process can perform `control` actions regardless of its paired capabilities. Even through the CLI path, re-pairing a device with elevated capabilities only requires knowing the device name hasn't been used yet. There's no approval flow — `pair_client` auto-grants whatever capabilities are requested.

### PID file controls daemon lifecycle

`bootstrap_home_miner.sh:47-57` uses a PID file to manage the daemon. The `stop_daemon` function reads a PID from a file and kills it. If an attacker can write to `state/daemon.pid`, they can cause the bootstrap script to kill arbitrary processes (PID injection). This is a localhost-only concern but worth noting for the threat model.

---

## External Process Control & Service Lifecycle

### Force-kill without cleanup

`bootstrap_home_miner.sh:54` — After a 1-second grace period, `kill -9` force-terminates the daemon. This doesn't give the daemon a chance to flush pending spine writes or release the port cleanly. `allow_reuse_address = True` in `ThreadedHTTPServer` mitigates the port issue, but spine corruption is possible.

### No Content-Length limit

`daemon.py:177` reads `Content-Length` from the request header with no upper bound:
```python
content_length = int(self.headers.get('Content-Length', 0))
body = self.rfile.read(content_length)
```

A request with `Content-Length: 999999999` will attempt to allocate ~1GB. This is a trivial denial-of-service on localhost.

### No graceful shutdown signal handling in daemon

The daemon catches `KeyboardInterrupt` but has no `SIGTERM` handler. The bootstrap script sends `SIGTERM` (via `kill`), which Python converts to a `SystemExit` — this works, but `server.shutdown()` won't be called, so in-flight requests may be dropped.

---

## Correctness & Milestone Fit

The spec claims are **mostly honest**. What's marked as built is actually present. The remaining-work table accurately maps to genesis plans.

**Fits well:**
- Daemon/store/spine/CLI separation is clean and follows the contracts
- Design system compliance in the gateway client is genuine
- Event spine is the sole write path — no dual-writer risk
- The six shell scripts cover the claimed user journeys
- Thread-safe simulator with proper locking

**Doesn't fit:**
- The spec says "Capability enforcement: `store.py` exports `has_capability()` used by `cli.py` before any control action" — this implies capabilities are enforced. They're checked in one optional path.
- The spec says "Event spine is encrypted" — it's plaintext JSONL
- The no-hashing audit (`no_local_hashing_audit.sh`) greps for `def.*hash` in Python files — this is a heuristic, not a proof. The spec's acceptance criterion "No-hashing audit script proves off-device mining" overstates what the script actually demonstrates.

---

## Remaining Blockers (Ordered by Blast Radius)

| # | Blocker | Genesis Plan | Why Before Next Slice |
|---|---------|-------------|----------------------|
| 1 | Daemon API has no authentication | 003 | Capability model is fictional without it |
| 2 | Token creation is structurally broken (instant expiry) | 003 | Must be fixed alongside token enforcement |
| 3 | Event spine is plaintext | 011 | Contract says encrypted; building inbox UX on plaintext spine creates migration debt |
| 4 | No automated tests | 004 | Every finding above was found by reading code, not by tests catching regressions |
| 5 | BIND_HOST allows 0.0.0.0 | 004 | One env var misconfiguration exposes the unauthenticated API to the network |
| 6 | Spine append is not crash-safe | 004 | Data loss path exists on unclean shutdown |
| 7 | Bootstrap pairing is not idempotent | 003 | Re-running bootstrap fails instead of recovering |

---

## Assessment Summary

The **spec layer is strong** — contracts are well-defined, the error taxonomy is thoughtful, the design system is genuine. The **implementation is a coherent prototype** that proves the product claim.

The **security model is structurally incomplete** in a way the existing auto-generated review doesn't surface: the capability system only works if all access goes through `cli.py`, but the daemon API is the real trust boundary and it's open. This isn't a bug to fix — it's a design gap that genesis plan 003 must close before the system can honestly claim "scoped permissions."

The auto-generated review correctly identifies 6 gaps. This Nemesis pass adds 7 more findings (unauthenticated daemon API, instant-expiry tokens, shell injection, no CORS, no content-length limit, PID injection, non-atomic coupled state) and upgrades the severity assessment of the ones already identified.

**Recommendation:** Approve the slice as an honest milestone-1 prototype. Prioritize genesis plan 003 (daemon auth) before 004 (tests) — testing an unauthenticated system produces false confidence.