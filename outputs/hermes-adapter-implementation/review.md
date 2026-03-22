# Hermes Adapter Implementation — Review

**Status:** Ready for Implementation
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22
**Reviewed by:** Claude Opus 4 (review stage)

---

## Executive Summary

The specify stage produced no artifacts. The `MiniMax-M2.7-highspeed` run generated 0 tokens of output — no code, no spec prose, no decisions. The lane arrived at this review with nothing implemented and all six frontier tasks unstarted.

The implementation foundation is present and reviewed: `references/hermes-adapter.md`, `references/event-spine.md`, and `references/inbox-contract.md` define a coherent contract. The daemon code in `services/home-miner-daemon/` provides `spine.py`, `store.py`, and `daemon.py` as concrete substrates. The gap is entirely in the adapter layer.

**Verdict: Ready to implement. This review provides the trace-level security analysis and concrete implementation guidance the next stage needs.**

---

## Frontend Task Readiness

| Frontier Task | Readiness | Evidence |
|---------------|-----------|---------|
| Create `hermes.py` adapter module | READY | No file exists; create from spec contract |
| `HermesConnection` with authority token validation | READY | `GatewayPairing` dataclass exists in `store.py`; needs `token_used` and expiration enforcement |
| `readStatus` through adapter | READY | `miner.get_snapshot()` exists in `daemon.py:118`; adapter must gate it |
| `appendSummary` through adapter | READY | `spine.append_hermes_summary()` exists in `spine.py:103`; adapter must gate and set Hermes's own principal |
| Event filtering (block `user_message`) | READY | `spine.get_events()` accepts optional `kind` filter; adapter must apply positive allowlist |
| Hermes pairing endpoint | READY | `daemon.py` has `ThreadedHTTPServer` pattern; new route registration is straightforward |

---

## Code Trace Analysis

### `store.py:create_pairing_token()` — Token Expiration Bug

```
services/home-miner-daemon/store.py:84-90
```

```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()   # ← born expired
    return token, expires
```

`expires` is set to `datetime.now(timezone.utc)` — the instant of creation. No code currently checks expiration, so this is a latent bug. The moment any code adds `if datetime.now(tz) > expires: reject()`, every token ever issued will be rejected.

**Impact on Hermes adapter:** `POST /hermes/pair` must issue a corrected token with a future expiration. `connect()` must perform the expiration check and must also handle the pre-existing expired tokens that already exist in `state/pairing-store.json`.

**Fix:** `expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()`

### `store.py:pair_client()` — Token Replay Bug

```
services/home-miner-daemon/store.py:92-113
```

The `GatewayPairing` dataclass has `token_used: bool = False` as a field. `pair_client()` stores it in the pairing record. No function anywhere in the codebase sets `token_used = True` after a token is consumed. The field is dead code.

**Impact on Hermes adapter:** Any authority token can be used multiple times to create duplicate pairings. The replay check must be added as a new `consume_token()` function or inline in `connect()`.

### `spine.py:append_hermes_summary()` — Principal Identity

```
services/home-miner-daemon/spine.py:103-114
```

```python
def append_hermes_summary(summary_text: str, authority_scope: list, principal_id: str):
    return append_event(
        EventKind.HERMES_SUMMARY,
        principal_id,    # ← caller controls this
        {
            "summary_text": summary_text,
            "authority_scope": authority_scope,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    )
```

The `principal_id` argument is opaque to the spine. Any caller can stamp any principal. The `hermes_summary_smoke.sh` script passes `load_or_create_principal().id` — the owner's principal — so Hermes summaries in the event spine are indistinguishable from owner actions. The adapter must pass Hermes's own principal, not the owner's.

### `spine.py:get_events()` — No Caller-Scoped Filtering

```
services/home-miner-daemon/spine.py:68-78
```

```python
def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    events = _load_events()
    if kind:
        events = [e for e in events if e.kind == kind.value]
    events.reverse()
    return events[:limit]
```

`get_events()` trusts the caller to self-restrict. If a caller requests `kind=EventKind.USER_MESSAGE`, it receives all user messages. The adapter must not pass through a caller-controlled `kind` parameter — it must apply its own positive allowlist internally and ignore any caller request for blocked kinds.

### `daemon.py:GatewayHandler` — No Auth on Control Endpoints

```
services/home-miner-daemon/daemon.py:130-154
```

