Now I have full context across all files. Let me write the comprehensive review.

---

`★ Insight ─────────────────────────────────────`
The Hermes adapter introduces a **capability-scoped adapter pattern** — a mediator that restricts an external agent to a subset of the system's full API surface. The key architectural question is whether the boundary enforcement is positive (allowlist-based, where Hermes can only call explicitly granted functions) or negative (blocklist-based, where Hermes is blocked from specific endpoints). This distinction is critical because negative enforcement fails open — any new endpoint is accessible by default.
`─────────────────────────────────────────────────`

---

# Hermes Adapter Implementation — Review

## 1. Correctness Issues

### Critical (Blocks End-to-End Flow)

**C1: Token never returned from pair endpoint — Hermes has no way to authenticate.**

`hermes.py:212` calls `_generate_token()` which returns `(token_id, expires_at)`, but `pair_hermes()` stores the expiry on the pairing object and never returns the token_id. The daemon's `/hermes/pair` handler (`daemon.py:276-281`) returns `hermes_id`, `device_name`, `capabilities`, `paired_at` — no token. The `/hermes/connect` endpoint requires an `authority_token` to authenticate. There is no API path for Hermes to obtain its token.

The end-to-end flow is: pair → get token → connect → use. Step 2 is missing.

**C2: CLI has broken imports that crash at runtime.**

- `cli.py:238`: `from . import hermes as hm` — relative import fails in standalone execution (the file uses `sys.path.insert` at the top, line 17-18, which means it's intended to run as `python cli.py`, not as a module). This will raise `ImportError`.
- `cli.py:289`: `from services.home_miner_daemon import hermes as hm_module` — path uses underscores, but the directory is `home-miner-daemon` (hyphens). This will also raise `ImportError`.
- `cli.py:329`: Same broken import as line 289.

**C3: JavaScript TypeError in gateway — `JSON.dumps` is Python, not JavaScript.**

`index.html:735`: `JSON.dumps({...})` should be `JSON.stringify({...})`. This crashes the Hermes re-connect fallback path.

### Significant

**C4: `get_connection_status` always reports `connected: True` for any paired Hermes** (`hermes.py:303-319`). It checks `_get_pairing()` not `_hermes_connections`. A paired-but-not-connected Hermes appears connected. A connected Hermes after daemon restart appears connected (stale pairing data) even though the in-memory session is gone.

**C5: `token_expires_at` on `HermesPairing` is saved to disk as "now" before it's overwritten** (`hermes.py:205,209,213`). The pairing is persisted at line 209 with `token_expires_at=datetime.now()`, then the field is mutated at line 213 after the save. The on-disk pairing has an immediately-expired timestamp. This is cosmetic since the real token expiry lives in `hermes-tokens.json`, but it's confusing state.

**C6: Token expiration is not enforced on active sessions.** `connect()` validates expiry once, then stores the connection in the in-memory dict forever. No periodic check. A Hermes agent stays authorized after its token expires.

**C7: Over-fetch multiplier in `get_filtered_events` is insufficient** (`hermes.py:425`). If the spine has >50% user_message events, `limit * 2` won't yield `limit` readable events. Should iterate until satisfied or accept a best-effort model and document it.

### Minor

**C8: `can_control()` is dead code** (`hermes.py:434-440`). No code path grants `'control'` capability to Hermes. The function exists as a "boundary enforcement helper" but could mask a future capability-injection bug since it tests a dynamic condition (`'control' in connection.capabilities`) rather than returning a constant `False`.

**C9: Test file referenced but doesn't exist.** `review.md:125` mentions `services/home-miner-daemon/tests/test_hermes.py (not yet written)`. The spec's acceptance criteria claim "All adapter tests pass" — no tests exist.

**C10: `fetchHermesStatus()` in index.html fires on every Agent tab visit** and uses a hardcoded fallback token `'hermes-token-001'` that won't exist in the store. Every visit generates a failed connect → pair → failed connect cycle.

---

## 2. Milestone Fit

| Frontier Task | Status | Notes |
|---|---|---|
| Create hermes.py adapter module | **Done** | Module exists, ~450 lines |
| HermesConnection with token validation | **Partial** | Dataclass exists. Token validation logic exists but tokens are unreachable (C1) |
| readStatus through adapter | **Done** | Capability check + miner snapshot delegation works |
| appendSummary through adapter | **Done** | Capability check + spine append works |
| Event filtering (block user_message) | **Done** | Allowlist filter on HERMES_READABLE_EVENTS is correct |
| Hermes pairing endpoint on daemon | **Partial** | Endpoint exists but doesn't return token (C1) |
| Agent tab in gateway | **Partial** | HTML structure exists but JS has crash bug (C3) |
| Tests | **Not started** | No test files exist |

**Verdict:** The structural shape is correct. The adapter module, daemon endpoints, CLI commands, and gateway UI are all present. But the implementation has a broken end-to-end flow (no token return path), runtime crashes (broken imports, JS TypeError), and no tests. This is not shippable as-is.

---

## 3. Nemesis Security Review

### Pass 1 — First-Principles Challenge: Trust Boundaries

**S1 (CRITICAL): Control endpoint blocking is negative/opt-in — Hermes can bypass it by omitting its auth header.**

`daemon.py:329-355`: The miner control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) check `self._get_hermes_auth()` — which looks for `Authorization: Hermes <id>`. If the header is absent, the control action proceeds. This means:

