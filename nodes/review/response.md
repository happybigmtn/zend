

`★ Insight ─────────────────────────────────────`
This review crosses documentation accuracy, security posture, and state consistency. The key tension in this codebase is that the **CLI layer pretends to be a security boundary** (capability checks) while the **HTTP daemon is wide open**. Documentation that conflates these two layers creates a false sense of security for operators.
`─────────────────────────────────────────────────`

---

# Documentation & Onboarding — Lane Review

## Verdict: **Qualified Pass with Blockers**

The lane produced all required artifacts, the docs are well-structured, and several real daemon bugs were found and fixed during verification. But the review claims "complete and accurate" while the docs contain fabricated claims, a functional blocker in the recommended operator flow, and a CLI bug that will crash on use.

---

## 1. Correctness — Documentation vs. Code

### BLOCKING: False claims that will mislead operators

| Doc claim | Reality | Severity |
|-----------|---------|----------|
| `operator-quickstart.md:424` — "Event spine payloads are encrypted at rest" | `spine.py` writes plain JSON to `event-spine.jsonl`. Zero encryption. The module docstring (`spine.py:3`) says "encrypted event journal" — aspirational, not actual. | **High** — operators may store sensitive data trusting this claim |
| `operator-quickstart.md:63` — `ZEND_TOKEN_TTL_HOURS` env var with default 720 (30 days) | This env var does not exist anywhere in the code. `store.py:89` sets `token_expires_at` to `datetime.now()` — tokens expire **immediately** at creation. No code ever checks expiration. | **High** — fabricated feature |
| `api-reference.md:58,106` — Endpoints "Require `observe` or `control` capability" | The daemon has **zero auth**. Any device that can reach port 8080 can call any endpoint. Capability checks only exist in the CLI (`cli.py`), not the HTTP layer. | **High** — misleading security posture |
| `api-reference.md:400` — HTTP `401 unauthorized` error code | No daemon endpoint ever returns 401. The daemon has no auth concept. | **Medium** |

### BLOCKING: CLI `events --kind` will crash

`cli.py:190-191` passes a raw string to `spine.get_events(kind=...)`, but `spine.py:87` calls `kind.value` on it — which raises `AttributeError` on a plain string. The daemon's `/spine/events` endpoint correctly converts to `EventKind` first (`daemon.py:193`), but the CLI doesn't.

```
$ python3 cli.py events --client alice-phone --kind control_receipt
→ AttributeError: 'str' object has no attribute 'value'
```

The review claims "All CLI commands are accurate ✅" — this specific command was either not tested or was tested differently.

### BLOCKING: CORS will break the documented operator LAN setup

`operator-quickstart.md:219-224` recommends:
```bash
python3 -m http.server 9000 --directory apps/zend-home-gateway
```

The HTML gateway fetches from `http://127.0.0.1:8080` (hardcoded in `index.html:632`). When served from a different origin (`http://<server-ip>:9000`), the browser will block cross-origin requests because `daemon.py` sends no CORS headers. The documented operator flow **will not work** in a browser.

### Non-blocking accuracy issues

| Issue | Location |
|-------|----------|
| README architecture diagram omits `GET /spine/events` — added during this lane but not reflected | `README.md:31-55` |
| README directory structure omits `scripts/fetch_upstreams.sh` | `README.md:74` |
| `daemon.py` has duplicate `import os` (lines 3 and 16) | `daemon.py:3,16` → line 3 is actually `import sys`, then `import os` at line 16 is fine. Wait — line 13 is `import os` and line 16... let me recheck. Lines 13-14: `import os` / `import sys`. Then line 20 is another `import os` after the `sys.path.insert`. **Confirmed duplicate.** |
| `architecture.md:299` claims "No locking needed for appends" — not true under Python threading with the `ThreadedHTTPServer` | `spine.py:64` uses file open/append per call with no lock |

---

## 2. Milestone Fit

| Required artifact | Delivered | Quality |
|-------------------|-----------|---------|
| `README.md` rewrite | ✅ | Good — 156 lines, clean structure, quickstart works for local dev |
| `docs/contributor-guide.md` | ✅ | Good — thorough onboarding, accurate project structure |
| `docs/operator-quickstart.md` | ✅ | Contains fabricated claims (encryption, TTL env var) and broken LAN flow |
| `docs/api-reference.md` | ✅ | Misleading auth claims, CLI events --kind bug |
| `docs/architecture.md` | ✅ | Best doc in the set — honest about what exists, good data flow diagrams |
| `outputs/.../spec.md` | ✅ | Accurate system understanding |
| `outputs/.../review.md` | ✅ | Claims "complete and accurate" without flagging the issues above |
| Verification on clean machine | ⚠️ | Partial — local dev flow verified, LAN operator flow not actually tested |

The lane's bug-finding during verification (enum serialization, missing `/spine/events` endpoint) demonstrates real diligence. The problem is that the review then over-claims verification completeness.

---

## 3. Nemesis Security Review

### Pass 1 — First-Principles Trust Boundaries

