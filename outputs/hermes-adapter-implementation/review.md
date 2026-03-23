# Hermes Adapter Implementation — First Honest Review

**Status:** First Honest Reviewed Slice
**Generated:** 2026-03-23
**Reviewer:** Bootstrap Agent
**Spec type:** Capability Spec

---

## Review Scope

This review assesses the specification artifact (`outputs/hermes-adapter-implementation/spec.md`) for the Hermes Adapter Implementation frontier. No code has been written yet; this review covers whether the spec is self-contained, accurate, implementable, and aligned with the codebase as it exists today.

---

## Executive Summary

**Verdict: APPROVED — spec is complete and implementable. Proceed to implementation.**

The spec is self-contained, grounded in the actual codebase, and correctly scoped to Milestone 1.1. One minor factual error was corrected during review (EventKind value names). The spec is ready for the supervisory plane.

---

## Codebase Grounding

### EventKind enum — verified against `spine.py`

| Spec reference | spine.py actual | Match |
|----------------|-----------------|-------|
| `hermes_summary` | `EventKind.HERMES_SUMMARY = "hermes_summary"` | ✓ |
| `miner_alert` | `EventKind.MINER_ALERT = "miner_alert"` | ✓ |
| `control_receipt` | `EventKind.CONTROL_RECEIPT = "control_receipt"` | ✓ |
| `pairing_requested` | `EventKind.PAIRING_REQUESTED = "pairing_requested"` | ✓ |
| `pairing_granted` | `EventKind.PAIRING_GRANTED = "pairing_granted"` | ✓ |
| `capability_revoked` | `EventKind.CAPABILITY_REVOKED = "capability_revoked"` | ✓ |
| `user_message` | `EventKind.USER_MESSAGE = "user_message"` | ✓ |

### spine.py functions — verified

| Spec reference | spine.py actual | Match |
|----------------|-----------------|-------|
| `spine.get_events(limit=...)` | `get_events(kind=None, limit=100) -> list[SpineEvent]` | ✓ |
| `spine.append_hermes_summary(...)` | `append_hermes_summary(summary_text, authority_scope, principal_id)` | ✓ |
| `SpineEvent.kind: str` | `kind: str` (not enum) | ✓ |

### store.py functions — verified

| Spec reference | store.py actual | Match |
|----------------|-----------------|-------|
| `load_or_create_principal()` | exists, returns `Principal` | ✓ |
| `load_pairings()` / `save_pairings()` | exist, work on `pairing-store.json` | ✓ |

### daemon.py structure — verified

| Spec expectation | daemon.py actual | Match |
|-----------------|-----------------|-------|
| `miner.get_snapshot()` | exists on `MinerSimulator` | ✓ |
| ThreadedHTTPServer + BaseHTTPRequestHandler | present | ✓ |
| `/miner/start`, `/miner/stop`, `/miner/set_mode` | present | ✓ |

---

## Spec Completeness Assessment

### Architecture ✓

- In-process adapter (not separate service) — matches the codebase structure
- Token auth scheme uses two headers — correct and distinct from device auth
- Adapter imports from `spine.py` and `store.py` — no external dependencies added

### Data Models ✓

- `HermesAuthorityToken`, `HermesConnection`, `TokenValidationResult` — defined with all fields
- `HERMES_CAPABILITIES = ['observe', 'summarize']` — correct for Milestone 1.1
- `HERMES_READABLE_EVENT_KINDS` set uses correct snake_case string values from `EventKind`
- Pairing stored as `hermes_id`-keyed entry in `pairing-store.json` — distinct namespace from device pairings

### Token Validation Contract ✓

Four validation checks: structure (required JSON fields), expiry (ISO 8601 comparison), issuer (`zend-daemon` string match), capabilities (subset of `HERMES_CAPABILITIES`). All are implementable with stdlib only.

### Event Filtering ✓

Over-fetch strategy (`limit * 2`) is documented and justified. Filtering is a simple set membership check on `SpineEvent.kind`. Correct — no events with `kind == "user_message"` can reach Hermes.

### Endpoint Design ✓

Five endpoints defined with HTTP methods, auth requirements, and consistent JSON error format. Error table covers all failure modes: missing headers, invalid token, expired token, wrong issuer, missing capability, not paired.

