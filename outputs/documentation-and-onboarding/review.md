# Documentation & Onboarding Lane — Nemesis Review

**Status:** CONDITIONAL PASS
**Reviewer:** Nemesis (automated adversarial review)
**Lane:** documentation-and-onboarding
**Plan:** genesis/plans/008-documentation-and-onboarding.md
**Date:** 2026-03-22

## Verdict

The documentation plan is structurally sound and the milestones are well-scoped. However, the plan contains factual claims about the codebase that are wrong. If a contributor follows the plan as written, they will document phantom endpoints, phantom environment variables, and an auth model that does not match reality. These are not taste issues — they are correctness failures that would produce documentation that breaks on first use.

**Conditional pass:** the plan can proceed if the factual errors listed below are corrected first. No architectural changes needed.

---

## Pass 1 — First-Principles Challenge

### Trust Boundaries

**Finding: The plan misrepresents where auth enforcement happens.**

The plan (Milestone 4) says endpoints require "Authentication requirement (none, observe, control)." In reality, the daemon HTTP layer (`daemon.py`) has zero auth enforcement. Any process on the LAN can call `/miner/start`, `/miner/stop`, `/miner/set_mode` without presenting any credential or capability token.

Auth checks happen only in `cli.py` — the CLI looks up the device name in `store.py` and checks capabilities before making the HTTP call. The shell scripts wrap this CLI. But the daemon itself is unauthenticated.

**Risk for documentation:** If the API reference documents endpoint-level auth ("requires control capability"), an operator will believe the daemon is protected. It is not. An attacker on the same LAN can POST directly to the daemon.

**Recommendation:** The API reference must document this accurately: "The daemon HTTP API has no authentication. Access control is enforced by the CLI layer. In milestone 1, LAN isolation is the sole security boundary."

### Authority Assumptions

**Finding: Token expiration is a dead stub.**

`store.py:89` sets `token_expires_at = datetime.now(timezone.utc).isoformat()` — every token expires at creation time. The token value itself (a UUID) is generated but never stored in a retrievable lookup, never checked on subsequent calls, and `token_used` is always `False`. The entire trust ceremony around tokens is structural fiction in milestone 1.

**Risk for documentation:** The operator quickstart (Milestone 3) references "ZEND_TOKEN_TTL_HOURS" as a configurable environment variable. This variable does not exist anywhere in the code. No code reads it. If documented, operators will set it and wonder why it has no effect.

**Recommendation:** Operator quickstart must document only the four real env vars: `ZEND_STATE_DIR`, `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_DAEMON_URL`. Note that token TTL configuration is planned but not yet implemented.

### Who Can Trigger Dangerous Actions

The daemon's `MinerSimulator` is an in-process simulator with no external side effects. The "dangerous" actions (start, stop, set_mode) only change in-memory state. This is appropriate for milestone 1 but must be stated explicitly in the architecture doc so operators don't mistake the simulator's safety for daemon-level auth.

---

## Pass 2 — Coupled-State Review

### Phantom Endpoints

**Finding: Three endpoints in the plan do not exist in the daemon.**

The plan's Milestone 4 lists these endpoints to document:

| Endpoint | Exists in daemon.py? |
|----------|---------------------|
| `GET /health` | YES |
| `GET /status` | YES |
| `GET /spine/events` | NO — events are accessed via `cli.py events`, not HTTP |
| `GET /metrics` | NO — no metrics endpoint exists |
| `POST /miner/start` | YES |
| `POST /miner/stop` | YES |
| `POST /miner/set_mode` | YES |
| `POST /pairing/refresh` | NO — no pairing refresh endpoint exists |

If the documentation lane creates an API reference with these phantom endpoints and includes curl examples, every curl for `/spine/events`, `/metrics`, and `/pairing/refresh` will return `{"error": "not_found"}` with HTTP 404.

**Recommendation:** Strike the three phantom endpoints from Milestone 4. Document only the five real routes. If the events endpoint is desired, document the CLI interface instead (`python3 cli.py events`).

### State Consistency: Pairing Store vs Event Spine

Pairing is recorded in two places: `store.py` writes to `pairing-store.json` and `spine.py` appends to `event-spine.jsonl`. These writes are not atomic. If the process crashes between the store write and the spine append, the pairing exists in the store but has no event trail. The documentation should note this as a known limitation of the milestone 1 implementation.

### Health Endpoint Response Shape

**Finding: `/health` does not return `{"status": "ok"}`.**

The plan's Milestone 1 says: "A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{\"status\": \"ok\"}`."

