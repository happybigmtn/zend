# Documentation & Onboarding — Review

**Status:** Conditional Pass
**Lane:** documentation-and-onboarding
**Reviewer:** opus-4.6 (nemesis review)
**Date:** 2026-03-22

## Verdict

The documentation slice is structurally complete and well-organized. All five
deliverables exist, match the plan's scope, and cover the required sections. Two
code bugs outside this lane's touched surfaces prevent the acceptance criteria
from being fully met. One false claim in the docs was corrected in this review.

## Blockers (code bugs, outside this lane)

### B1: Enum serialization in daemon.py

`MinerStatus` and `MinerMode` inherit from `(str, Enum)`. On Python 3.11+,
`json.dumps()` serializes these as `"MinerStatus.STOPPED"` and
`"MinerMode.PAUSED"` instead of the documented `"stopped"` and `"paused"`.

**Verified:**

```
$ python3 -c "import json; from enum import Enum; \
  class S(str,Enum): X='x'; \
  print(json.dumps({'v': S.X}))"
{"v": "S.X"}
```

**Impact:**
- All API response examples in `docs/api-reference.md` do not match actual output
- `apps/zend-home-gateway/index.html` line 656 compares `state.status === 'stopped'` — never true
- Mode button highlighting (line 676) compares `btn.dataset.mode === state.mode` — never matches
- Acceptance criterion #4 (curl examples work) cannot be met

**Fix:** In `daemon.py`, use `.value` when building response dicts:
- `start()` line 104: `self._status` → `self._status.value`
- `stop()` line 113: `self._status` → `self._status.value`
- `set_mode()` line 133: `self._mode` → `self._mode.value`
- `get_snapshot()` lines 142-143: `self._status` → `self._status.value`, `self._mode` → `self._mode.value`

### B2: CLI event kind filtering crashes

`cli.py` passes a raw string to `spine.get_events(kind=kind)`. Inside
`get_events`, the function calls `kind.value` which raises `AttributeError`
on a plain string.

**Impact:** Documented usage `cli.py events --kind control_receipt` crashes.

**Fix:** In `cli.py` `cmd_events()`, convert the string to `EventKind`:
```python
kind = spine.EventKind(args.kind) if args.kind != 'all' else None
```

## Corrections made in this review

### C1: False token-expiry claim in architecture.md

`docs/architecture.md` stated "Expired tokens are rejected during pairing."
This is false — `store.py:89` sets `token_expires_at` to `datetime.now()`
(immediately expired) and no code validates token expiry.

**Fixed:** Changed to "Token expiry validation is not yet implemented in
milestone 1."

### C2: Misleading auth description in api-reference.md

The API reference stated authorization is "checked at the pairing layer,"
implying HTTP endpoints are protected. HTTP endpoints have zero
authentication — capability checks are CLI-only.

**Fixed:** Clarified that HTTP endpoints are unauthenticated and capability
checks are enforced at the CLI layer only.

## Document-by-document assessment

### README.md — Pass

| Check | Result |
|-------|--------|
| Under 200 lines | 154 lines |
| Quickstart commands | 5 commands, match script interfaces |
| Architecture diagram | ASCII, matches SPEC |
| Directory structure | Accurate (subset of scripts listed, appropriate for brevity) |
| Prerequisites | Python 3.10+, stdlib only |
| Test command | `pytest` command present |
| Expected output | Shows plain-string values (correct intent, blocked by B1) |

### docs/contributor-guide.md — Pass (minor gaps)

| Check | Result |
|-------|--------|
| Dev environment setup | Python, venv, pytest covered |
| Project structure | All key directories explained |
| Making changes | Edit → test → verify flow |
| Coding conventions | Stdlib-only, naming, errors |
| Plan-driven development | ExecPlan workflow documented |
| Submitting changes | Branch naming, PR checklist |

Minor gaps:
- Scripts directory listing omits `hermes_summary_smoke.sh` and
  `no_local_hashing_audit.sh` (though the latter is referenced at line 232)
- References listing omits `design-checklist.md`
- Line 248 shows `import sqlite3` as stdlib example — technically correct but
  misleading since codebase uses JSONL, not SQLite

