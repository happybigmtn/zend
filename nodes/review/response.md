All 19 tests pass. Now I have full context. Let me write the review.

---

# Hermes Adapter Implementation — Nemesis Review

`★ Insight ─────────────────────────────────────`
The auto-generated review (from MiniMax-M2.7) is a **rubber stamp**. It says "approved for merge" and calls the implementation "production-ready" while missing multiple security-critical issues. This is exactly why Nemesis review exists — to challenge the first reviewer's assumptions. The specify-model generated working code that passes its own tests, but the security boundary enforcement has real holes.
`─────────────────────────────────────────────────`

## Pass 1 — First-Principles Challenge: Trust Boundaries and Authority

### CRITICAL: Unauthenticated Pairing (No Trust Ceremony)

`hermes.py:171-239` — `pair_hermes()` and `daemon.py:295-331` — `/hermes/pair`

The product spec explicitly requires:
> "Hermes connects through a Zend adapter and receives only the capabilities and event surfaces **Zend explicitly grants**."
> "Zend milestone 1 includes a first-class trust ceremony. Pairing must feel safe, named, and revocable."

**What happens**: Any process on the LAN can `POST /hermes/pair` with any `hermes_id` and receive a valid authority token. No approval, no challenge, no user confirmation. The "trust ceremony" is completely absent for Hermes pairing.

The gateway pairing (`store.py:pair_client`) at least requires explicit CLI invocation. Hermes pairing has an open HTTP endpoint. This means any compromised LAN device can self-register as a Hermes agent and gain `observe` + `summarize` capabilities — reading miner state and writing to the event spine.

**Blast radius**: An attacker can silently observe miner operations and inject arbitrary summary text into the user's inbox without any user awareness.

### CRITICAL: Hermes Control Block is Trivially Bypassable

`daemon.py:260-293` — Control endpoint protection:

```python
if hermes_auth_or_none(self.headers):
    self._send_json(403, {"error": "HERMES_UNAUTHORIZED", ...})
    return
```

`hermes_auth_or_none` returns `None` for invalid/expired tokens AND for missing headers. The logic is: "if this is a **valid** Hermes session, block control." A Hermes agent that wants to bypass the control block simply omits its `Authorization` header or sends a garbage token. Result: the check returns `None`, falls through, and the control command executes.

This is **defense by negative detection** — checking "is this definitely Hermes?" rather than "is this authorized to control?" The correct approach is **positive authorization**: control endpoints should require a gateway Bearer token with `control` capability. Blocking a known Hermes identity is defense-in-depth, not the primary gate.

**Proof of bypass**: A Hermes agent knows its token. It can send `POST /miner/start` without any Authorization header, and the miner starts. The 403 block only fires when the agent honestly identifies itself.

### HIGH: Token Expiration Calculation is Wrong

`hermes.py:192-195`:
```python
now = datetime.now(timezone.utc)
expires = datetime.now(timezone.utc)
expires = expires.replace(hour=23, minute=59, second=59)
```

This does NOT create a 24-hour token as claimed in the spec and review. It creates a token that expires at 23:59:59 UTC **on the same calendar day**. If you pair at 23:00 UTC, the token expires in ~1 hour. If you pair at 00:01 UTC, it expires in ~24 hours. The behavior depends entirely on when you pair, and the spec says "24 hours."

Additionally, `replace()` doesn't change the date — so a token issued at 23:50 UTC expires 9 minutes later, not 24 hours later.

### HIGH: Re-Pair Leaks Old Tokens

`hermes.py:199-237` — When `pair_hermes()` is called for an existing `hermes_id` (the "idempotent" path):

1. A new token UUID is generated (line 197)
2. The pairing record is updated with the new token (line 209)
3. The new token is saved to the token store (lines 229-237)

**The old token is never removed from the token store.** Each re-pair creates an additional valid token while the old one remains valid until it expires. The test at line 218 correctly asserts `pairing1.token != pairing2.token`, but never checks that `pairing1.token` is invalidated. Both tokens work.

An attacker who observes one pairing response has a token that survives re-pairing.

### HIGH: `/hermes/pairings` Lists All Pairings Without Authentication

`daemon.py:245-246` and `daemon.py:418-433`:

The `/hermes/pairings` endpoint returns all Hermes pairing records with no auth check. While it doesn't return tokens in the response (good), it leaks `hermes_id`, `device_name`, `capabilities`, `paired_at`, and `token_expires_at` to any LAN observer. This is information disclosure that aids reconnaissance.

---

## Pass 2 — Coupled-State and Storage Consistency

### MEDIUM: Pairing/Token Store Shares One File, Fights Over Keys

`hermes.py:101-136`:

Both `_save_hermes_pairings` and `_save_hermes_tokens` read/write `hermes-tokens.json`. The pairings save function **strips** the `tokens` key (line 114), while the tokens save function **reads the pairings, injects `tokens`, and writes the whole thing**.

Concurrent writes will clobber each other. No file locking. In a threaded HTTP server (`ThreadedHTTPServer` uses `ThreadingMixIn`), two simultaneous Hermes requests could corrupt the store.

The `list_hermes_pairings` function (line 400-407) has to manually skip `key == 'tokens'` — a code smell that proves the storage model is confused.

### MEDIUM: Token Not Bound to Current Principal

