# Hermes Adapter — Honest Review

**Status:** Reviewed with blockers
**Reviewed:** 2026-03-22
**Reviewer:** Claude Opus 4.6
**Lane:** `hermes-adapter-implementation`

Files reviewed: `services/home-miner-daemon/hermes.py`,
`services/home-miner-daemon/daemon.py`,
`services/home-miner-daemon/cli.py`,
`services/home-miner-daemon/tests/test_hermes.py`,
`services/home-miner-daemon/spine.py`,
`services/home-miner-daemon/store.py`

---

## Verdict

**Do not merge as-is.** The adapter module itself is well-structured and the
capability boundary is correctly implemented. Four bugs in `daemon.py` and
`hermes.py` must be fixed before this lane is milestone-ready. The security model
has acceptable gaps for LAN-only M1 but those gaps are hard blockers before any
network exposure.

---

## What the Implementation Gets Right

1. **Capability allowlist at token parse** — `_parse_token` (hermes.py, ~line 100)
   rejects tokens containing unknown capabilities. `control` is blocked before
   any function is called.

2. **Event filtering uses a positive allowlist** — `HERMES_READABLE_EVENTS` lists
   exactly the event kinds Hermes may see. `user_message` is absent by design.

3. **Payload stripping for sensitive events** — `_strip_sensitive_fields` uses a
   field-level allowlist for `control_receipt` events, stripping all fields except
   `['command', 'status', 'receipt_id', 'mode']`.

4. **Pairing is idempotent** — `pair_hermes` checks for an existing record and
   refreshes the token rather than creating a duplicate.

5. **Defense in depth on control blocking** — Two independent barriers: (a) the
   adapter function level checks capabilities on `read_status`/`append_summary`, and
   (b) `_handle_control_check` in `daemon.py` looks for the `Hermes` auth prefix and
   returns 403 without ever calling the miner. A capability-spoofing bug in the
   adapter cannot open the control surface because the HTTP layer blocks on identity
   prefix alone.

6. **20 unit tests pass** covering the adapter's public surface and the critical
   enforcement paths.

---

## Blockers (must-fix before merge)

### B1: Double-call on all control endpoints

**File:** `services/home-miner-daemon/daemon.py`
**Lines:** 196, 198, 203, 218, 220, 225

Every control endpoint calls the miner method twice in the same request:

```python
elif self.path == '/miner/start':
    self._handle_control_check() or self._send_json(
        200 if miner.start()["success"] else 400, miner.start())  # ← miner.start() called twice
```

The first call mutates miner state (starts/stops/sets mode). The second call
sees the new state and returns `"already_running"` / `"already_stopped"`. The
HTTP response is always a failure even when the operation succeeded.

**Fix:** Capture the result once:
```python
result = miner.start()
self._handle_control_check() or self._send_json(200 if result["success"] else 400, result)
```

Apply the same pattern to `/miner/stop` and `/miner/set_mode`.

---

### B2: Duplicate `do_GET` definition

**File:** `services/home-miner-daemon/daemon.py`
**Lines:** 170–176 (first definition), 299–310 (second definition)

Python class bodies silently overwrite duplicate method names. The first
`do_GET` (line 170) defines `/health` and `/status` handlers and is dead code.
The second `do_GET` (line 299) is the live one and redefines the same handlers
plus adds Hermes endpoints.

If a future contributor edits the first definition expecting it to take effect,
the change vanishes silently. This has not caused a bug yet because the second
definition is a superset, but it is a maintenance hazard.

**Fix:** Delete the first `do_GET` definition entirely (lines 170–176). Move any
logic unique to it into the surviving definition.

---

### B3: Pairing tokens expire at issuance

**File:** `services/home-miner-daemon/hermes.py`
**Lines:** 215 (re-pair refresh), 229 (new pairing)

Both the re-pair and new-pairing paths set `token_expires_at` to the current time:

```python
existing.token_expires_at = datetime.now(timezone.utc).isoformat()   # line 215
# ...
token_expires_at=datetime.now(timezone.utc).isoformat(),           # line 229
```

Every token expires the instant it is created. This is currently masked because
the daemon never validates `token_expires_at` on subsequent requests (see S1),
but it makes the authority token contract meaningless for any future session
binding.

**Fix:** Add `timedelta(hours=24)` to the current time:
```python
from datetime import timedelta
token_expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
```

---

### B4: `_get_or_create_principal_id` can return an unpersisted UUID

**File:** `services/home-miner-daemon/hermes.py`
**Lines:** 238–249

