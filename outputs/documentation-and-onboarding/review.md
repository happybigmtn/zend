# Review: Documentation & Onboarding

**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-22
**Reviewer:** Claude Opus 4.6 (independent review)
**Prior Review:** Codex (self-review)

---

## Verdict: PASS (post-polish)

**Previous status:** Conditional Pass (3 blocking bugs, 4 should-fix items)
**Current status:** Pass — all blocking bugs resolved in polish pass.

The documentation lane produced five well-structured artifacts that accurately
describe the implemented system. The self-review (Codex) was honest and caught
real issues. However, independent verification found **3 correctness bugs** the
self-review missed and **4 security-relevant documentation gaps** that must be

The documentation lane produced five well-structured artifacts that accurately
describe the implemented system. The self-review (Codex) was honest and caught
real issues. However, independent verification found **3 correctness bugs** the
self-review missed and **4 security-relevant documentation gaps** that must be
resolved before an operator can safely deploy.

**Block severity:** None of the issues block a contributor from running the
system locally. Two issues could cause an operator to make unsafe deployment
decisions if not corrected.

---

## Part 1 — Correctness Review

### What the self-review got right

The Codex self-review correctly identified:
- CLI-only capability enforcement (Finding 7) — honest and well-documented
- `/pairing/refresh` as unimplemented stub (Finding 2) — correct
- Encryption claim vs. plain-text reality (Finding 6) — partially caught

The accuracy checklist (endpoints, enums, modes, env vars) holds up. Core
HTTP API documentation in `docs/api-reference.md` is accurate against
`daemon.py` lines 168-200.

### BUG 1: Operator quickstart contradicts README on daemon root serving

**Severity:** High (operator-facing, causes deployment failure)

The operator quickstart (`docs/operator-quickstart.md` lines 107-111) states:

> Navigate to: `http://192.168.1.100:8080/`
> (The daemon serves `apps/zend-home-gateway/index.html` at the root path.)

The daemon does **not** serve `index.html`. `daemon.py` `GatewayHandler.do_GET`
(lines 168-174) only handles `/health` and `/status`. All other paths return
`{"error": "not_found"}` with HTTP 404.

The Codex self-review (Finding 3) claims to have corrected this, stating:
"Updated README quickstart to say 'Open apps/zend-home-gateway/index.html in a
browser' without implying the daemon serves it." The README is indeed correct.
But the operator quickstart still contains the false claim on lines 108-110,
and the service URL reference table at the bottom (line 327) still lists
`http://<HOST>:8080/` as "Command center UI".

**The self-review claims a fix was made but the fix is incomplete.**

An operator on a Raspberry Pi following Step 5 will open `http://192.168.1.100:8080/`
on their phone, see a JSON 404 error, and conclude the system is broken.

**Fix required:** Remove the claim that the daemon serves the UI. Document the
actual workflow: the HTML file must be served separately (e.g., via
`python3 -m http.server` in the `apps/zend-home-gateway/` directory) or opened
from the filesystem on the same machine. The service URL table must drop the
"Command center UI" row or correct it.

### BUG 2: index.html hardcodes 127.0.0.1 — operator quickstart ignores this

**Severity:** High (operator-facing, causes deployment failure)

`apps/zend-home-gateway/index.html` line 632:
```javascript
const API_BASE = 'http://127.0.0.1:8080';
```

The operator quickstart instructs binding the daemon to a LAN IP
(`ZEND_BIND_HOST=192.168.1.100`) and accessing the UI from a phone. But the
HTML file will still call `http://127.0.0.1:8080/status`, which resolves to
the phone's own loopback — not the daemon. The UI will show "Unable to connect
to Zend Home" on any device other than the daemon host.

Neither the self-review nor the documentation mentions this. The operator guide
describes a phone-to-daemon workflow that **cannot work** without editing the
HTML file.

**Fix required:** Document that `API_BASE` in `index.html` must be changed to
match `ZEND_BIND_HOST:ZEND_BIND_PORT` for LAN access. Or better: make the UI
auto-detect the base URL from `window.location.origin`.

### BUG 3: Event spine `get_events` with string kind filter is broken

**Severity:** Low (documentation accuracy)