The actual `/health` endpoint returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`. There is no `"status"` key. Documentation must show the real response shape.

### Data Flow: CLI Working Directory

**Finding: The CLI has an implicit working-directory dependency.**

`cli.py` line 17: `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` means it works by importing `store` and `spine` as sibling modules. The plan's quickstart shows running `python3 services/home-miner-daemon/cli.py status --client my-phone` from the repo root. This works because of the `sys.path` manipulation, but the contributor guide should note this is a single-directory package, not an installed module.

---

## Pass 3 — Security & Operator Safety

### LAN Binding Is Not Enforced by Code

The daemon defaults to `127.0.0.1` (loopback only, not LAN-accessible). To actually use it from a phone on the same LAN, the operator must set `ZEND_BIND_HOST` to their LAN IP (e.g., `192.168.1.x`). The operator quickstart must cover this transition explicitly and warn that binding to `0.0.0.0` exposes the unauthenticated daemon to the entire network.

The plan says "LAN-only binding, what to check, what not to expose" in Milestone 3 but the implementation has no runtime check that prevents binding to a public interface. An operator who sets `ZEND_BIND_HOST=0.0.0.0` gets an internet-exposed unauthenticated miner control API with no warning.

**Recommendation:** The operator quickstart should include a boxed warning: "The daemon has no authentication at the HTTP level. Binding to `0.0.0.0` or a public interface exposes full miner control to anyone who can reach the port. Milestone 1 assumes LAN isolation as the sole security boundary."

### State Directory Permissions

State files (`principal.json`, `pairing-store.json`, `event-spine.jsonl`) are written with default umask permissions. On a multi-user system, these are world-readable, leaking the principal ID, pairing records, and all event payloads. The operator quickstart should advise `umask 077` or explicit `chmod 600` on the state directory.

### PID File Race Condition

`bootstrap_home_miner.sh` checks `kill -0 "$PID"` to detect a running daemon, but there's a TOCTOU window: the old PID could be recycled by another process between the check and the kill. The script also force-kills (`kill -9`) after 1 second, which could hit a recycled PID. Low risk in single-user home deployment but should be noted in the contributor guide.

### Event Spine Is Plaintext

The plan and spec repeatedly say "encrypted event spine" and "encrypted operations inbox." The implementation writes plaintext JSONL. This is noted in the existing home-command-center review as a known gap, but the documentation lane must not perpetuate the "encrypted" claim in user-facing docs. Documentation should say "event journal" and note that encryption at rest is planned for a future milestone.

---

## Blockers

These must be fixed before the lane produces accurate documentation:

| # | Blocker | Location | Fix |
|---|---------|----------|-----|
| 1 | Phantom endpoints `/spine/events`, `/metrics`, `/pairing/refresh` | Plan Milestone 4 | Strike from endpoint list; document CLI `events` command instead |
| 2 | Phantom env var `ZEND_TOKEN_TTL_HOURS` | Plan Milestone 3 | Remove from env var table |
| 3 | Wrong `/health` response shape | Plan Milestone 1 proof | Change `{"status": "ok"}` to `{"healthy": true, "temperature": ..., "uptime_seconds": ...}` |
| 4 | Auth model described at HTTP level | Plan Milestone 4 | Clarify that auth is CLI-layer only; daemon is unauthenticated |

## Warnings (Non-blocking)

| # | Warning | Risk |
|---|---------|------|
| 1 | Token TTL is a dead stub | Operator docs may imply configurable token expiry that doesn't work |
| 2 | Spine writes not atomic with store writes | Crash can leave pairing with no event trail |
| 3 | State files have default umask | Multi-user systems leak principal and events |
| 4 | No runtime guard against public bind | `0.0.0.0` binding creates unauthenticated internet exposure |
| 5 | "Encrypted" language in plan vs plaintext reality | User-facing docs must not claim encryption that doesn't exist |
| 6 | PID file TOCTOU in bootstrap script | Force-kill can hit recycled PID on multi-process systems |

## Milestone Fit

The six plan milestones map well to the codebase's current state:

| Milestone | Feasibility | Notes |
|-----------|-------------|-------|
| 1: README rewrite | Ready | Must use correct health response and real env vars |
| 2: Contributor guide | Ready | Note single-directory package, no pip install |
| 3: Operator quickstart | Ready with caveats | Must exclude phantom env var, include LAN binding guidance |
| 4: API reference | Blocked on corrections | Must strip phantom endpoints, clarify auth model |
| 5: Architecture doc | Ready | Must not claim encryption at rest |
| 6: Verification | Deferred | Requires running daemon; plan suggests CI job in future |

## Remaining Work After This Lane

- CI job to verify quickstart commands on each push
- Actual token TTL implementation with configurable expiry
- HTTP-level auth (even a bearer token) for daemon endpoints
- Encryption at rest for the event spine
- State file permission hardening

## Summary

The plan is well-structured and the milestones are independently valuable. The primary risk is that the plan was written against a _planned_ API surface rather than the _implemented_ one. Four factual corrections are required before implementation begins. With those fixes, the lane can produce documentation that is honest and verifiable.