`hermes.py:148-168` — `validate_authority_token()` verifies token existence and expiration but never checks that the `principal_id` in the token matches the current system principal. If the principal file is deleted and recreated (e.g., during recovery), old Hermes tokens reference a stale principal_id. The connection would succeed with a phantom identity.

### LOW: `verify_connection_auth` is Dead Code / Misleading

`hermes.py:356-364`:

```python
def verify_connection_auth(connection: HermesConnection, required_capability: str = None) -> bool:
    if required_capability:
        return required_capability in connection.capabilities
    return True
```

This function doesn't verify auth — it checks an in-memory list. Once a `HermesConnection` is created, it's valid in memory forever, even if the underlying token is revoked. The function is never called anywhere in the codebase. Dead code that could mislead future developers into thinking connections are re-validated.

### LOW: `get_filtered_events` Over-Fetch Heuristic Doesn't Guarantee Limit

`hermes.py:317-335`:

```python
all_events = get_events(limit=limit * 2)
```

If Hermes-readable events are sparse (e.g., 1 in 100), requesting `limit=20` fetches 40 events, filters to maybe 0-1 results, and returns far fewer than 20. The heuristic is fine for dense cases but silently under-delivers for sparse cases.

### LOW: `authority_scope` Not Validated in `append_summary`

`hermes.py:297-314`:

The `authority_scope` parameter is passed directly into the event payload without validation. A Hermes agent can write any string here, including strings that impersonate higher-privilege scopes (e.g., "control"). While this doesn't grant actual capabilities, it pollutes the event spine with misleading metadata.

### LOW: Unnecessary I/O on Every GET Request

`daemon.py:233-234`:

```python
def do_GET(self):
    hermes_conn = hermes_auth_or_none(self.headers)
```

Every GET request — including `/health` — attempts Hermes auth extraction, which reads and parses the Hermes tokens JSON file from disk. This is wasted I/O for non-Hermes endpoints.

### LOW: Redundant `sys.path.insert` in hermes.py

`hermes.py:27-28`:

```python
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

The bare imports of `spine` and `store` on lines 23-24 already work (Python adds the script's directory to the path). The explicit `sys.path.insert` is redundant and risks shadowing standard library modules if this directory contains files with colliding names.

---

## Spec Fit Assessment

| Spec Requirement | Status | Issue |
|---|---|---|
| Hermes connects through Zend adapter with explicitly granted authority | **FAIL** | Pairing is unauthenticated — authority is self-granted |
| First-class trust ceremony for pairing | **FAIL** | No ceremony, no approval flow |
| Hermes cannot issue control commands | **PARTIAL** | Block works only when Hermes honestly identifies itself |
| Hermes cannot read user_message events | **PASS** | Allowlist filter is correct |
| Observe capability reads miner status | **PASS** | Works correctly |
| Summarize capability appends to spine | **PASS** | Works correctly |
| Token valid for 24 hours | **FAIL** | Expires at end of UTC day, not +24h |
| Idempotent re-pairing | **FAIL** | Old tokens leak on re-pair |
| LAN-only binding | **PASS** | Binds to 127.0.0.1 by default |

---

## Remaining Blockers

1. **Pairing must require user approval** — either a CLI confirmation, a trust sheet (per DESIGN.md), or at minimum a pre-shared secret. Open pairing violates the spec's trust model.

2. **Control endpoints need positive authorization** — not negative Hermes detection. The current approach is bypassable. Control should require a Bearer token with `control` capability.

3. **Fix token expiration** — replace `expires.replace(hour=23, ...)` with `now + timedelta(hours=24)`.

4. **Revoke old tokens on re-pair** — delete the previous token from the store before saving the new one.

5. **Separate the storage files** — pairings and tokens should not share a JSON file, or at minimum use file locking.

---

## Verdict

**NOT approved for merge.**

The code is structurally sound — data flows correctly, the capability model is well-separated, tests cover the happy path and basic boundaries, and the event filtering allowlist is correct. The specify model did a creditable job building the adapter shape.

But the security boundaries have real holes that contradict the product spec's trust model. The three critical issues (unauthenticated pairing, bypassable control block, token expiration bug) need fixing before this slice can honestly claim it enforces the Hermes capability boundary.

The auto-generated review missed all of these because it tested whether the code does what the code says — not whether the code does what the **spec** says.

`★ Insight ─────────────────────────────────────`
**Defense by negative detection vs. positive authorization**: The control block checks "is this definitely Hermes?" instead of "is this authorized to control?" This is a common security anti-pattern. Negative detection (blocklisting) is always bypassable because the adversary controls their identity presentation. Positive authorization (allowlisting) is the correct pattern: control endpoints should require proof of `control` capability, not absence of Hermes identity.

**Token expiration with `replace()` vs `timedelta()`**: `datetime.replace()` sets absolute field values, not offsets. It's a subtle but critical distinction — `replace(hour=23)` means "23:00 today" not "23 hours from now." For time-offset calculations, always use `timedelta`.

**Append-only stores need garbage collection for revoked/expired entries**: The token store grows unboundedly because expired tokens are never cleaned up and re-pairing leaks old tokens. In an append-only system design, you need a separate compaction or expiry sweep.
`─────────────────────────────────────────────────`