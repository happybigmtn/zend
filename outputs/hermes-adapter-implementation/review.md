# Hermes Adapter Implementation — Security Review

**Review date:** 2026-03-22
**Reviewer:** Nemesis Security Review
**Implementation:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/cli.py`
**Reference contract:** `references/hermes-adapter.md`

## Verdict

**Conditional Approval.** The milestone 1 functional scope is met: the capability boundary correctly scopes Hermes to `observe + summarize`, control endpoints are double-blocked, and event filtering excludes `user_message`. Two critical authentication findings (C1, C2) undermine the boundary against a local adversary and must be remediated before merge. All other findings are acceptable for MVP with post-merge tracking.

---

## Critical Findings — Fix Before Merge

### C1 — Re-pairing returns secret token in plain text

**File:** `services/home-miner-daemon/hermes.py`, function `pair_hermes()`

`pair_hermes()` is idempotent: if `hermes_id` already exists in `hermes-pairings.json`, it returns the full `HermesPairing` including the secret `token` field. The daemon endpoint at `/hermes/pair` then reflects this token in the JSON response.

**Any caller who knows or guesses a `hermes_id` can retrieve its bearer token** by calling `/hermes/pair`, regardless of whether they previously performed the pairing.

**Remediation:** On re-pair of an existing `hermes_id`, return only metadata (hermes_id, device_name, paired_at, capabilities) without the token. Alternatively, reject with `409 Conflict` and require explicit unpair first.

---

### C2 — Post-connect auth requires only `hermes_id`, not token

**Files:** `services/home-miner-daemon/daemon.py` (`_get_hermes_connection()`), `services/home-miner-daemon/hermes.py` (`connect()`)

After `/hermes/connect` validates the token once and stores the resulting `HermesConnection` in the in-memory `_hermes_connections` dict, every subsequent request uses only `Authorization: Hermes <hermes_id>` — the token is never required again. `_get_hermes_connection()` looks up the connection by `hermes_id` alone.

**Any process that knows a `hermes_id` (a user-chosen string, not a secret) can impersonate any connected Hermes agent**, provided it can reach the daemon. A misbehaving local process, a compromised sibling container, or a CSRF attack (see L5) all satisfy this condition.

**Remediation:** Require `Authorization: Hermes <hermes_id>:<token>` on every authenticated request, validating against the stored pairing record. Alternatively, issue a short-lived session token at connect time and require that session token on subsequent requests.

---

## High Findings — Fix Before Merge

### H1 — `/hermes/pair` is unauthenticated

**File:** `services/home-miner-daemon/daemon.py`, route handler for `/herhermes/pair`

No authentication is required to create a Hermes pairing. Combined with C1, any process that can reach the daemon can retrieve any Hermes agent's token and gain full Hermes access. The daemon binds to `127.0.0.1` by default, but `ZEND_BIND_HOST` is configurable and many home networks are flat.

**Remediation:** Require principal/owner authentication on `/hermes/pair`, or implement an operator-approval flow. At minimum, require that a client with `control` capability has already paired before Hermes pairing is permitted.

---

### H2 — `token_expires_at` is set to creation time, never enforced

**File:** `services/home-miner-daemon/hermes.py`, `pair_hermes()`

```python
token_expires_at=datetime.now(timezone.utc).isoformat()
```

Expiration is set to *now*, not a future time. `connect()` never checks `token_expires_at`. If expiration logic is ever added, all existing tokens fail immediately.

**Remediation:** Set `token_expires_at` to a real future time (e.g., 30 days) and enforce it in `connect()`. Or remove the field until it is implemented.

---

### H3 — `import os` appears after functions that reference it

**File:** `services/home-miner-daemon/hermes.py`

`os.environ` is referenced inside `_get_hermes_pairings_file()` (called from `_get_hermes_pairings()`), but `import os` appears several lines after those functions are defined. Python resolves all module-level imports before executing any function body, so this works at runtime — but it is fragile, confusing, and will break if an early-line import or a future refactor introduces a circular dependency or load-order issue.

**Remediation:** Move `import os` to the top of the file with the other imports.

---

## Medium Findings — Track Post-Merge

### M1 — No revocation mechanism

No `unpair_hermes()` function exists. Once paired, a Hermes agent retains access until the daemon restarts *and* `hermes-pairings.json` is manually edited. The `capability_revoked` event kind is defined in the spine contract but the adapter never emits it. A lost or compromised Hermes agent cannot be invalidated without daemon downtime.

### M2 — No rate limiting or size limit on summary append

`append_summary()` has no deduplication, rate limiting, or size cap on `summary_text`. A misbehaving Hermes agent can flood the spine. Consider a simple per-agent write budget.

### M3 — In-memory connection state never expires

`_hermes_connections` in `daemon.py` grows monotonically. Connections are never cleaned up. If a pairing is deleted from disk, the in-memory connection remains valid for the lifetime of the daemon process.

### M4 — Hermes events share `principal_id` with user events

`hermes.py` passes `connection.principal_id` to `append_hermes_summary()`, attributing Hermes summaries to the same principal as user-initiated events. The `kind=hermes_summary` field is the only discriminator. Consider including `hermes_id` in the summary payload for clearer audit trails.

### M5 — Broad exception catch in `/hermes/pair` leaks internals

`daemon.py` route for `/hermes/pair`:

```python
except Exception as e:
    self._send_json(500, {"error": str(e)})
