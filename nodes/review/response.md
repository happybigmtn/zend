I've now read every file in the codebase. Here's the full review.

---

# Carried Forward: Build the Zend Home Command Center — Review

## TL;DR

The MiniMax-generated spec and review are **structurally sound** but contain **several factual errors** and **miss critical security findings**. The spec correctly maps the implementation topology. The review correctly identifies the three headline gaps (no token enforcement, no tests, Hermes stub). But it makes false claims about design-system color compliance, misses that the daemon HTTP layer has **zero auth**, and overlooks multiple code bugs.

---

## 1. Spec Assessment

**Correct:**
- Component table accurately maps real files
- Data models match `daemon.py`, `store.py`, `spine.py`
- API table matches `GatewayHandler.do_GET/do_POST`
- Design system section correctly references `DESIGN.md` requirements
- Error taxonomy correctly reflects `references/error-taxonomy.md`
- Observability section correctly reflects `references/observability.md`

**Incorrect or misleading:**
- **Genesis plans don't exist.** The spec references "genesis plans 002–014" with a full mapping table, but the `genesis/` directory doesn't exist in the repo. There are zero genesis plan files. The spec treats these as real artifacts.
- **`outputs/home-command-center/spec.md` referenced as "prior synthesis"** — this file doesn't exist.
- The provenance line says "Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`" — this file does exist and is accurate.

`★ Insight ─────────────────────────────────────`
The spec's genesis plan references are a fabrication layer — they describe a decomposition that was *imagined* but never materialized as files. This is a common LLM failure mode when summarizing plans: treating intended future work as if it already has durable artifacts. A reviewer must always `glob genesis/**/*.md` to verify.
`─────────────────────────────────────────────────`

---

## 2. Review Assessment

**Correct claims:**
- Daemon binds `127.0.0.1` — TRUE (`daemon.py:34`)
- `token_used=False` never set to True — TRUE (`store.py:49,113`)
- Zero test files — TRUE
- Hermes adapter is contract-only stub — TRUE (`hermes_summary_smoke.sh` calls spine directly)
- Event spine implements source-of-truth constraint — TRUE
- Inbox tab never fetches events — TRUE (no `fetchEvents()` in `index.html`)
- Observability events not emitted in daemon — TRUE

**False claims in the review:**

### FALSE: "Design system compliance: correct color variables"

The review (line 133) says: *"correct color variables, 44×44 touch targets... correct component vocabulary. No banned AI-slop patterns detected."*

This is **wrong**. The `index.html` CSS variables use a completely different color palette than `DESIGN.md`:

| DESIGN.md | index.html |
|-----------|------------|
| Basalt `#16181B` | `--color-bg: #FAFAF9` (warm white) |
| Slate `#23272D` | `--color-surface: #FFFFFF` (pure white) |
| Mist `#EEF1F4` | `--color-border: #E7E5E4` (stone) |
| Moss `#486A57` | `--color-success: #15803D` (green, wrong shade) |
| Amber `#D59B3D` | `--color-warning: #B45309` (orange, wrong shade) |
| Signal Red `#B44C42` | `--color-error: #B91C1C` (crimson, wrong shade) |
| Ice `#B8D7E8` | Not present |

The client uses a warm neutral/stone palette. DESIGN.md specifies a dark-surface domestic palette. These are fundamentally different design languages.

### FALSE: "No banned AI-slop patterns detected"

Empty states violate the DESIGN.md guardrail: *"Every empty state needs warmth, context, and a primary next action."*

- `index.html:556`: "No messages yet" — no next action
- `index.html:569`: "Hermes not connected" — no next action
- `index.html:544`: "No receipts yet" — no next action

### FALSE: "CLI correctly enforces capability checks before daemon calls"

The CLI does check capabilities, but the daemon HTTP endpoints have **zero auth**. Any process on localhost can `POST /miner/start` without any token or capability check. The capability enforcement exists only in the CLI wrapper, not at the daemon boundary.

---

## 3. Nemesis Security Review

### Pass 1 — First-Principles Trust Boundary Challenge

**CRITICAL: Daemon HTTP has no authentication**

`daemon.py:168-174` serves `/status` to any request. `daemon.py:176-199` accepts `/miner/start`, `/miner/stop`, `/miner/set_mode` from any request. There's no header check, no token validation, no client identification. The spec says `/status` requires `observe` or `control` — but the daemon doesn't enforce this.

The CLI (`cli.py`) checks `has_capability()` before calling the daemon, but this is defense at the wrong layer. Any `curl` or rogue process on localhost bypasses all capability enforcement.

**Severity: Critical for milestone 1.** Even on localhost, any process can control the miner.

**CRITICAL: Token expiration is set to creation time**

`store.py:88-89`:
```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # expires NOW
    return token, expires
```

Every pairing token is born already expired. This means `PairingTokenExpired` should fire on every pairing attempt, but nothing checks expiration. The review notes token replay isn't enforced but misses that expiration is also broken at the source.

**HIGH: No CORS headers on daemon**

The gateway client (`index.html`) makes `fetch()` calls to `http://127.0.0.1:8080`. If served from a different origin (including `file://`), browsers will block these requests. The daemon sets no `Access-Control-Allow-Origin` header.

**HIGH: Shell injection in hermes_summary_smoke.sh**

`hermes_summary_smoke.sh:52-53`:
```python
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
```

