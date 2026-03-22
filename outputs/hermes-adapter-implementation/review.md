# Hermes Adapter Implementation Lane — Review

**Status:** BLOCKED — No Implementation Exists
**Reviewed:** 2026-03-22
**Reviewer:** Nemesis-style security review (2-pass)

## Executive Summary

The `hermes-adapter-implementation` lane has **no deliverables**. The specify stage
reported success but produced 0 tokens (MiniMax-M2.7-highspeed no-op). The output
directory `outputs/hermes-adapter-implementation/` is empty. No `hermes.py` adapter
module exists anywhere in the codebase. No code was written for any of the six
frontier tasks.

The existing codebase has a smoke test (`scripts/hermes_summary_smoke.sh`) that
**bypasses** the adapter concept entirely and writes directly to the event spine
using the owner principal. This is architecturally wrong — it masks the absence
of the adapter by simulating Hermes as the owner.

## Frontier Task Audit

| Task | Status | Evidence |
|------|--------|----------|
| Create `hermes.py` adapter module | **Missing** | No file exists; `grep -r hermes services/` finds only `spine.py` event kind |
| HermesConnection with authority token validation | **Missing** | No connection class, no token validation code anywhere |
| readStatus through adapter | **Missing** | Status is read via direct HTTP (`/status`) with no adapter mediation |
| appendSummary through adapter | **Missing** | Smoke test calls `spine.append_hermes_summary()` directly, no adapter |
| Event filtering (block `user_message` for Hermes) | **Missing** | `spine.get_events()` returns all kinds; no filtering by caller identity |
| Hermes pairing endpoint on daemon | **Missing** | `daemon.py` has no `/hermes/*` routes; no Hermes-specific pairing flow |

**Result: 0 of 6 tasks completed.**

## Correctness

Not applicable — there is no implementation to evaluate for correctness. The
existing primitives (`spine.py`, `store.py`, `daemon.py`) are structurally
correct for the home-miner-daemon slice but have no Hermes-specific mediation.

## Milestone Fit

The Hermes adapter is a required component of the milestone 1 acceptance criteria
in `specs/2026-03-19-zend-product-spec.md`:

> Hermes Gateway can connect through the Zend-native gateway adapter using only
> explicitly granted authority

This criterion is **not satisfied**. The existing smoke test gives the impression
of Hermes integration but does not enforce any authority boundary. It uses
`load_or_create_principal()` (the owner principal) and calls the spine directly,
which is the opposite of delegated authority.

## Remaining Blockers

1. **No adapter module exists.** The entire `hermes.py` must be written from scratch.
2. **No Hermes-specific principal or token model.** The `store.py` pairing system
   creates client pairings with `observe`/`control` capabilities. Hermes needs
   a distinct pairing type with `observe`/`summarize` capabilities. This type
   does not exist.
3. **No daemon endpoint for Hermes pairing.** The daemon's `GatewayHandler` has
   no route for issuing a Hermes authority token or accepting a Hermes connection.
4. **No event read filtering.** `spine.get_events()` returns all event kinds.
   Hermes must be restricted to `hermes_summary`, `miner_alert`, and
   `control_receipt` per `references/hermes-adapter.md`.
5. **No event write restriction.** `spine.append_event()` accepts any `EventKind`.
   The adapter must ensure Hermes can only write `hermes_summary`.

---

## Nemesis-Style Security Review

### Pass 1 — First-Principles Challenge

#### Trust Boundaries

**Finding P1-1: No trust boundary between Hermes and owner.**
The contract (`references/hermes-adapter.md`) defines Hermes as a delegated
authority with scoped capabilities. But no code enforces this separation. The
smoke test runs Hermes operations under the owner's `PrincipalId`, making Hermes
and the owner indistinguishable in the event spine. An auditor reading the spine
cannot tell whether a `hermes_summary` event was written by the actual owner or
by a delegated agent.

**Severity:** High — identity confusion in the audit trail.
**Required fix:** Hermes must operate under its own principal or a scoped
delegation token that is distinct from the owner principal. Events written by
Hermes must carry the Hermes principal, not the owner.

**Finding P1-2: Authority token contract is unimplemented.**
`references/hermes-adapter.md` says the authority token encodes Principal ID,
granted capabilities, and expiration time. No code implements token issuance,
validation, or expiration checking. The concept exists only in documentation.

**Severity:** Critical — the entire capability scoping mechanism is absent.
**Required fix:** Implement token issuance in the pairing flow and token
validation in every adapter method.

**Finding P1-3: Daemon endpoints are unauthenticated.**
All HTTP endpoints (`/health`, `/status`, `/miner/start`, `/miner/stop`,
`/miner/set_mode`) accept requests from any LAN caller with no token, no
capability check, and no principal identification. The capability enforcement
in `cli.py` exists only in the CLI layer and is trivially bypassed by calling
the HTTP API directly.

**Severity:** High — capability enforcement is cosmetic.
**Impact on Hermes:** Even with a correctly implemented adapter, Hermes (or any
LAN process) could bypass the adapter and call the daemon directly. The daemon
itself must enforce authentication.

**Finding P1-4: `user_message` events are readable by any caller.**
The contract says Hermes must not read `user_message` events. But
`spine.get_events()` has no caller identity concept. Any code path that calls
`get_events()` gets all event kinds including encrypted user messages.

**Severity:** Medium — privacy violation in the event read path.
**Required fix:** Event read functions must accept a caller identity and filter
based on that caller's permitted event kinds.

#### Dangerous Actions

**Finding P1-5: Hermes cannot trigger miner control in milestone 1, but nothing
prevents it.**
The contract says direct miner control through Hermes is deferred. But since the
daemon has no authentication, any process — including a hypothetical Hermes
process — can POST to `/miner/start`, `/miner/stop`, or `/miner/set_mode`.