```python
def _get_or_create_principal_id() -> str:
    principal_file = os.path.join(state_dir, 'principal.json')
    if os.path.exists(principal_file):
        with open(principal_file, 'r') as f:
            data = json.load(f)
            return data.get('id', str(uuid.uuid4()))  # ← random UUID if 'id' key absent
    return str(uuid.uuid4())  # ← never persisted
```

If `principal.json` exists but lacks an `id` key, a random UUID is returned and
used as the Hermes `principal_id` but never written back. If Hermes pairs before
daemon bootstrap, the Hermes `principal_id` diverges from the system's
`PrincipalId`. The product spec requires one shared `PrincipalId` across gateway
and Hermes.

**Fix:** Replace the entire function body with a call to `store.load_or_create_principal()`:
```python
from store import load_or_create_principal
# ...
def _get_or_create_principal_id() -> str:
    return load_or_create_principal().id
```

---

## Should-fix (not blockers for LAN-only M1)

### S1: Authority token is ceremonial

The `/hermes/connect` endpoint validates the authority token, but
`/hermes/status`, `/hermes/events`, and `/hermes/summary` authenticate by
`hermes_id` header lookup against the pairing store. There is no session binding
between connect and subsequent requests. A token intercepted on the LAN is
replayable within its validity window.

**Acceptable for LAN-only M1.** Must be resolved before plan 006 (token auth) or
any network exposure.

### S2: `/hermes/events` query param parsing always fails

**File:** `services/home-miner-daemon/daemon.py`
**Line:** 341

```python
if self.path == '/hermes/events':   # ← exact match; path includes query string
```

`self.path` is the raw request path including the query string (e.g.,
`/hermes/events?limit=10`). Exact equality always fails. The limit parameter is
never parsed and every request returns the default 20 events.

The current `_handle_hermes_get` parses `?limit=` from `self.path.split('?')[1]`
but never reaches that code because the path check on line 341 already failed.

**Fix:** Strip query params before comparing:
```python
path_only = self.path.split('?')[0]
if path_only == '/hermes/events':
```

### S3: Over-fetch heuristic can under-deliver on event filtering

`get_filtered_events` fetches `limit * 2` events then filters to readable kinds.
If the spine is dominated by `user_message` events, fewer than `limit` events may
be returned even though more readable events exist further back in the journal.

**Not a blocker for M1.** Acceptable until pagination or cursor-based event
fetching is added.

### S4: New event kinds would leak by default

`_strip_sensitive_fields` uses a field allowlist only for `control_receipt`.
All other event kinds are passed through unmodified. Any future event kind added
to `HERMES_READABLE_EVENTS` would leak its full payload until explicitly
hardened.

**Not a blocker for M1.** Document the expectation that new event kinds must be
reviewed before addition to the allowlist.

### S5: No authentication on `/hermes/pair`

Any HTTP client on the LAN can create a Hermes pairing. The trust boundary for
M1 is the LAN itself.

**Acceptable for LAN-only M1.** Requires authentication before any network
exposure.

---

## Test Coverage Gaps

The following scenarios have no test coverage and should be added before merge:

| Scenario | Why it matters |
|---|---|
| B1 — double-call on control | Every control response is currently wrong |
| B2 — duplicate `do_GET` | Maintenance hazard; no runtime test |
| B3 — token expiration on pair | Tokens are currently unusable past issuance |
| B4 — PrincipalId divergence | Shared identity invariant broken |
| S2 — query param on `/hermes/events` | Limit parameter never works |
| Hermes HTTP control attempt | End-to-end blocking not tested at HTTP level |

---

## Nemesis Security Analysis (M1 scope)

### Trust boundary
The adapter enforces capabilities at the function level. The daemon enforces
Hermes identity at the HTTP level via `Authorization: Hermes <id>` prefix. Two
independent enforcement points — defense in depth.

The HTTP-level enforcement does not use cryptographic identity. A LAN attacker
who omits the Hermes prefix can reach control endpoints without authentication.
This is a pre-existing daemon gap, not Hermes-specific.

### Privilege escalation
Hermes cannot escalate to `control` capability. The token parser rejects it at
parse time (`_parse_token`), and the daemon blocks control endpoints independently
via `_handle_control_check`. Two independent barriers.

### Replay
Pairing is idempotent. Authority tokens have no nonce or session binding, so
they are replayable within their validity window. Acceptable for LAN-only M1.

### State consistency
Two pairing stores exist: `state/pairing-store.json` (store.py, gateway clients)
and `state/hermes-pairings.json` (hermes.py, Hermes agents) with independent
principal management. This is the most significant architectural issue — the shared
`PrincipalId` invariant is broken (B4).

### File-system safety
JSON store writes are not atomic. Concurrent pairing requests could lose writes.
Acceptable for single-user M1.