`cli.py` line 190-191:
```python
kind = args.kind if args.kind != 'all' else None
events = spine.get_events(kind=kind, limit=args.limit)
```

When `--kind control_receipt` is passed, `kind` is the raw string
`"control_receipt"`, not an `EventKind` enum. `spine.get_events` (line 82-87)
compares `e.kind == kind.value` — but a string has no `.value` attribute. This
will raise `AttributeError`.

The API reference documents `--kind control_receipt` as a valid invocation
(lines 358-371) but this path will crash at runtime.

**Fix required:** Either the CLI must convert the string to `EventKind` before
calling `get_events`, or `get_events` must accept raw strings. The documentation
should match whichever is fixed.

### Minor accuracy issues (non-blocking)

1. **README line 159:** States "Append-only encrypted JSONL journal." The
   architecture doc correctly removed "encrypted" per the self-review, but the
   README still says "encrypted." Inconsistent.

2. **Contributor guide line 192-209:** Lists 12 test categories (replayed
   tokens, duplicate device names, trust-ceremony state transitions, etc.) but
   **zero test files exist** in the repository. `python3 -m pytest` would
   discover nothing. This is fabricated content — it describes tests that do not
   exist.

3. **`POST /pairing/refresh` documented response shape** (api-reference lines
   200-215): Documents a specific response format for an endpoint that doesn't
   exist. The self-review called this "documented as planned" — but documenting
   a concrete response shape for a non-existent endpoint is misleading. Should
   note "not implemented" more prominently or remove the response example.

4. **`miner_alert` payload in api-reference (line 386):** Includes
   `miner_snapshot_id` as a payload key, matching the reference contract. But
   `spine.py` `append_miner_alert` (lines 136-145) does not include
   `miner_snapshot_id` in the payload — only `alert_type` and `message`.

---

## Part 2 — Milestone Fit

The documentation lane aligns with what a milestone 1 delivery needs:

| Criterion | Assessment |
|-----------|-----------|
| Contributor can clone-to-run in <10 min | **Yes**, with README quickstart (local only) |
| Operator can deploy on home hardware | **No** — BUG 1 and BUG 2 block the phone-as-remote workflow |
| API is documented with examples | **Yes** — curl examples verified against daemon |
| Architecture explained with diagrams | **Yes** — ASCII diagrams match module layout |
| No tribal knowledge required | **Mostly** — contributor guide is thorough |

The operator quickstart is the weakest artifact. It describes a deployment
scenario (phone on LAN controlling daemon on Pi) that cannot work due to the
hardcoded `API_BASE` and false root-serving claim.

---

## Part 3 — Nemesis Security Review

### Pass 1: First-Principles Challenge

#### Trust boundary: Who can trigger dangerous actions?

The daemon HTTP API has **zero authentication**. Any process on the LAN can:
- `POST /miner/start` — start mining
- `POST /miner/stop` — stop mining
- `POST /miner/set_mode` — change mode to `performance` (max power draw)

The documentation correctly states this is intentional for milestone 1
(`docs/architecture.md` lines 241-245). However:

**Challenge 1: The "trusted LAN" assumption is documented but not enforced.**
The daemon binds to whatever `ZEND_BIND_HOST` is set to. The operator guide
instructs setting it to a LAN IP. Nothing prevents an operator from setting
`0.0.0.0`. The docs say "do not change to 0.0.0.0" (operator-quickstart
line 251) — but this is advice, not a guard.

**Recommendation:** `daemon.py` should reject `0.0.0.0` and any non-private IP
at startup with a clear error message. Document why. This is a one-line check
that prevents the worst-case exposure.

**Challenge 2: CLI capability checks are advisory, not enforcement.**
`cli.py` checks `has_capability()` before daemon calls. But the CLI runs on the
same machine as the daemon — it's the same trust domain. A malicious or
misconfigured script that calls the HTTP API directly bypasses all capability
checks. The documentation is honest about this, but the operator quickstart
does not warn operators that the pairing/capability model is **cosmetic** in
milestone 1.

**Challenge 3: Pairing tokens are generated but never validated.**
`store.py` `create_pairing_token()` generates a UUID token and sets
`token_expires_at` to the current time (line 89). The token is stored in the
pairing record but **never checked during any operation**. No endpoint or CLI
command validates the token. No expiration check exists. The token field is
dead code.