**Severity:** Medium — the "deferred" boundary is aspirational, not enforced.

### Pass 2 — Coupled-State Review

#### Pairing State Consistency

**Finding P2-1: `create_pairing_token()` generates immediately-expired tokens.**
In `store.py:89`:
```python
expires = datetime.now(timezone.utc).isoformat()
```
This sets `token_expires_at` to the current time. Every token is born expired.
The expiration field is structurally broken.

**Severity:** High — token expiration is meaningless.
**Required fix:** Add a configurable TTL (e.g., 5 minutes) to the expiration
timestamp.

**Finding P2-2: `token_used` flag is write-only.**
`GatewayPairing.token_used` is initialized to `False` in `pair_client()` but
is never set to `True` by any code path. Token replay prevention does not exist.

**Severity:** High — replay attacks are possible.
**Required fix:** Set `token_used = True` after first use. Reject tokens where
`token_used` is already `True`.

**Finding P2-3: File-based state has no concurrency protection.**
`store.py` reads the full JSON file, modifies the in-memory dict, and writes it
back. `spine.py` appends to a JSONL file. Neither uses file locking. Concurrent
requests to the threaded HTTP server (`ThreadedHTTPServer`) can cause:
- Lost pairing records (write-after-read race in `save_pairings`)
- Interleaved JSON lines in the spine (concurrent appends)

**Severity:** Medium — data corruption under concurrent access.
**Required fix:** Use `fcntl.flock()` or equivalent for both stores.

#### Secret Handling

**Finding P2-4: Shell injection in smoke test.**
`scripts/hermes_summary_smoke.sh:52` interpolates `$SUMMARY_TEXT` directly
into a Python string literal using single quotes:
```bash
python3 -c "
...
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
..."
```
A `SUMMARY_TEXT` containing a single quote would break out of the Python string.
While this script is developer-only, it establishes a dangerous pattern.

**Severity:** Low (dev-only script) — but the pattern should not be copied into
production adapter code.
**Required fix:** Pass values via environment variables or stdin, not string
interpolation into code.

#### Capability Scoping

**Finding P2-5: Capability model does not include `summarize`.**
The existing `GatewayCapability` type is `'observe' | 'control'`. The Hermes
contract adds `'observe' | 'summarize'` as `HermesCapability`. These are
different capability namespaces. The adapter must either:
(a) extend the existing capability model with `summarize`, or
(b) maintain a separate Hermes capability model.

The choice affects the pairing store schema. Neither option is implemented.

**Severity:** Medium — architectural decision not yet made.

#### Idempotence and Retry Safety

**Finding P2-6: `append_hermes_summary()` is not idempotent.**
Calling it twice with the same content creates two events. The event spine is
append-only by design, which is correct, but the adapter should deduplicate
or at minimum carry an idempotency key so retried Hermes summaries don't
produce duplicate inbox entries.

**Severity:** Low — append-only is the design, but the adapter should expose
an idempotency mechanism for Hermes callers.

#### Service Lifecycle

**Finding P2-7: No Hermes connection lifecycle management.**
The contract defines `connect(authority_token) -> HermesConnection`. There is
no concept of connection state, disconnection, reconnection, or heartbeat.
When the daemon restarts, there is no way for a connected Hermes to detect it
has lost its session. The adapter must define what happens to an active Hermes
connection when the daemon process dies and restarts.

**Severity:** Medium — operational resilience gap.

---

## Summary of Findings

| ID | Finding | Severity | Category |
|----|---------|----------|----------|
| P1-1 | No trust boundary between Hermes and owner | High | Identity |
| P1-2 | Authority token contract unimplemented | Critical | AuthZ |
| P1-3 | Daemon endpoints unauthenticated | High | AuthN |
| P1-4 | `user_message` readable by any caller | Medium | Privacy |
| P1-5 | Miner control not gated for Hermes | Medium | AuthZ |
| P2-1 | Pairing tokens born expired | High | Token lifecycle |
| P2-2 | `token_used` flag never set | High | Replay prevention |
| P2-3 | No file locking for concurrent access | Medium | Data integrity |
| P2-4 | Shell injection in smoke test | Low | Code quality |
| P2-5 | Capability model missing `summarize` | Medium | Schema |
| P2-6 | Summary append not idempotent | Low | Retry safety |
| P2-7 | No connection lifecycle management | Medium | Resilience |

## Review Verdict

**NOT APPROVED — Lane produced no implementation.**

The specify stage was a no-op. Zero code was written. The six frontier tasks
are entirely unaddressed. The existing codebase has the primitives (event spine,
pairing store, daemon) but none of the Hermes-specific mediation, authority
delegation, or capability enforcement that the adapter contract requires.

The security review also surfaces pre-existing issues (P2-1, P2-2, P2-3) in
the home-miner-daemon that the adapter implementation should address or at
minimum not inherit. These are not blockers caused by this lane, but they
become attack surfaces once Hermes connects.

## Recommended Next Steps

1. Re-run the specify stage with a capable model (not MiniMax-M2.7-highspeed at 0 tokens).
2. Implement `services/home-miner-daemon/hermes.py` with:
   - `HermesConnection` class with token validation
   - `readStatus()` that delegates to daemon and enforces `observe` capability
   - `appendSummary()` that writes to spine with Hermes principal (not owner)
   - Event read filtering (block `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`)
3. Add `/hermes/pair` endpoint to daemon that issues scoped authority tokens.
4. Fix `create_pairing_token()` to use an actual future expiration time.
5. Implement `token_used` flip to prevent replay.
6. Add file locking to `store.py` and `spine.py`.
7. Fix `hermes_summary_smoke.sh` to use the adapter rather than direct spine access.