All `/miner/start`, `/miner/stop`, and `/miner/set_mode` endpoints are unauthenticated and unescaped from localhost. For milestone 1 LAN-only scope, this is an accepted limitation provided the adapter is the exclusive Hermes-facing surface. However, if Hermes runs on the same host, it can bypass the adapter entirely and call the daemon directly. This is acceptable for milestone 1 but must be documented as a LAN-isolation requirement.

### `hermes_summary_smoke.sh` — Direct Spine Call

```
scripts/hermes_summary_smoke.sh
```

The script invokes:
```python
python3 -c "
import sys; sys.path.insert(0, 'services/home-miner-daemon')
from spine import append_hermes_summary
from store import load_or_create_principal
p = load_or_create_principal()
append_hermes_summary('smoke test', ['observe'], p.id)
"
```

This bypasses the adapter entirely. The rewrite must call `POST /hermes/summary` at `http://localhost:8080/hermes/summary` with the Hermes authority token in `X-Hermes-Token`.

---

## Security Findings

| ID | Severity | Location | Finding | Recommendation |
|----|----------|----------|---------|----------------|
| R1 | HIGH | `store.py:89` | Token expiration set to creation time; all tokens born expired | Fix `create_pairing_token()` to set future expiration; `connect()` must check it |
| R2 | HIGH | `spine.py:103` | Hermes summaries stamped with owner's principal; event spine cannot distinguish owner from Hermes | Adapter must issue Hermes its own `PrincipalId` during pairing and pass it to `append_hermes_summary()` |
| R3 | HIGH | `spine.py:68` | `get_events()` has no caller-scope filtering; `user_message` accessible to any caller | Adapter `get_events()` applies positive allowlist; blocks `user_message` silently |
| R4 | HIGH | `store.py` | `token_used` field declared but never set; token replay unblocked | New `consume_token()` function; `connect()` calls it and raises on already-used |
| R5 | MEDIUM | `daemon.py:130` | `/miner/*` endpoints unauthenticated; Hermes on same host could bypass adapter | Document as LAN-isolation requirement for milestone 1; not a blocker |
| R6 | MEDIUM | `daemon.py` | No Hermes-specific routes exist | Implement `hermes_handlers.py` with `HermesHandler` class; register at `/hermes/*` |
| R7 | LOW | `spine.py` | No idempotency for summary appends; duplicate Hermes retries create duplicate events | Consider idempotency key in payload; defer to future lane |
| R8 | LOW | `hermes_summary_smoke.sh` | Smoke test bypasses adapter boundary | Rewrite to use `POST /hermes/summary` HTTP endpoint |

Findings R1–R4 are pre-existing bugs that the adapter must either fix or work around. Findings R5–R6 are gaps the adapter must fill. Findings R7–R8 are nice-to-have for milestone 1.

---

## Implementation Order

The review recommends this implementation sequence to keep each step independently verifiable:

1. **Fix `store.py:create_pairing_token()`** — set `expires` to 24 hours in the future. Run the existing smoke script to confirm pairing still works after the fix.

2. **Add `consume_token()` to `store.py`** — marks `token_used = True` and raises on already-used. Write a small test that issues a token, consumes it twice, and observes the second call rejected.

3. **Create `services/home-miner-daemon/hermes.py`** — implement `HermesConnection`, `connect()`, `requires()`, `read_status()`, `append_summary()`, `get_events()`. At this stage `connect()` only validates against the pairing store; daemon routes come next.

4. **Add Hermes HTTP handlers** — `HermesHandler` or `hermes_handlers.py` with routes for `/hermes/pair`, `/hermes/status`, `/hermes/summary`, `/hermes/events`. Wire `X-Hermes-Token` extraction into the adapter's `connect()` call. Register handlers with the existing `ThreadedHTTPServer`.

5. **Rewrite `hermes_summary_smoke.sh`** — replace the direct spine import with a `POST /hermes/summary` call using the token from `/hermes/pair`.

6. **Add integration assertions** — the adapter's event filtering can be proven by appending a `user_message` event directly to the spine, then calling `GET /hermes/events` and confirming it is absent from the result.

---

## What This Lane Does NOT Cover

- Signed JWT/SASL authority tokens (future lane)
- Hermes `control` capability (future lane)
- Hermes inbox message access (future lane)
- Idempotency for summary appends (future lane)
- Daemon endpoint-level auth (accepted limitation for LAN-only milestone 1)
- Full automated test suite (future lane)