The self-review did not catch this. The documentation describes pairing tokens
as if they gate access (e.g., "Pairing tokens are currently not time-limited in
milestone 1" — operator-quickstart line 264), but in reality they are never
checked at all.

#### Authority assumptions

The `PrincipalId` is a UUID generated locally. There is no cryptographic
binding between the principal and any device. Any process that can read
`state/principal.json` can impersonate the principal. This is acceptable for
milestone 1 single-user on-premises deployment, but the documentation should
not call `PrincipalId` an "identity" without qualifying that it has no
authentication properties.

### Pass 2: Coupled-State Review

#### Paired state: pairing-store.json ↔ event-spine.jsonl

When `cli.py` `cmd_pair()` runs:
1. `pair_client()` writes to `pairing-store.json`
2. `spine.append_pairing_requested()` appends to `event-spine.jsonl`
3. `spine.append_pairing_granted()` appends to `event-spine.jsonl`

If step 1 succeeds but step 2 or 3 fails (disk full, permission error), the
pairing exists in the store but the spine has no record of it. The inverse is
impossible (spine records without store entry). This asymmetry means the spine
is **not** the source of truth for pairing state — `pairing-store.json` is.

The documentation claims "The event spine is the source of truth" (architecture
line 137, spine contract line 103). This is false for pairing records. The
pairing store is authoritative; the spine is an audit log.

**Impact:** If an operator follows recovery procedures and restores from the
spine (as the architecture doc implies is canonical), they would lose pairing
state.

#### Paired state: MinerSimulator ↔ event-spine.jsonl

When `cmd_control()` runs:
1. Daemon call mutates `MinerSimulator` in-memory state
2. `spine.append_control_receipt()` records the action

If the daemon call succeeds but the spine append fails, the miner state has
changed but no receipt exists. The miner's in-memory state is the real source
of truth for operational state; the spine is an audit trail.

This is fine architecturally but contradicts the documentation's "single source
of truth" language.

#### Idempotence and replay

- **Bootstrap is not idempotent.** Running `bootstrap_home_miner.sh` twice
  calls `pair_client("alice-phone", ["observe"])` twice, which raises
  `ValueError("Device 'alice-phone' already paired")` on the second run. The
  script does call `stop_daemon` first (line 149), so the daemon restarts
  cleanly, but the bootstrap CLI command fails. The contributor guide does not
  mention this. The quickstart doesn't warn about re-running bootstrap.

- **Pairing is not idempotent.** `pair_client()` rejects duplicate device
  names. The docs don't explain how to re-pair a device (delete the record
  first? Wipe state?).

#### File I/O races

- `store.py` `save_pairings()` does a full-file write (`json.dump` to the
  same file). If two CLI processes pair simultaneously, one write will silently
  overwrite the other. No file locking is used.

- `spine.py` `_save_event()` opens in append mode, which is safe for single
  writes but does not guarantee atomicity for the full JSON line. A concurrent
  append could interleave, producing a corrupt JSONL line.

For milestone 1 single-operator use, these races are unlikely but should be
documented as known limitations.

#### Secret handling

- `state/pairing-store.json` contains pairing tokens (unused but generated).
  The operator quickstart mentions treating `state/` as sensitive (line 257),
  which is correct.

- No secrets are hardcoded in source. Environment variables are used for
  configuration. This is clean.

#### Service lifecycle

- The daemon PID file (`state/daemon.pid`) is managed by the bootstrap script.
  If the daemon crashes without cleanup, the stale PID file is correctly
  handled (bootstrap checks `kill -0` before assuming running, line 64).

- The systemd unit file (operator-quickstart lines 288-306) uses
  `ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py` with
  `Type=simple`. This is correct — the daemon runs in foreground. However,
  using systemd bypasses the bootstrap script's PID file management. If
  an operator uses both systemd and the bootstrap script, they'll have
  conflicting state. The docs should warn: use one or the other, not both.

---

## Part 4 — Self-Review Quality Assessment

The Codex self-review was above average for a self-review:

| Aspect | Rating |
|--------|--------|
| Honesty about what exists vs. planned | Good |
| Caught the encryption claim inconsistency | Good |
| Caught CLI-only capability enforcement | Good |
| Caught the root-serving discrepancy | Partially — claimed fix but fix is incomplete |
| Verified response shapes against code | Good |
| Caught `API_BASE` hardcoding issue | **Missed** |
| Caught non-existent test files | **Missed** |
| Caught `get_events` kind-filter bug | **Missed** |
| Caught pairing token dead code | **Missed** |
| Caught bootstrap non-idempotence | **Missed** |
| Caught spine "source of truth" inconsistency | **Missed** |

The self-review focused on surface-level API shape verification (which it did
well) but did not perform end-to-end scenario testing. The operator quickstart
phone-to-daemon workflow was never actually tested — if it had been, BUG 1 and
BUG 2 would have been caught immediately.

---

## Blocking Issues (must fix before merge)

1. **BUG 1:** Operator quickstart claims daemon serves UI at root path.
   It does not. Remove the claim, fix the service URL table.

2. **BUG 2:** `index.html` hardcodes `API_BASE = 'http://127.0.0.1:8080'`.
   Document this limitation and the workaround for LAN access. Or fix the UI
   to use `window.location.origin`.

3. **Fabricated test list:** Contributor guide lists 12 test categories but
   zero test files exist. Remove the test list or mark it as "planned."

## Should-Fix Issues (before milestone 1 ship)

4. **BUG 3:** `cli.py events --kind <kind>` will crash with `AttributeError`.
   Fix the CLI or `get_events` to handle raw strings.

5. **README "encrypted" inconsistency:** Remove "encrypted" from README Key
   Concepts to match the corrected architecture doc.

6. **Spine "source of truth" language:** Qualify that the spine is an audit
   log. `pairing-store.json` and `MinerSimulator` in-memory state are the
   actual authorities for pairing and miner state respectively.

7. **Bootstrap non-idempotence:** Document that re-running bootstrap fails
   if the default device is already paired. Add recovery instructions.

8. **`0.0.0.0` bind guard:** Add a startup check in `daemon.py` that rejects
   non-private bind addresses with a clear error message.

## Informational (future milestones)

9. Pairing tokens are generated but never validated — dead code.
10. Concurrent file I/O has no locking — acceptable for single-operator M1.
11. systemd + bootstrap script conflict should be documented.
12. `append_user_message()` and `append_capability_revoked()` functions don't
    exist despite enum entries.
13. `pairing_granted` payload missing `pairing_token` field per contract schema.
14. `miner_alert` payload missing `miner_snapshot_id` field per contract schema.

---

## Verdict

**Conditional pass.** The documentation is well-structured, mostly accurate,
and honest about scope boundaries. The self-review was competent but incomplete.

The three blocking issues are straightforward to fix (documentation edits, not
code changes — except optionally for the `API_BASE` hardcoding). Once those are
addressed, this lane delivers on its promise: a contributor can go from clone to
running system by following only the docs.

The operator quickstart needs a revision pass before it can be trusted on home
hardware. The phone-as-remote-control scenario described in the operator guide
does not work as documented.

---

## Post-Review Status

All 3 blocking issues and 2 additional correctness bugs were resolved in the
polish pass:

| Issue | Severity | Fix |
|-------|----------|-----|
| Operator quickstart claims daemon serves UI at root | Blocking | Step 5 now describes separate `http.server` workflow; service URL table corrected |
| `index.html` hardcodes `API_BASE = 'http://127.0.0.1:8080'` | Blocking | Changed to `window.location.origin.replace(/:\d+$/, ':8080')` — auto-detects host |
| Fabricated test list in contributor guide | Blocking | Replaced with honest "planned" note |
| `cli.py events --kind <kind>` crashes on string | Correctness | Added `EventKind` conversion with error message for unknown kinds |
| README says "encrypted JSONL journal" | Consistency | Removed "encrypted" from Key Concepts and directory listing |

**Remaining should-fix items** (not blocking, deferred to future lanes):
- Bootstrap non-idempotence not documented
- `0.0.0.0` bind guard missing in daemon startup
- Spine "source of truth" language overstates its authority for pairing/miner state
- `pairing_granted` and `miner_alert` payload fields diverge from contract schema
- Pairing tokens are dead code (never validated)
- Concurrent file I/O has no locking (acceptable for single-operator M1)
- systemd + bootstrap script conflict not documented