```

Any exception — `PermissionError`, `OSError`, `KeyError` — is stringified and sent to the client. Internal paths, module names, and state can leak.

### M6 — Pairing file writes are not atomic

`_save_hermes_pairings()` in `hermes.py` writes directly to `hermes-pairings.json`. A crash or signal mid-write produces a truncated or corrupted file. Use write-to-temp + `os.rename()`.

---

## Low / Informational

### L1 — Event filter may under-return

`get_filtered_events()` over-fetches by 2×, but if the spine is dominated by non-readable events, fewer than `limit` results are returned. The 2× multiplier is an arbitrary heuristic with no upper bound on wasted reads.

### L2 — Reference divergence: `user_message` blocked vs read-only

`references/hermes-adapter.md` §Event Spine Access says "read-only access to user messages." The implementation blocks `USER_MESSAGE` entirely. This is more restrictive (privacy-first) but is an undocumented divergence. See spec design decision #2.

### L3 — Three separate Hermes state stores

Hermes state is split across `state/hermes-pairings.json` (persistent, adapter), `_hermes_connections` (in-memory, daemon), and `state/hermes-cli-state.json` (persistent, CLI). No single view of Hermes agent state exists.

### L4 — Token files are world-readable by default

`hermes-pairings.json` and `hermes-cli-state.json` contain bearer tokens with the process umask (typically 0644). Acceptable for single-user home miner; document the expectation or tighten permissions for production.

### L5 — No CORS or origin validation

If `ZEND_BIND_HOST` is set to a non-loopback address, a malicious webpage can trigger pairing or connection requests via browser-side scripts. See H1.

### L6 — Hermes connect/disconnect not audited

No spine event is emitted when a Hermes agent connects or disconnects. The operator has no visibility into Hermes session lifecycle.

---

## Milestone 1 Fit

| Requirement | Status | Notes |
|---|---|---|
| Observe-only: read miner status | **MET** | `read_status()` checks `observe` capability |
| Summary append to event spine | **MET** | `append_summary()` checks `summarize` |
| No direct miner control | **MET** | Double defense: adapter check + daemon header check |
| Event spine read: `hermes_summary`, `miner_alert`, `control_receipt` | **MET** | Whitelist in `get_filtered_events()` |
| Block `user_message` | **EXCEEDED** | Blocked entirely; reference says read-only |
| Pairing endpoint | **MET** | `/hermes/pair` grants `observe + summarize` |
| CLI commands | **MET** | `pair`, `connect`, `status`, `summary`, `events` |
| Authority token encodes principal, capabilities, expiration | **NOT MET** | UUID-based lookup token; capabilities stored server-side (see design decision #1) |

The functional scope is achieved. The boundary logic is sound. The authentication model is the blocker.

---

## Required Before Merge

1. **C1 remediation** — re-pair must not return the token
2. **C2 remediation** — every authenticated request must validate the token (or a session token derived from it)
3. **H3 remediation** — move `import os` to top of file

## Post-Merge Tracking

- M1: Revocation mechanism (`unpair_hermes`, spine event emission)
- M2: Rate limiting / size cap on summary append
- M3: Connection TTL / cleanup in `_hermes_connections`
- M4: Include `hermes_id` in summary payload
- M5: Narrow exception handling in `/hermes/pair`
- M6: Atomic pairing file writes
- L1: Improve event filter efficiency
- L2: Document `user_message` blocking as deliberate
- L3: Consider unifying Hermes state stores
- L4: Document umask expectation or set `0o600` on token files
- L5: Add origin validation if non-loopback binding is supported
- L6: Emit connect/disconnect spine events
- H1: Require owner auth on `/hermes/pair`
- H2: Real token expiration with enforcement
