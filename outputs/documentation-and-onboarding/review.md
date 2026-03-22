# Documentation & Onboarding — Review

**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-22
**Reviewer:** Nemesis review (two-pass security + correctness)

## Verdict: CONDITIONAL PASS

The documentation is structurally complete and covers the right surfaces. Three
falsehoods were found and fixed in this review. Remaining blockers are noted
below. The lane can proceed once the blockers are addressed.

---

## Pass 1 — First-Principles Trust Boundary Review

### Finding 1: HTTP endpoints are unauthenticated (known, documented)

All five daemon HTTP endpoints (`/health`, `/status`, `/miner/start`,
`/miner/stop`, `/miner/set_mode`) accept unauthenticated requests. Capability
checks exist only in the CLI layer. Any LAN client that can reach the daemon
can curl control endpoints directly.

**Documentation status:** `docs/api-reference.md` correctly states "No
authentication required at HTTP layer" and "The daemon HTTP endpoints are
intentionally unauthenticated for milestone 1." The `docs/architecture.md`
design decisions section explains why. No doc fix needed — the limitation is
honestly stated.

**Risk:** Low for milestone 1 (LAN-only assumption). Higher if operators bind
to 0.0.0.0 without firewall rules. The operator quickstart security section
covers this adequately.

### Finding 2: Token replay prevention documented but not implemented

`docs/architecture.md` contained a code snippet showing `token_used` being
checked on pairing reuse. This code does not exist in `store.py`. The
`token_used` field is stored as `False` but never read.

**Fix applied:** Rewrote the Token Replay Prevention section to accurately
describe current state: the field exists, duplicate device names provide basic
protection, full enforcement is deferred.

### Finding 3: Token expiration is immediate

`store.py:89` sets `token_expires_at` to `datetime.now()`, meaning every token
expires at creation time. The `ZEND_TOKEN_TTL_HOURS` variable mentioned in the
exec plan does not exist in code.

**Documentation status:** Docs do not claim token TTL is configurable, so no
falsehood — but operators have no way to set token lifetime. This is a code
gap, not a documentation gap.

### Finding 4: No CORS headers on daemon

The daemon does not set `Access-Control-Allow-Origin` headers. The HTML client
at `file://` may face CORS restrictions when fetching from
`http://<lan-ip>:8080`. This could silently break the command center when
accessed from a different origin than localhost.

**Documentation status:** Not mentioned. `docs/operator-quickstart.md` should
note this as a known limitation when accessing the daemon from a phone browser.

---

## Pass 2 — Coupled-State & Protocol Surface Review

### Finding 5: Pairing store ↔ spine desynchronization window

In `cli.py:cmd_pair()`, the pairing is persisted to `pairing-store.json` via
`pair_client()` (line 103), then spine events are appended (lines 106-115). If
the process crashes between these operations, the store has the pairing but the
spine has no record of it. The inverse (spine without store) cannot happen.

**Impact:** Low — the pairing functions but the audit trail has a gap. The
store is the authority for "can this device do X?" and the spine is the audit
trail. A gap here means a paired device works but the pairing event is missing
from the journal.

### Finding 6: Bootstrap skips pairing_requested event

`cli.py:cmd_bootstrap()` calls `spine.append_pairing_granted()` but never
`spine.append_pairing_requested()`. The default bootstrap pairing appears in
the spine as granted without ever being requested. Compare with `cmd_pair()`
which correctly emits both events.

**Impact:** Spine inconsistency — a consumer filtering for the
`pairing_requested → pairing_granted` flow would see an orphaned grant.

### Finding 7: Event spine has no principal scoping on queries

`spine.get_events()` returns all events regardless of `principal_id`. In a
multi-principal scenario, events would leak across principals.

**Impact:** None for milestone 1 (single principal). Would become a security
issue if multi-principal support is added.

### Finding 8: `get_events` kind filter crashed on CLI input

`spine.py:87` called `kind.value` on the `kind` parameter, which crashes with
`AttributeError` when the CLI passes a plain string instead of an `EventKind`
enum. The documented `--kind control_receipt` filter was non-functional.

**Fix applied:** Changed to resolve `.value` only for `EventKind` instances,
falling back to direct string comparison. Both enum and string callers now work.

---

## Falsehoods Found and Fixed

| # | Location | Falsehood | Fix |
|---|----------|-----------|-----|
| 1 | `docs/architecture.md` L322-329 | Token replay prevention code snippet that doesn't exist in codebase | Rewrote to describe actual behavior |
| 2 | `docs/contributor-guide.md` L209-215 | Claims test suite covers 5 areas; no test files exist | Replaced with honest "no tests yet" |
| 3 | `README.md` L89-93 | Implies test suite exists | Added note that tests don't exist yet |