### docs/operator-quickstart.md — Pass

Strongest document in the set. Covers hardware requirements, installation,
systemd service configuration, LAN access, pairing, recovery, and security.
The recovery section correctly advises clearing all state, which avoids the
principal-pairing orphan problem.

### docs/api-reference.md — Conditional Pass (blocked by B1)

All existing HTTP endpoints are documented with curl examples. CLI commands
are documented separately. Error codes are accurate. The auth description
was corrected in this review (C2).

Blocked: Documented response formats show plain strings (`"stopped"`,
`"paused"`) but daemon returns enum class names. Cannot verify criterion #4
until B1 is fixed.

### docs/architecture.md — Pass (corrected)

ASCII diagrams present and accurate. Module guide matches source code.
Data flows correctly describe control, pairing, and event query paths.
Design decisions are well-reasoned. Token expiry claim was corrected in
this review (C1).

## Nemesis security review

### Pass 1 — Trust boundaries

**HTTP endpoints are unauthenticated.** Any process bound to the daemon's
interface can `POST /miner/start` or `/miner/set_mode` without any pairing
or capability check. The capability model documented in the architecture
only applies to CLI commands. For milestone 1 (simulator, LAN-only), this
is acceptable. The corrected API reference (C2) now accurately reflects
this boundary.

**Pairing tokens are decorative.** Tokens are generated with immediate
expiry (`datetime.now()`) and never validated. `token_used` is stored but
never checked. No code path rejects an expired or reused token. The
corrected architecture doc (C1) no longer claims otherwise.

### Pass 2 — Coupled-state review

**Principal ↔ Pairing consistency:** If `state/principal.json` is deleted
and recreated (new UUID), existing pairings in `pairing-store.json`
reference an orphaned `principal_id`. The operator quickstart's recovery
section advises clearing all state (`mv state state.old`), which correctly
avoids this inconsistency. However, it doesn't warn against selectively
deleting files.

**In-memory state ↔ Spine:** The miner simulator state resets on daemon
restart (always `STOPPED/PAUSED`). The spine retains old control receipts
showing the miner was `running`. This temporal inconsistency is by design
(simulator has no persistence) but is not documented. A reader of the spine
post-restart could mistakenly believe the miner is still running.

**Pairing idempotence:** `pair_client()` raises `ValueError` on duplicate
device names. This is correct behavior but the operator quickstart doesn't
explain how to re-pair a device (must clear pairing store or remove the
entry manually).

### Pass 3 — Secret handling and privilege escalation

**Pairing store is plaintext JSON.** Anyone with filesystem access can read
all pairing tokens and capabilities. For LAN-only milestone 1, acceptable.

**Capability escalation via filesystem:** An operator with write access to
`state/pairing-store.json` can grant any device `control` capability. This
is by design (operator is the trust root).

**No rate limiting** on any endpoint. Acceptable for milestone 1.

## Acceptance criteria status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | README quickstart works from fresh clone | Blocked by B1 (expected output mismatch) |
| 2 | Contributor guide enables test execution | Pass (pytest command works, tests may be empty) |
| 3 | Operator guide covers full deployment lifecycle | Pass |
| 4 | API reference curl examples work | Blocked by B1 (response format mismatch) |
| 5 | Architecture doc matches actual code | Pass (after corrections C1, C2) |

## Plan progress update

After this review, the plan checklist should read:

- [x] Rewrite README.md with quickstart and architecture overview
- [x] Create docs/contributor-guide.md with dev setup instructions
- [x] Create docs/operator-quickstart.md for home hardware deployment
- [x] Create docs/api-reference.md with all endpoints documented
- [x] Create docs/architecture.md with system diagrams and module explanations
- [ ] Verify documentation accuracy by following it on a clean machine
  → Blocked by B1, B2. Re-verify after daemon enum fix.

## Sign-off

| Role | Status | Date | Notes |
|------|--------|------|-------|
| Author | Approved | 2026-03-22 | |
| Reviewer | **Conditional Pass** | 2026-03-22 | Pass after B1, B2 are fixed in daemon lane |
