# Zend Home Command Center — Carried-Forward Review

**Status:** Carried Forward — Blocking Gaps Identified
**Generated:** 2026-03-22
**Reviewer:** Claude Opus 4.6 (second-pass honest review)
**Supersedes:** `outputs/home-command-center/review.md`

---

## Verdict

**NOT APPROVED — blocking gaps remain.**

The scaffold is structurally correct and the architectural direction is sound.
However, three security gaps that the prior review noted as "risks" are actually
spec violations: daemon has no auth, tokens expire at creation, and the spine
writes plaintext. A review that approves work while leaving critical security
boundaries unimplemented trains the system to treat security as optional polish.

---

## Critical Gaps — Must Fix

### C1: Daemon-level auth is absent

**Location:** `services/home-miner-daemon/daemon.py`, `GatewayHandler` class

The HTTP server accepts any request to `/miner/start`, `/miner/stop`, and
`/miner/set_mode` without a token, PrincipalId, or capability check. The
capability check at `cli.py:134` (`has_capability(args.client, 'control')`)
is trivially bypassed by calling the HTTP API directly.

**Impact:** Any process on localhost can start/stop the miner and change modes
with no pairing or permission.

**Fix:** The daemon must require a bearer token on every request. The daemon —
not the CLI — must check capabilities server-side.

---

### C2: Pairing token expires at creation

**Location:** `services/home-miner-daemon/store.py:89`

```python
expires = datetime.now(timezone.utc).isoformat()
```

The token is expired the instant it is created. The `token_expires_at` field is
written but never checked in any pairing flow. `token_used` is `False` at
creation and never set to `True` after use. Both `PairingTokenExpired` and
`PairingTokenReplay` from `references/error-taxonomy.md` are defined but
unimplemented.

**Fix:** Set a real future expiry. Check `token_expires_at` during pairing.
Set `token_used = True` atomically on first use.

---

### C3: Event spine is plaintext

**Location:** `services/home-miner-daemon/spine.py`

The spine appends unencrypted JSON lines to `state/event-spine.jsonl`. The
product spec, `references/event-spine.md`, and the ExecPlan all require
encryption. The prior review called this a "risk" and still approved the slice.

**Fix:** Design the encryption boundary now (even if implementation is deferred
to the next slice). Define the stub as an explicit placeholder, not an implicit
assumption that encryption will be added later without planning.

---

## High-Priority Gaps — Required by the ExecPlan

### C4: No automated tests

The ExecPlan acceptance criteria require "at least one automated test per new
script." No test files exist anywhere in the repository.

### C5: `references/gateway-proof.md` missing

The ExecPlan requires proof transcripts proving the end-to-end flow works.
The file does not exist.

### C6: Bootstrap not idempotent

Re-running `scripts/bootstrap_home_miner.sh` fails because `alice-phone` is
already paired. The plan requires idempotent scripts.

### C7: Control receipt not atomic

If `spine.append_control_receipt` at `cli.py:157` raises (disk full, permission
error), the daemon has already accepted the mode change at line 150. The event
spine and daemon state diverge. The ExecPlan's "event spine is source of truth"
invariant is violated.

---

## Medium-Priority Gaps

### C8: UI hardcodes capabilities

`apps/zend-home-gateway/index.html:626` sets `state.capabilities =
['observe', 'control']` without fetching from the daemon. An observe-only client
will show control buttons.

### C9: Upstream SHAs not pinned

`upstream/manifest.lock.json` has `"pinned_sha": null` for all entries.
`scripts/fetch_upstreams.sh` fetches branch `main` at head time, not a fixed
revision.

### C10: `state/README.md` missing

The ExecPlan requires a note that local state is disposable. Not present.

### C11: `references/onboarding-storyboard.md` missing

Listed as a required artifact in the ExecPlan. Not present.

### C12: Hermes smoke test bypasses adapter

`scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary` directly,
not through any adapter layer. It proves Python can call a function, not that
the adapter boundary exists.

---

## What Works

- **Repo layout** matches the ExecPlan.
- **`MinerSimulator`** uses threading locks for state mutations.
- **`PrincipalId`** is UUID v4, shared across store and spine.
- **Event spine** models all 7 event kinds and is append-only.
- **Daemon binds `127.0.0.1`** as specified.
- **Gateway UI** follows `DESIGN.md` typography and color system.
- **Reference contracts** in `references/` define the boundaries clearly.

---

## Blocking vs. Deferred

| Gap | Blocking? | Rationale |
|-----|-----------|-----------|
| C1 Daemon auth | **Yes** | Core security promise |
| C2 Token lifecycle | **Yes** | Trust ceremony is broken without it |
| C3 Encryption | **Deferred** | Boundary must be designed now; implementation can follow |
| C4 Tests | **Yes** | ExecPlan requires them for acceptance |
| C5 Proof transcripts | **Yes** | ExecPlan requires them for acceptance |
| C6 Idempotence | **Yes** | Prevents recovery runs |
| C7 Atomicity | **No** | Can log and warn for now |

---

## Forward Path

The carried-forward lane must deliver:

1. Daemon-level bearer-token auth with server-side capability checks.
2. Pairing token lifecycle: real expiry, replay detection, `token_used` flag.
3. At minimum, an explicit encryption stub in `spine.py` that documents the
   encryption interface, so the plaintext path is an acknowledged placeholder.
4. At least one automated test per script, covering error paths.
5. `references/gateway-proof.md` with runnable transcripts.
6. Idempotent bootstrap.

Genesis plans 004, 008, 009, 011, and 012 address the remaining gaps. This
slice resolves the auth and token issues; the next slice should complete tests,
proof transcripts, and encryption implementation.
