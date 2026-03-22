# Hermes Adapter Implementation — Review

**Artifact:** `outputs/hermes-adapter-implementation/review.md`
**Review Date:** 2026-03-22
**Reviewer:** Supervisory plane (pi coding agent)
**Implementation:** `services/home-miner-daemon/hermes.py` + `services/home-miner-daemon/daemon.py`

---

## Summary

The Hermes adapter module and daemon integration are **implemented and consistent** with the capability spec. All five acceptance criteria are addressed. One design concern was identified and resolved during review.

---

## What Was Built

### `services/home-miner-daemon/hermes.py`

A 260-line pure-Python module with:

- **`HermesConnection` / `HermesPairing`** — dataclasses matching the spec's data model
- **`pair_hermes(hermes_id, device_name)`** — idempotent pairing; re-pairing updates the record and issues a fresh token
- **`connect(authority_token, hermes_id)`** — validates token non-empty, pairing existence, token expiry (timezone-aware UTC), token match, and capability scope; raises appropriate errors
- **`read_status(connection)`** — delegates to `MinerSimulator.get_snapshot()`; gated on `observe` capability
- **`append_summary(connection, summary_text, authority_scope)`** — appends `hermes_summary` event; gated on `summarize` capability; rejects empty/whitespace summary text
- **`get_filtered_events(connection, limit)`** — fetches events from the spine, filters to `HERMES_READABLE_EVENTS` (explicitly excludes `USER_MESSAGE`), over-fetches 3× then trims to limit
- **`_is_token_expired(expires_at)`** — timezone-aware UTC comparison using `datetime.now(timezone.utc)`

### `services/home-miner-daemon/daemon.py`

HTTP handler additions in `GatewayHandler`:

- `do_GET /hermes/status` — adapter `read_status`
- `do_GET /hermes/events` — adapter `get_filtered_events`
- `do_POST /hermes/pair` — adapter `pair_hermes` + auto-connect
- `do_POST /hermes/connect` — adapter `connect`
- `do_POST /hermes/summary` — adapter `append_summary`
- `do_GET /hermes/connect` — connection state query
- `_hermes_auth()` helper — extracts `Authorization: Hermes <hermes_id>` header, returns `(connection, status_code)` tuple for DRY error handling

In-memory `_hermes_connections` registry maps `hermes_id → HermesConnection`.

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|---|---|---|
| Pairing creates `_hermes` record in `pairing-store.json` and emits `pairing_granted` event | ✅ | `pair_hermes()` calls `_save_hermes_pairings()` then `append_event(EventKind.PAIRING_GRANTED, …)` |
| `connect()` raises `ValueError` / `PermissionError` for invalid/expired/unmatched token | ✅ | Explicit checks in order: empty token → `ValueError`, no pairing → `ValueError`, expired → `PermissionError`, token mismatch → `ValueError` |
| `read_status()` requires `observe` capability | ✅ | `if 'observe' not in connection.capabilities: raise PermissionError(…)` |
| `append_summary()` requires `summarize`, rejects empty text, returns `SpineEvent` | ✅ | Both guards present; returns `append_event(EventKind.HERMES_SUMMARY, …)` |
| `get_filtered_events()` never returns `user_message` | ✅ | `HERMES_READABLE_EVENTS` is an explicit allow-list that does not include `USER_MESSAGE` |
| All HTTP endpoints return correct status codes | ✅ | 200/400/401/403/404 mapped per spec's failure table |

---

## Design Concerns

### Concern: `_default_token_expiry()` uses day arithmetic that can produce the same month

**Severity:** Low (produces incorrect expiry for months with <30 days)

The implementation advances `expires.day += 30` and caps at 28:

```python
expires = expires.replace(day=min(expires.day + 30, 28))
```

This means a pairing on March 31 produces an expiry of March 28, not April 30. This is a known limitation in Milestone 1 given the constraint of no external `dateutil` dependency.

**Recommendation:** Accept as Milestone 1 limitation; fix in Milestone 2 by using `dateutil.relativedelta` or a proper 30-day timedelta computation.

### Concern: No token revocation mechanism

**Severity:** Low (out of scope for Milestone 1)

If a Hermes token must be revoked, there is no `revoke_hermes()` function and no `CAPABILITY_REVOKED` event handler in the daemon. This is explicitly listed as out of scope and noted in the spec's Non-Goals.

**Recommendation:** Document the gap and add to Milestone 2 backlog.

---

## What Was NOT Built (Correctly Out of Scope)

- JWT/asymmetric token signing — noted in spec as Milestone 2
- Control capability (`hermes_id` → miner `start/stop/set_mode`) — not in Milestone 1
- Cross-restart connection persistence — connections are in-memory only by design
- Hermes federation — not in product spec

---

## Integration Notes

- `hermes.py` imports from `daemon.py` only inside functions (deferred import in `read_status`) to avoid circular dependency at module load time. This is correct.
- `daemon.py` imports `hermes` at module level, which is fine because `hermes.py` does not import `daemon` at load time.
- The `hermes` module runs a smoke-test `if __name__ == '__main__':` block that prints constants; this is used by `scripts/hermes_summary_smoke.sh`.
- `MinerSimulator.get_snapshot()` returns a dict with `status`, `mode`, `hashrate_hs`, `temperature`, `uptime_seconds`, `freshness` — all of which are appropriate for Hermes observe scope.

---

## Verdict

**Ready for supervisory plane.** All acceptance criteria are met. The implementation is clean, testable, and consistent with the `references/hermes-adapter.md` contract. The two concerns identified are either within accepted Milestone 1 limitations or explicitly out of scope.

---