- A Hermes agent that omits the header can control the miner freely
- Any unauthenticated network-adjacent client can also control the miner
- The security boundary is backwards: it blocks honest agents and permits dishonest ones

**The control endpoints have zero authentication.** They don't require any auth — they only reject requests that voluntarily declare themselves as Hermes. This is a "polite fence" not a security boundary.

**S2 (HIGH): Pairing is unauthenticated.**

`POST /hermes/pair` requires no authentication. Any client that can reach the daemon can create a Hermes pairing. When the daemon is configured for LAN binding (`ZEND_BIND_HOST=0.0.0.0`), any device on the network can pair. For milestone 1 at `127.0.0.1`, this is acceptable but must be flagged for the LAN milestone.

**S3 (HIGH): hermes_id is the session credential, and it's user-chosen.**

After `/hermes/connect`, the session is stored at `_hermes_connections[hermes_id]` (`daemon.py:294`). Subsequent requests authenticate with `Authorization: Hermes <hermes_id>` (`daemon.py:189-191`). The hermes_id is chosen by the caller during pairing. This means:
- Session hijacking is trivial if hermes_ids are predictable (e.g., "hermes-001")
- There's no cryptographic binding between the connect token and the session
- The token-based auth is ceremony — the actual auth is just knowing the hermes_id

**S4 (MEDIUM): Tokens stored in plaintext on disk alongside the data they protect.**

`hermes-tokens.json` contains all authority tokens in the same state directory as the pairings and event spine. An attacker with filesystem read access has complete control. For a home device this is somewhat expected, but it should be documented as a known limitation.

**S5 (MEDIUM): No rate limiting on summary append.**

A malicious Hermes agent can spam `POST /hermes/summary` to fill the event spine and inbox with noise, effectively performing a denial of the inbox's usefulness.

### Pass 2 — Coupled-State & Protocol Surfaces

**S6 (HIGH): Three-store state divergence.**

| Store | Location | Lifecycle |
|---|---|---|
| Pairings | `hermes-pairings.json` (disk) | Survives restart |
| Tokens | `hermes-tokens.json` (disk) | Survives restart |
| Sessions | `_hermes_connections` (memory) | Lost on restart |

After daemon restart: pairings exist, tokens exist, sessions are gone. `get_connection_status()` reports "connected" based on pairings (stale). An agent with a valid token can re-connect, which is correct — but the status reporting is wrong.

**S7 (MEDIUM): File-based JSON stores have no locking.**

`ThreadedHTTPServer` handles concurrent requests across threads. Both `_load_tokens()`/`_save_tokens()` and `_load_pairings()`/`_save_pairings()` do read-modify-write without any locking. Concurrent pair or connect requests can corrupt these files (lost writes, truncated JSON).

**S8 (MEDIUM): No replay protection on tokens.**

Authority tokens can be reused any number of times within their 24-hour window. No nonce, no sequence counter, no session binding. A captured token grants full Hermes access until expiry.

**S9 (LOW): Event spine has no principal isolation.**

`get_filtered_events()` returns all events of allowed kinds, regardless of `principal_id`. In a multi-principal deployment, Hermes for one principal sees another principal's events. Acceptable for milestone 1 (single-principal), but latent.

**S10 (LOW): `escapeHtml` in gateway is correctly implemented** — creates a text node and reads innerHTML. XSS via summary_text is mitigated. The one remaining injection surface is if summary text mimics system messages in the inbox, which is a UI deception risk rather than code execution.

---

## 4. Remaining Blockers

To ship this slice:

1. **Fix token return path** — `/hermes/pair` must return the authority token so Hermes can connect
2. **Fix CLI imports** — replace relative imports with the pattern already used at file top
3. **Fix JS `JSON.dumps`** → `JSON.stringify`
4. **Add file locking or serialize state access** — at minimum for token and pairing stores
5. **Write tests** — the spec claims they pass; they don't exist
6. **Add auth to control endpoints** — even for milestone 1, the "polite fence" is not a security boundary. Either require gateway device auth on control endpoints or use a positive allowlist on the Hermes path

---

`★ Insight ─────────────────────────────────────`
**The deepest architectural issue here is S1** — the adapter uses negative enforcement (block Hermes from control) instead of positive enforcement (require auth for control). A well-designed capability system should fail-closed: if you can't prove you're authorized, you can't act. The current design fails-open: if you don't announce you're Hermes, you get full control. This is the difference between an allowlist and a blocklist, and it's a common trap in adapter/proxy patterns where the proxy checks "is this the restricted user?" instead of "is this an authorized user?"
`─────────────────────────────────────────────────`