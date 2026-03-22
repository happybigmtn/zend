# Documentation & Onboarding Lane — Review

**Status:** FAILED — no artifacts produced
**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-22

## Executive Summary

The documentation-and-onboarding lane's specify stage reported "success" but produced
nothing. MiniMax-M2.7-highspeed logged 0 tokens in / 0 tokens out. The required
output artifact `outputs/documentation-and-onboarding/spec.md` does not exist. None
of the six frontier tasks were started. One declared input
(`genesis/plans/001-master-plan.md`) does not exist in the repository.

This is a **silent failure masquerading as success** — the most dangerous kind.

---

## 1. Artifact Audit

### Required Artifacts

| Artifact | Exists | Notes |
|----------|--------|-------|
| `outputs/documentation-and-onboarding/spec.md` | NO | Specify stage produced nothing |
| `outputs/documentation-and-onboarding/review.md` | YES | This file |

### Frontier Tasks

| Task | Status | Evidence |
|------|--------|----------|
| Rewrite README.md with quickstart and architecture overview | NOT DONE | README.md is unchanged planning-only boilerplate |
| Create docs/contributor-guide.md | NOT DONE | File does not exist |
| Create docs/operator-quickstart.md | NOT DONE | File does not exist |
| Create docs/api-reference.md | NOT DONE | File does not exist |
| Create docs/architecture.md | NOT DONE | File does not exist |
| Verify documentation accuracy on clean machine | NOT DONE | No documentation to verify |

### Input Audit

| Input | Exists | Notes |
|-------|--------|-------|
| `README.md` | YES | Planning-only, not a quickstart |
| `SPEC.md` | YES | Spec authoring guide |
| `SPECS.md` | YES | One-line redirect to SPEC.md |
| `PLANS.md` | YES | ExecPlan authoring guide |
| `DESIGN.md` | YES | Visual design system |
| `genesis/plans/001-master-plan.md` | NO | Directory does not exist |

---

## 2. Correctness

Zero. Nothing was produced. The specify stage's "success" status is incorrect
and must be treated as a hard failure.

The 0/0 token count indicates the model was invoked but either received an empty
prompt, returned an empty response, or the provider call silently failed. In any
case, no specification was written, and no downstream work was possible.

---

## 3. Milestone Fit

The documentation lane is supposed to make Zend approachable for three audiences:

1. **Contributors** — need dev setup, architecture orientation, codebase map
2. **Operators** — need home-hardware deployment instructions
3. **API consumers** — need endpoint reference for the daemon

Today, none of these audiences are served. The existing README describes Zend as
"the canonical planning repository" and lists document paths. It does not explain
how to start the daemon, pair a client, or understand the architecture. A new
contributor cloning this repo would need to read the ExecPlan (800+ lines) to
figure out what to do. That defeats the purpose of documentation.

The implementation artifacts from the home-command-center lane (daemon, CLI,
scripts, gateway UI) exist and are functional, but completely undocumented for
external use.

---

## 4. Remaining Blockers

1. **Specify stage must be re-run** with a functioning model. The MiniMax
   provider produced nothing.
2. **Missing input**: `genesis/plans/001-master-plan.md` does not exist.
   Either create it or remove it from the input list.
3. **README.md rewrite** should be the first documentation artifact — it's the
   front door of the repo.
4. **API reference** can be derived mechanically from `daemon.py` (5 endpoints)
   and `cli.py` (6 subcommands).
5. **Architecture doc** has strong source material in the ExecPlan's diagrams
   and the product spec, but needs to be extracted into standalone form.

---

## 5. Nemesis Security Review

The documentation lane itself has no security surface, but the implementation
it should document has serious security issues that any honest documentation
must disclose. A documentation lane that omits security warnings is actively
dangerous — it gives false confidence to operators deploying the system.

### Pass 1 — First-Principles Trust Boundary Challenge

#### Finding 1: CRITICAL — Daemon has NO authentication

The HTTP daemon (`services/home-miner-daemon/daemon.py`) accepts all requests
without authentication. The capability model (`observe`/`control`) exists only
in `cli.py` and `store.py`. It is never enforced at the HTTP layer.

**Who can trigger dangerous actions:** Any process on the LAN that can reach
`BIND_HOST:BIND_PORT`. The daemon exposes `/miner/start`, `/miner/stop`, and
`/miner/set_mode` as unauthenticated POST endpoints. Bypassing the CLI and
calling the daemon directly skips all capability checks.

The entire pairing ceremony is theater if the daemon itself doesn't validate
the caller's identity. An attacker on the same network can control the miner
without ever pairing.

**Blast radius:** Full unauthorized miner control. Mode changes, start/stop.
In a future milestone with payout-target mutation, this would be catastrophic.

#### Finding 2: CRITICAL — Pairing tokens never expire

`store.py:89` sets `expires` to `datetime.now(timezone.utc).isoformat()` —
the current time, not a future time. There is no code path that validates
token expiration. The `PairingTokenExpired` error in the taxonomy is defined
but never raised. Pairing tokens are permanent.

#### Finding 3: HIGH — No CORS, no CSRF