**The daemon has no security boundary.** The entire capability/pairing system is an advisory UX layer in the CLI. The HTTP daemon is a naked, unauthenticated control surface.

| Surface | Who can trigger | What they can do |
|---------|-----------------|------------------|
| `POST /miner/start` | Any LAN device | Start mining |
| `POST /miner/stop` | Any LAN device | Stop mining |
| `POST /miner/set_mode` | Any LAN device | Change mode to performance |
| `GET /status` | Any LAN device | Read all miner state |
| `GET /spine/events` | Any LAN device | Read full audit trail |
| `GET /health` | Any LAN device | Probe daemon existence |

**No CSRF protection.** Any webpage loaded in a browser on the LAN can `fetch('http://192.168.x.x:8080/miner/start', {method:'POST'})`. The daemon will happily comply.

**PrincipalId is not a secret.** It's a UUID in a plain JSON file. It's included in every spine event and returned in API responses. It provides identity labeling, not authentication.

**Token expiration is broken.** `create_pairing_token()` (`store.py:86-90`) sets `token_expires_at = datetime.now()` — immediately expired. No code path ever checks this field.

### Pass 2 — Coupled-State Consistency

**Daemon state vs. spine divergence on restart.** The miner state is in-memory only (`MinerSimulator`). The spine persists forever. After a daemon restart:
- Spine says: "set_mode balanced, accepted" (historical)
- Daemon says: status=stopped, mode=paused (fresh)
- No reconciliation mechanism exists

**Pairing store vs. spine ordering in `cmd_pair`.** `cli.py:103-115`:
1. `pair_client()` writes to `pairing-store.json`
2. `append_pairing_requested()` writes to spine
3. `append_pairing_granted()` writes to spine

If step 1 succeeds but step 2 fails (disk full, permission error), you have a paired device with no audit trail. The spine is supposed to be the source of truth, but the store is written first.

**`cmd_bootstrap` doesn't append `pairing_requested`.** `cli.py:73-95` — bootstrap creates the principal and pair, then appends `pairing_granted` but never `pairing_requested`. This breaks the "every pairing starts with a request" invariant documented in the event spine schema.

### Pass 3 — External Process Control & Operator Safety

**`rm -rf state/*` destroys identity permanently.** Multiple docs recommend this as recovery (`contributor-guide.md:338`, `operator-quickstart.md:337`). This destroys the `PrincipalId`. If the principal is ever shared with external systems (inbox, Hermes, other devices), this is an identity-destroying operation with no recovery path. The docs should warn about this consequence.

**systemd unit doesn't bootstrap.** The operator guide's systemd `ExecStart` (`operator-quickstart.md:304`) runs `daemon.py` directly. This starts the HTTP server but doesn't create the PrincipalId or pair any device. A fresh install following only the systemd instructions will have an empty `state/` directory. The guide should add a `ExecStartPre` or a note about running bootstrap first.

**`kill -9` in stop_daemon.** `bootstrap_home_miner.sh:54` — force-kills after 1 second. Currently low-impact since the daemon doesn't persist state, but this pattern will cause data loss when the daemon manages more state.

**JSONL concurrent append safety.** `spine.py:64` opens the file and appends with no lock. The `ThreadedHTTPServer` can service concurrent requests. Two simultaneous spine appends from different threads could interleave partial JSON lines, corrupting the spine file. `architecture.md:299` claims "No locking needed for appends" — this is incorrect under threading.

---

## 4. Required Fixes Before This Lane Ships

### Must fix (blockers)

1. **Remove false encryption claim** from `operator-quickstart.md:424` and `spine.py:3` docstring
2. **Remove fabricated `ZEND_TOKEN_TTL_HOURS`** from `operator-quickstart.md:63` and the "30 days" claim
3. **Fix CLI `cmd_events`** to convert string to `EventKind` before passing to `get_events()`
4. **Add CORS headers** to `daemon.py` `_send_json` (at minimum `Access-Control-Allow-Origin: *` for local LAN use), or document that the HTML gateway must be served from the same origin
5. **Clarify API reference auth model** — state explicitly that the HTTP daemon has no auth and that capability checking is CLI-only

### Should fix

6. **Add `GET /spine/events`** to README architecture diagram
7. **Fix duplicate `import os`** in `daemon.py`
8. **Add systemd bootstrap note** to operator guide
9. **Warn about PrincipalId loss** in `rm -rf state/*` recovery sections
10. **Add threading lock** to `spine.py` `_save_event` (or document the concurrency limitation)

---

`★ Insight ─────────────────────────────────────`
The core architectural tension here is **advisory auth vs. real auth**. The CLI checks capabilities, but the daemon trusts everyone. This is fine for milestone 1 as long as the docs are honest about it. The danger is when docs describe the advisory layer as if it's a security boundary — operators will deploy with a false sense of protection. The fix isn't to add auth now; it's to make the docs say "LAN-only, no HTTP auth, capability checking is CLI-side only" loudly and clearly.
`─────────────────────────────────────────────────`