The shell variables `$SUMMARY_TEXT` and `$AUTHORITY_SCOPE` are interpolated inside single quotes within a Python `-c` string. Currently these are hardcoded constants, but the pattern sets a trap: if anyone adds user input to these variables, single-quote escaping breaks the Python expression. This is a latent injection vector.

**MEDIUM: PID file TOCTOU race**

`bootstrap_home_miner.sh:62-69`: Checks PID file, reads it, checks if process alive — all with race windows. Two concurrent bootstrap invocations can interfere.

### Pass 2 — Coupled-State Review

**CRITICAL: Pairing store ↔ Event spine inconsistency on failure**

`cli.py:102-115` (`cmd_pair`): The pairing record is created in the store (line 103) BEFORE spine events are appended (lines 106-115). If `spine.append_pairing_requested()` or `spine.append_pairing_granted()` throws, the pairing exists in the store but no events are recorded. The `EventAppendFailed` error class is defined but no code path catches spine write failures.

**HIGH: cmd_events kind filter is broken**

`cli.py:190-191`:
```python
kind = args.kind if args.kind != 'all' else None
events = spine.get_events(kind=kind, limit=args.limit)
```

`spine.get_events()` expects `kind` to be an `EventKind` enum or `None`. But `args.kind` is a raw string (e.g., `"control_receipt"`). Inside `get_events()`, the comparison is `e.kind == kind.value` — but `kind` is a string, which has no `.value` attribute. This will crash with `AttributeError` for any non-`all` kind filter.

**HIGH: pairing_granted event missing pairing_token field**

The event-spine contract (`references/event-spine.md:50-53`) defines `pairing_granted` as requiring a `pairing_token` field. But `spine.py:107-116` (`append_pairing_granted`) only includes `device_name` and `granted_capabilities`. Contract violation.

**HIGH: No ControlCommandConflict enforcement**

`MinerSimulator` uses `threading.Lock()` for internal state mutations, but the daemon has no command serialization at the HTTP handler level. Two simultaneous `POST /miner/set_mode` requests with different modes both succeed — last writer wins. The `ControlCommandConflict` error class from the taxonomy is defined but never raised.

**MEDIUM: Bootstrap creates observe-only pairing**

`cli.py:78`: `pairing = pair_client(args.device, ['observe'])` — the bootstrapped primary device gets only `observe`, not `control`. The spec implies the primary device should have control capability for the six concrete validation steps. The plan's step 5 (`set_mining_mode.sh`) requires `control` capability. A bootstrapped-only device can't complete the validation sequence.

**MEDIUM: Gateway client hardcodes capabilities**

`index.html:626`: `capabilities: ['observe', 'control']` — hardcoded. There's no endpoint to discover actual capabilities. An observe-only device will see Start/Stop buttons that fail on click, rather than being hidden or disabled.

**LOW: Event spine has no fsync**

`spine.py:64`: Opens file in append mode, writes, but no `f.flush()` / `os.fsync()`. Crash between write and kernel flush loses events.

`★ Insight ─────────────────────────────────────`
The fundamental architectural gap here is that the capability model lives in the CLI layer but not in the daemon layer. This is a classic "enforcement at the wrong boundary" problem. The daemon is the trust boundary — it's the thing that receives HTTP requests from arbitrary sources. The CLI is a convenience wrapper. Moving capability checks to the daemon (or adding token-based auth on HTTP) is the single highest-priority fix before any other work proceeds.
`─────────────────────────────────────────────────`

---

## 4. Milestone Fit

The implemented slice **partially fits** the plan's milestone 1. What exists:

| Plan Requirement | Status |
|---|---|
| LAN-only daemon | Done (127.0.0.1 binding) |
| MinerSimulator with same contract | Done |
| PrincipalId + pairing records | Done |
| Event spine (JSONL, append-only) | Done |
| 4-destination gateway client | Done (wrong colors) |
| Bootstrap / pair / status / control scripts | Done |
| Off-device proof script | Stub only |
| Hermes adapter | Contract only, no implementation |
| Encrypted operations inbox in client | Not wired |
| Automated tests | Zero |
| Token replay/expiry enforcement | Zero |
| Observability structured logging | Zero |
| Trust ceremony UX | Missing |

The ExecPlan's Progress section (lines 37-68) correctly shows all implementation items as unchecked. The review's "partial acceptance" verdict is accurate — but it should be stronger: the slice is not safe to build on until HTTP-layer auth exists.

---

## 5. Remaining Blockers (Ordered)

1. **Daemon HTTP auth** — no further work should proceed until the daemon enforces capabilities on its HTTP endpoints, not just in the CLI wrapper.
2. **Token lifecycle** — `create_pairing_token()` creates immediately-expired tokens. Fix expiration, add token validation on pairing, enforce single-use.
3. **Design system colors** — the gateway client uses the wrong color palette entirely. Must be rethemed to match DESIGN.md.
4. **cmd_events crash** — string-to-enum mismatch means `--kind` filtering always crashes.
5. **Pairing ↔ spine atomicity** — spine append failures silently leave orphan pairing records.
6. **Bootstrap capability** — primary device should get `observe,control`, not `observe` only, or the six-step validation sequence cannot complete.
7. **Empty states need next actions** — DESIGN.md guardrail violation.
8. **pairing_granted missing pairing_token** — contract violation with `references/event-spine.md`.
9. **Genesis plans don't exist as files** — spec references 13 plans that aren't written.