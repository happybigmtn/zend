Now I have the full picture. Here's my Nemesis-style review.

---

## Lane Review: `carried-forward-build-command-center`

### Correctness of Lane Artifacts

The spec and review are structurally sound documents — they catalog the implementation accurately and identify real gaps. However, the review performed by the genesis sprint is **insufficiently adversarial**. It found surface-level issues (token replay, missing tests) but missed deeper architectural trust violations.

---

### Pass 1 — First-Principles Trust Challenge

#### CRITICAL: The daemon has no access control at all

The review's "Gap 1" (token replay) is a distraction from the real problem: **the daemon HTTP API is completely unauthenticated**. There is no auth header, no bearer token, no session, no CORS restriction. `daemon.py:176-200` accepts `POST /miner/start`, `/miner/stop`, `/miner/set_mode` from any HTTP client without checking who is calling.

The review states capability scoping "works" and cites the CLI's `has_capability()` check as evidence. This is wrong. The CLI enforces capabilities **client-side** — any process that speaks HTTP can bypass the CLI entirely and control the miner directly:

```
curl -X POST http://127.0.0.1:8080/miner/start
```

No pairing token, no capability, no principal ID needed. The capability model is theatrical: it exists in `store.py` and `cli.py` but the daemon — the actual authority — doesn't participate.

**Verdict:** The spec's acceptance criterion "Observer clients cannot issue control commands" (line 216) is **false**. It is only true when the observer uses the CLI. Direct HTTP access bypasses all controls.

#### CRITICAL: The gateway client hardcodes capabilities

`index.html` stores `capabilities: ['observe', 'control']` in client-side state (confirmed by the explore agent). These are never verified against the pairing store. Any user can open devtools and set any capability. The client polls `/status` and posts to `/miner/set_mode` directly — the daemon accepts unconditionally.

#### HIGH: Token expiration is set to NOW, not the future

`store.py:89`:
```python
expires = datetime.now(timezone.utc).isoformat()
```

This creates tokens that are **immediately expired**. Even if expiration checking existed, every token would fail. This is either a bug (intended `+ timedelta(hours=24)`) or a stub that was never completed. The review says "token replay prevention is not enforced" but doesn't catch that the expiration logic is also broken at the value level.

#### HIGH: Pairing emits `pairing_granted` before `pairing_requested` in bootstrap

`cli.py:73-95` — `cmd_bootstrap()` calls `pair_client()` (which creates the record), then emits `pairing_granted`. It never emits `pairing_requested`. The event spine shows a grant without a request — the audit trail is incomplete for the bootstrap flow.

Meanwhile, `cmd_pair()` (line 98-128) emits both events, but **after** the pairing is already created in the store. If either spine append fails, the pairing exists but the audit trail doesn't reflect it.

---

### Pass 2 — Coupled-State Review

#### State pair: pairing-store.json ↔ event-spine.jsonl

These are coupled but not transactional. `pair_client()` in `store.py` writes to `pairing-store.json` first, then the caller (`cli.py`) appends spine events separately. If the process crashes between these steps:
- **Pairing exists, spine doesn't know** — a device is paired but there's no audit record
- **Recovery requires comparing store to spine** — no reconciliation mechanism exists

This is the classic "two-file transaction" problem. The spec acknowledges the spine is "source of truth" but the store can diverge from it silently.

#### State pair: MinerSimulator._status ↔ event-spine.jsonl

Control commands in `cli.py:131-176` hit the daemon first (changing miner state), then append a control receipt to the spine. If the spine append fails:
- The miner state has changed
- No audit record exists
- The receipt is silently lost

The miner's in-memory state and the spine's on-disk log can disagree. No recovery path exists.

#### State pair: capabilities in pairing-store.json ↔ capabilities in HTML client state

The HTML client's capabilities are hardcoded and never refreshed from the server. If an operator revokes a capability by modifying the pairing store, the client continues operating with its cached (stale) capabilities. Since the daemon doesn't check capabilities either, the revocation has no effect.

#### Idempotence: daemon control commands

`daemon.py:88-104` — `start()` returns `{"success": False, "error": "already_running"}` if called twice. This is correct for state protection but creates a usability issue: the CLI interprets any non-success as a failure and still appends a `"rejected"` control receipt to the spine (cli.py:156). A harmless retry pollutes the audit trail.

#### JSONL append atomicity

`spine.py:62-65` — `_save_event()` uses `open(SPINE_FILE, 'a')` and `f.write(json.dumps(...) + '\n')`. Python's `write()` is not guaranteed atomic for large payloads. If the payload exceeds the pipe buffer or the process is killed mid-write, a partial JSON line can corrupt the entire spine file. Subsequent `_load_events()` would crash on `json.loads(line)` with no recovery.

---

### Pass 3 — Secret Handling, Privilege Escalation, Service Lifecycle

#### Secret handling