## Code Bug Fixed

| File | Line | Bug | Fix |
|------|------|-----|-----|
| `spine.py` | 87 | `kind.value` crashes on plain string input from CLI | Resolve `.value` only for `EventKind` instances |

---

## Correctness Verification

### Endpoints (5/5 correct)

| Endpoint | Documented | In Code | Response Format Match |
|----------|------------|---------|----------------------|
| GET /health | Yes | daemon.py:169 | Yes |
| GET /status | Yes | daemon.py:171 | Yes |
| POST /miner/start | Yes | daemon.py:186 | Yes |
| POST /miner/stop | Yes | daemon.py:189 | Yes |
| POST /miner/set_mode | Yes | daemon.py:192 | Yes |

### CLI Commands (6/6 correct)

| Command | Documented | In Code | Args Match |
|---------|------------|---------|------------|
| health | Yes | cli.py:213 | Yes |
| status | Yes | cli.py:209 | Yes |
| bootstrap | Yes | cli.py:216 | Yes |
| pair | Yes | cli.py:220 | Yes |
| control | Yes | cli.py:225 | Yes |
| events | Yes | cli.py:233 | Yes |

### Environment Variables (4/4 correct)

| Variable | Documented Default | Code Default | Match |
|----------|-------------------|--------------|-------|
| ZEND_BIND_HOST | 127.0.0.1 | 127.0.0.1 | Yes |
| ZEND_BIND_PORT | 8080 | 8080 | Yes |
| ZEND_STATE_DIR | state/ | `Path(__file__).parents[2] / "state"` | Yes |
| ZEND_DAEMON_URL | http://127.0.0.1:8080 | http://127.0.0.1:8080 | Yes |

### Data Models (2/2 correct)

| Model | Fields Documented | Fields in Code | Match |
|-------|-------------------|----------------|-------|
| Principal | id, created_at, name | id, created_at, name | Yes |
| GatewayPairing | id, principal_id, device_name, capabilities, paired_at, token_expires_at, token_used | Same | Yes |

### Event Kinds (7/7 correct)

All documented event kinds match `spine.py:EventKind` enum exactly.

### File Paths (all correct)

All documented paths (daemon.py, cli.py, spine.py, store.py, event-spine.jsonl,
principal.json, pairing-store.json, scripts/) verified to exist.

### Scripts (4/4 correct)

bootstrap_home_miner.sh, pair_gateway_client.sh, read_miner_status.sh,
set_mining_mode.sh — all exist. Bootstrap --stop flag works as documented.

---

## Plan Coverage

### Endpoints from plan milestone 4 not in code or docs

The exec plan lists these endpoints to document, but they do not exist in code:

- `GET /spine/events` — not implemented
- `GET /metrics` — not implemented
- `POST /pairing/refresh` — not implemented

The docs correctly omit them. The plan should be updated to reflect reality.

### README line count

139 lines. Under the 200-line limit specified in the plan.

---

## Milestone Fit

The documentation matches the milestone 1 system accurately (after fixes).
It correctly scopes to LAN-only, stdlib-only, simulator-based operation.

## Remaining Blockers

| # | Blocker | Severity | Owned By |
|---|---------|----------|----------|
| 1 | No test suite exists — docs reference pytest but no tests to run | High | Code lane |
| 2 | Plan task "Verify documentation accuracy by following it on a clean machine" not done | Medium | This lane |
| 3 | CORS limitation undocumented — HTML client may fail when daemon is on LAN IP | Low | This lane |
| 4 | Plan lists 3 endpoints (GET /spine/events, GET /metrics, POST /pairing/refresh) that don't exist — plan needs update | Low | Plan maintenance |
| 5 | Bootstrap skips pairing_requested event — spine audit trail gap | Low | Code lane |

### Blocker 1 is the critical gap

The documentation tells contributors to run `python3 -m pytest` but there are
no tests. A new contributor following the guide will get zero test output and
wonder if something is broken. The docs now honestly state this, but the
absence of tests means the contributor guide's "verify your changes" workflow
has no automated safety net.

---

## Sign-off

| Criteria | Status |
|----------|--------|
| Endpoints documented accurately | Yes (5/5) |
| CLI commands documented accurately | Yes (6/6) |
| Environment variables match code | Yes (4/4) |
| File paths verified | Yes |
| Cross-references valid | Yes |
| No fabricated code snippets | Yes (after fix) |
| No fabricated test coverage claims | Yes (after fix) |
| Security boundaries honestly stated | Yes |
| Coupled-state risks identified | Yes |

**Result:** Conditional pass. Fixes applied make the documentation truthful.
Remaining blockers are tracked above — none require reverting the lane.