The daemon sends no CORS headers. The gateway client (`index.html`) hardcodes
`API_BASE = 'http://127.0.0.1:8080'`. If served from any origin other than
`127.0.0.1:8080` (including `file://`), the browser blocks requests. There
is also no CSRF protection on state-changing endpoints. Any page the user
visits could issue cross-origin requests to the daemon (browser CORS
enforcement varies for simple requests vs. preflighted ones — POST with
`Content-Type: application/json` is preflighted, but the daemon doesn't
check the Origin header even if CORS were configured).

#### Finding 4: HIGH — Event spine stores plaintext

The spec requires "encrypted event journal" and "encrypted operations inbox."
The implementation writes plaintext JSONL to `state/event-spine.jsonl`. No
encryption is applied. The file is created with default permissions (typically
644), making it world-readable. PrincipalIds, device names, control commands,
and Hermes summaries are all stored in the clear.

#### Finding 5: MEDIUM — Bootstrap bypasses trust ceremony

`cli.py:cmd_bootstrap` creates a pairing with `observe` capability and emits
a `pairing_granted` event — but skips the `pairing_requested` event. The
audit trail shows a grant without a request. The plan's "trust ceremony" is
described in the design but not implemented; bootstrap auto-grants without
user confirmation.

### Pass 2 — Coupled-State Consistency

#### Finding 6: CRITICAL — Capability enforcement is split-brain

The system has two layers that should agree on authorization but don't
communicate:

- **CLI layer** (`cli.py`): checks `has_capability()` before issuing
  daemon calls
- **Daemon layer** (`daemon.py`): accepts all requests unconditionally

This is not defense-in-depth — it's a single enforcement point with a
trivial bypass. The daemon is the actual authority (it does the work), but
it has no concept of authorization. The CLI is a convenience wrapper that
can be circumvented with `curl`.

A correct design enforces capabilities at the daemon level, with the CLI
as a thin client that passes tokens.

#### Finding 7: HIGH — Control command serialization not implemented

The ExecPlan requires: "Control commands must be serialized. The plan must
state how the daemon handles two competing control requests."

The daemon uses `threading.Lock()` on individual operations (start, stop,
set_mode), which prevents concurrent mutation of the miner state. But there
is no command queue, no conflict detection, and no `ControlCommandConflict`
error ever raised. Two simultaneous `set_mode` calls both succeed — the
last one wins silently. The plan's error taxonomy defines this failure
class but nothing implements it.

#### Finding 8: HIGH — No capability revocation

`EventKind.CAPABILITY_REVOKED` is defined. The error taxonomy references
`capability_revoked`. But no code path in cli.py, store.py, or daemon.py
implements revocation. Once a device is paired, it stays paired permanently.
A compromised device cannot have its access removed.

#### Finding 9: MEDIUM — File state has no integrity protection

State files (`principal.json`, `pairing-store.json`, `event-spine.jsonl`)
are plain JSON/JSONL with no checksums, no signatures, and no file locking
beyond what the OS provides for `open()`. A corrupted or tampered state file
would be loaded without validation. The event spine claims to be
"append-only" but nothing prevents truncation or modification.

#### Finding 10: MEDIUM — PrincipalId in localStorage

The gateway client (`index.html`) stores the PrincipalId in browser
localStorage with a hardcoded fallback UUID
(`550e8400-e29b-41d4-a716-446655440000`). Any script on the same origin
can read it. The fallback UUID means every uninitialized client shares the
same identity.

### Security Findings Summary

| # | Severity | Finding | Component |
|---|----------|---------|-----------|
| 1 | CRITICAL | Daemon has no authentication | daemon.py |
| 2 | CRITICAL | Pairing tokens never expire | store.py |
| 6 | CRITICAL | Capability enforcement is split-brain | daemon.py + cli.py |
| 3 | HIGH | No CORS, no CSRF | daemon.py + index.html |
| 4 | HIGH | Event spine stores plaintext | spine.py |
| 7 | HIGH | Control serialization not implemented | daemon.py |
| 8 | HIGH | No capability revocation | store.py |
| 5 | MEDIUM | Bootstrap bypasses trust ceremony | cli.py |
| 9 | MEDIUM | File state has no integrity protection | store.py, spine.py |
| 10 | MEDIUM | PrincipalId in localStorage | index.html |

### What Documentation Must Address

Any honest operator quickstart or contributor guide produced by this lane
MUST disclose:

1. The daemon is unauthenticated — LAN-only is a network boundary, not a
   security boundary
2. The event spine is not encrypted despite the spec saying it is
3. Pairing does not implement expiration or revocation
4. The system is a milestone 1 proof-of-concept, not production-ready
5. The gap between the spec's security claims and the implementation's
   actual security posture

Documentation that presents this system as "encrypted" or "capability-scoped"
without these caveats would be misleading.

---

## 6. Verdict

**LANE FAILED.** No artifacts were produced. Re-run required.

### Before Re-run

1. Fix the model provider issue (MiniMax-M2.7-highspeed produced 0 tokens)
2. Remove or create `genesis/plans/001-master-plan.md` as an input
3. Ensure the spec stage writes `outputs/documentation-and-onboarding/spec.md`

### When Re-running

The documentation spec should require:
- README quickstart with working `bootstrap -> pair -> status -> control` flow
- Honest security posture section in all docs
- API reference derived from actual daemon.py endpoints
- Architecture doc extracted from ExecPlan diagrams
- Operator guide with hardware requirements and LAN binding instructions
- Contributor guide with dev setup (Python 3, no dependencies beyond stdlib)