- **PrincipalId is a UUID** — predictable format, no cryptographic binding. Any process that reads `principal.json` can impersonate the principal.
- **Pairing tokens are UUIDs** — same issue. The token provides no proof of identity.
- **State files use default permissions** — `os.makedirs(STATE_DIR, exist_ok=True)` with no `chmod`. On a shared machine, other users can read `principal.json`, `pairing-store.json`, and `event-spine.jsonl`.
- **Event spine payloads are plaintext** — the docstring says "append-only encrypted event journal" but no encryption exists. The contract (`event-spine.md`) mentions encryption, the implementation doesn't deliver it.

#### Privilege escalation paths

1. **Observer → Controller via direct HTTP**: Any paired observer (or unpaired process) can POST to `/miner/start` directly
2. **No-auth → Full access via localhost**: Any process on localhost can control the miner without any pairing
3. **Hermes authority self-declaration**: `append_hermes_summary()` accepts an `authority_scope` list from the caller. Hermes (or any caller) can claim arbitrary authority in its spine events

#### Service lifecycle

- **Daemon has no graceful shutdown persistence** — in-memory miner state (running/stopped/mode) is lost on restart. No state file records the last-known miner state.
- **`ThreadedHTTPServer` with `allow_reuse_address=True`** — if the daemon crashes and restarts quickly, the socket reuse avoids bind failures. This is correct.
- **No PID file or lock** — multiple daemon instances can bind to different ports or race on state files.

#### `ZEND_BIND_HOST` escape hatch

The daemon binds to `127.0.0.1` by default but `ZEND_BIND_HOST` is a plain env var. Setting it to `0.0.0.0` exposes an unauthenticated API to the network. The review says "LAN-only binding enforced" — it's enforced by convention, not by code. There is no warning, validation, or network-level safeguard.

---

### Milestone Fit

The spec claims the slice delivers a "first honest reviewed slice" with these acceptance criteria checked:

| Criterion | Spec Claim | Actual |
|-----------|-----------|--------|
| Observer clients cannot issue control commands | Checked | **False** — daemon has no auth |
| Control commands produce receipts via event spine | Checked | Partially true — receipts can silently fail |
| Event spine appends are atomic and ordered | Checked | **Debatable** — no atomic write guarantee |
| No mining code in client HTML/JS | Checked | True |
| Daemon serves HTTP on localhost | Checked | True |
| Status reads return fresh snapshots | Checked | True |
| Pairing creates PrincipalId and capability-scoped records | Checked | True (records exist, enforcement doesn't) |

The slice is a **functional demo**, not a security milestone. It proves the architecture can work, but the trust boundaries exist only in documentation and client-side code, not in the daemon.

---

### Genesis Plan References — Phantom

Both the spec and review reference genesis plans 003-014 repeatedly. **No genesis plans directory or files exist** in the repository (`genesis/plans/` is empty). Every "addressed by genesis plan X" claim is a forward reference to work that hasn't been specified yet. The review's "Remaining Items (Mapped to Genesis Plans)" table maps 12 work items to plans that don't exist.

This isn't necessarily wrong — the genesis plans may be future work — but the artifacts should be honest about this. Saying "token replay prevention: addressed by genesis plan 003" when plan 003 doesn't exist is equivalent to saying "token replay prevention: TBD."

---

### Remaining Blockers Before This Slice Can Be Called "Reviewed"

1. **Daemon auth is mandatory** — Without server-side capability enforcement, the entire capability model is cosmetic. The daemon must verify the caller's identity and capabilities on every request.
2. **Token expiration bug must be fixed** — `datetime.now()` instead of `datetime.now() + timedelta(...)` makes all tokens immediately expired.
3. **State file transactions** — The store-then-spine pattern must either be made transactional or the failure modes must be documented and accepted.
4. **Genesis plans must exist or the references must be removed** — Citing nonexistent plans creates false confidence in the roadmap.
5. **"Encrypted event journal" claim must be reconciled** — Either implement encryption or remove the claim from the docstring and contracts.

---

`★ Insight ─────────────────────────────────────`
**Client-side enforcement is not enforcement.** The core architectural flaw here is a pattern seen in many early-stage systems: authorization logic lives in the CLI and frontend but not at the API boundary (the daemon). This is analogous to a web app that checks permissions in JavaScript but not on the server. The fix isn't to move checks around — it's to recognize that the daemon is the **trust boundary** and all authorization must happen there. The CLI and frontend are convenience layers, not security layers.

**Two-file transactions require explicit failure semantics.** When `store.py` and `spine.py` write to different files, any crash between writes creates inconsistency. The options are: (a) write-ahead log so the spine is the only write and the store is derived, (b) an explicit reconciliation pass on startup, or (c) document that the store can be ahead of the spine and accept the audit gap. The current code does none of these.
`─────────────────────────────────────────────────`