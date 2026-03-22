# Documentation & Onboarding Lane — Nemesis Review

**Status:** CONDITIONAL PASS — 4 blockers must be corrected before implementation
**Reviewer:** Nemesis (adversarial)
**Lane:** documentation-and-onboarding
**Date:** 2026-03-22

---

## Verdict

The lane goal is sound and the artifact inventory is well-scoped. However, the plan contains factual errors about the codebase that would produce documentation contradicting reality. Four are blockers; the rest are warnings. With the corrections below, the lane can produce honest, verifiable documentation.

---

## Blockers (Must Fix Before Implementation)

### B1 — Phantom Endpoints

Three endpoints in the plan do not exist in `daemon.py`. Documenting them with curl examples will produce `404 not_found` on first use.

| Phantom Endpoint | Plan Says | Reality |
|-----------------|-----------|---------|
| `GET /spine/events` | Document with curl | Events are read via `cli.py events`, not HTTP |
| `GET /metrics` | Document with curl | No metrics endpoint exists |
| `POST /pairing/refresh` | Document with curl | No refresh endpoint exists |

**Fix:** Document only the five real routes (`/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`). For event queries, document the CLI interface: `python3 cli.py events --client <name> --kind <kind> --limit <N>`.

---

### B2 — Phantom Environment Variable `ZEND_TOKEN_TTL_HOURS`

The operator quickstart references `ZEND_TOKEN_TTL_HOURS` as a configurable environment variable. No code reads this variable. It does not exist.

**Fix:** Remove from all env var tables. The four real env vars are: `ZEND_STATE_DIR`, `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_DAEMON_URL`. If you want to document planned behavior, clearly label it as "planned — not yet implemented."

---

### B3 — Wrong `/health` Response Shape

The README quickstart proof-of-success states: `{"status": "ok"}`. The actual response is:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

There is no `"status"` key.

**Fix:** Use the correct response shape in all examples and acceptance criteria.

---

### B4 — Auth Model Misrepresented at HTTP Level

The API reference plan describes auth requirements per endpoint ("requires observe", "requires control"). This is false. The daemon HTTP layer (`daemon.py`) has **zero auth enforcement**. Any process on the LAN can POST to `/miner/start`, `/miner/stop`, or `/miner/set_mode` without presenting any credential.

Auth checks live in `cli.py` and the shell scripts. The CLI looks up the device name in `store.py` and verifies capabilities before making the HTTP call. But the daemon itself is completely unauthenticated.

**Fix:** The API reference must include a prominent notice: "The daemon HTTP API has no authentication. Access control is enforced at the CLI layer. In milestone 1, LAN isolation is the sole security boundary." Each endpoint should show "Auth: None (HTTP layer)".

---

## Warnings (Document, But Do Not Block)

### W1 — Token Expiration Is a Dead Stub

`store.py:89`: `token_expires_at = datetime.now(timezone.utc).isoformat()` — every token expires at the moment it is created. The token value (a UUID) is generated but never stored for lookup, never checked on subsequent calls, and `token_used` is always `False`. The entire token trust ceremony is structural fiction in milestone 1.

Risk: Operator docs that imply configurable token TTL will mislead readers.

---

### W2 — Pairing Store and Spine Writes Are Not Atomic

`store.py` writes to `pairing-store.json` and `spine.py` appends to `event-spine.jsonl` separately. If the process crashes between the two writes, a pairing exists in the store with no event trail. The architecture doc and operator quickstart should note this as a known limitation.

---

### W3 — State Files Have Default Umask Permissions

`principal.json`, `pairing-store.json`, and `event-spine.jsonl` are written with the process umask (typically `022`). On a multi-user system, these files are world-readable, leaking the principal ID, all pairing records, and every event payload.

Risk: Shared hosting or family-shared systems.

---

### W4 — No Runtime Guard Against Public Binding

The daemon defaults to `127.0.0.1` (loopback only). To use from a LAN client, the operator must set `ZEND_BIND_HOST` to their LAN IP. There is no runtime check preventing `ZEND_BIND_HOST=0.0.0.0`. An operator who sets that exposes an unauthenticated miner control API to the entire internet.

**Fix:** The operator quickstart must include a boxed warning about this and recommend binding only to the specific LAN interface.

---

### W5 — Event Spine Is Plaintext

The plan and spec use the phrase "encrypted event spine." The implementation writes plaintext JSONL. User-facing docs must not claim encryption that does not exist.

**Fix:** Use "event journal" or "event spine" without the "encrypted" adjective. Note that encryption at rest is planned for a future milestone.

---

### W6 — PID File TOCTOU in Bootstrap Script

`bootstrap_home_miner.sh` checks `kill -0 "$PID"` then `kill -9 "$PID"`. Between the check and the signal, the PID could be recycled by another process. Low risk on a single-user home machine, but should be noted in the contributor guide for operators on shared systems.

---

## Milestone Feasibility

| Milestone | Ready? | Notes |
|-----------|--------|-------|
| 1: README rewrite | Ready (after B3 fix) | Must use correct `/health` shape and real env vars |
| 2: Contributor guide | Ready | Note the single-directory package constraint; no `pip install` needed |
| 3: Operator quickstart | Ready (after B2, B4 fixes) | Exclude phantom env var; include LAN binding warning; note umask risk |
| 4: API reference | Blocked (B1, B4) | Strip phantom endpoints; clarify daemon has no auth |
| 5: Architecture doc | Ready (after W5 fix) | Must not claim encryption at rest |
| 6: Verification | Deferred | Requires live daemon; CI job is a post-lane item |

---

## Remaining Work After Lane

These are not in scope for this lane but must not be forgotten:

- CI job to verify quickstart commands on every push
- HTTP-level authentication for daemon endpoints (even a simple bearer token)
- Working token TTL implementation with configurable expiry
- Encryption at rest for the event spine
- State directory permissions hardening (`chmod 700` or `umask 077`)

---

## Summary

The lane structure is right. The primary failure mode is documentation written against a *planned* API surface rather than the *implemented* one. Four factual corrections are blockers. With those in place, the lane can produce documentation that is honest, verifiable, and specific to the codebase as it exists today.