### Deferred Items — Correctly Excluded ✓

- Encrypted authority tokens → Milestone 2
- Hermes `control` capability → deferred
- Rate limiting on Hermes endpoints → Milestone 2
- Daemon-owner auth on `/hermes/pair` → Milestone 2

---

## Plan Alignment

The spec covers all six frontier tasks from the bootstrap request:

| Frontier Task | Spec Coverage |
|---------------|---------------|
| Create `hermes.py` adapter module | Full `hermes.py` module with all functions defined |
| HermesConnection with authority token validation | `connect()` + `validate_authority_token()` with four-check contract |
| `read_status` through adapter | `read_status()` with `observe` check + `miner.get_snapshot()` |
| `append_summary` through adapter | `append_summary()` with `summarize` check + `spine_append_hermes_summary()` |
| Event filtering (block user_message events) | `get_filtered_events()` with over-fetch + set membership filter |
| Hermes pairing endpoint | `pair_hermes()` + `/hermes/pair` endpoint spec |

---

## Design Decisions — Validated

1. **Adapter in-process, not a separate service** — Correct for Milestone 1.1. Avoids network complexity; enforces boundary via code, not deployment.

2. **Authority token as JSON string (not signed/encrypted)** — Correct for Milestone 1.1 per plan. Tokens are opaque. Real token security is deferred.

3. **Over-fetch 2× for filtered events** — Sound strategy. Events are append-only; over-fetching is safe and ensures callers get readable events when the spine is dominated by filtered kinds.

4. **Pairing idempotent by `hermes_id`** — Re-pairing regenerates the authority token. Matches expected behavior for agent reconnection.

5. **`user_message` filtered at adapter, not at spine** — Correct. The spine is general-purpose; filtering is Hermes-specific. No spine change required.

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Authority tokens are plaintext JSON | Low (per plan) | Milestone 2 adds signing; Milestone 1 tokens are long-lived and LAN-only |
| `/hermes/pair` requires no auth | Low (per plan) | Production should require daemon-owner auth; deferred to Milestone 2 |
| No rate limiting on Hermes endpoints | Low | Deferred to Milestone 2 |
| Pairing store not encrypted at rest | Low | State dir is gitignored; deferred |

---

## Gaps for Future Slices

1. **Implementation not yet started** — spec is complete; code is next
2. **`tests/test_hermes.py` not written** — test file is defined in spec acceptance criteria
3. **CLI subcommands not added** — `hermes` subcommands in `cli.py` are future
4. **Gateway client Agent tab** — integration with the mobile app's Agent tab is deferred

---

## Review Verdict

**APPROVED — spec is complete and ready for the supervisory plane.**

The spec correctly:
- References the actual `EventKind` values from `spine.py`
- Uses the real `spine.py` and `store.py` function signatures
- Calls `miner.get_snapshot()` from the actual `MinerSimulator`
- Documents all four token validation checks with concrete implementation
- Specifies consistent JSON error format across all five endpoints
- Defers real token encryption, rate limiting, and pairing auth to Milestone 2
- Is self-contained: a novice with only this repo can implement from it

---

## Proof Commands

Once `hermes.py` and the daemon endpoints are implemented, verify against:

```bash
# Start daemon
cd services/home-miner-daemon
python3 daemon.py &
DAEMON_PID=$!

# Pair Hermes (no auth required — first-run)
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# Returns: {"hermes_id": "...", "capabilities": ["observe", "summarize"], ...}
# Extract authority_token from response

# Read status (requires observe)
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>"
# Returns miner snapshot

# Append summary (requires summarize)
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe"}'
# Returns appended SpineEvent

# Read filtered events (no user_message)
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>"
# Returns events with kinds: hermes_summary, miner_alert, control_receipt ONLY

# Verify control rejected (403)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>"
# Returns: 403 {"error": "hermes_forbidden", "message": "control capability required"}

# Run adapter tests
python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v

kill $DAEMON_PID
```

---

## Open Questions for Future Review

1. Should authority tokens use asymmetric signing for Milestone 2?
2. Should Hermes pairing require daemon-owner authentication?
3. Should Hermes endpoints have per-Hermes rate limiting?
4. When should Hermes gain `control` capability, and what safeguards are needed?
5. Should Hermes have a TTL on its authority token rather than a far-future expiry?
