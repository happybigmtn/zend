# Hermes Adapter — Post-Implementation Review

**Reviewer:** Nemesis (first-principles + coupled-state)
**Date:** 2026-03-22
**Artifact:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/store.py`
**Source contract:** `references/hermes-adapter.md`

## Verdict

**CONDITIONALLY APPROVED — lane ready for supervisory plane.**

The adapter's domain model, capability enforcement, event filtering, and pairing lifecycle are correct and aligned with the reference contract. Three bugs were found and fixed during review. The code loads cleanly and all adapter functions behave as specified. One gap remains that must be addressed before this lane is fully done.

---

## What Was Done

### Bugs Fixed During Review

**BUG-1 — Dead `do_GET` shadow (daemon.py)**
The specify stage appended Hermes GET routes by defining a second `do_GET` method. Python silently shadows the first, so the original (lines 181–187) was dead code. No user-visible failure because the second definition handled everything correctly. Removed the first definition.

**BUG-2 — Auth header scheme mismatch (daemon.py)**
`_get_hermes_auth()` extracted the value after `Hermes ` from the `Authorization` header and passed it to `hermes_connect()`, which expects a JSON-encoded authority token. The documented scheme is `Authorization: Hermes <hermes_id>` (plain string), which fails JSON parsing on every authenticated request. Fixed by making `_get_hermes_auth()` look up the pairing by `hermes_id` directly, bypassing token parsing. `connect()` remains available for programmatic token-based connections.

**BUG-3 — `list_devices()` crash (store.py)**
Hermes pairings are stored in `state/pairing-store.json` with `hermes_id` fields that do not match `GatewayPairing`'s constructor (`id`). After any Hermes pairing, `list_devices()` raised `TypeError: unexpected keyword argument 'hermes_id'` for every caller. Fixed by filtering out `hermes:` prefixed keys in `list_devices()`.

---

## First-Principles Challenge

### Trust Boundaries

| Boundary | Assessment |
|----------|------------|
| Hermes cannot control miner | **Partial.** The adapter enforces this for Hermes-specific endpoints. But `/miner/start`, `/miner/stop`, `/miner/set_mode` have no auth at all — any LAN caller can trigger them. The adapter is a voluntary boundary, not an enforced one. |
| Hermes cannot read `user_message` | **Enforced.** `HERMES_READABLE_EVENTS` exclude `EventKind.USER_MESSAGE`. Applied in `get_filtered_events()`. |
| Authority token validates identity | **Weak.** Tokens are unsigned JSON. Anyone who knows a `hermes_id` can authenticate via the header scheme. Acceptable on LAN-only milestone 1. |
| Pairing requires approval | **Not enforced.** `POST /hermes/pair` creates a pairing immediately. The emitted `PAIRING_REQUESTED` / `PAIRING_GRANTED` events are cosmetic. |

### Dangerous Actions

| Action | Who Can Trigger | Guard |
|--------|----------------|-------|
| Pair Hermes agent | Any LAN client | None |
| Issue authority token | Any LAN client with `hermes_id` | Pairing must exist |
| Append summary to spine | Hermes with `summarize` | Capability check |
| Read miner status | Hermes with `observe` | Capability check |
| Start/stop miner | Any LAN client | **None** |

### Fragility

**Circular import.** `hermes.py:read_status()` imports `from daemon import miner` inside the function body (deferred). Daemon imports `hermes` at module level. This works but is fragile — moving the import to module level would break both modules simultaneously.

---

## Coupled-State Review

### Shared Pairing Store

Gateway and Hermes pairings share `state/pairing-store.json`. The `hermes:` prefix namespace prevents key collisions. After BUG-3 fix, `list_devices()` correctly filters Hermes entries and `list_hermes_pairings()` correctly filters gateway entries.

**Remaining concern:** No schema migration mechanism. If the pairing format changes, existing entries become unreadable. Low risk for milestone 1.

### Event Spine Consistency

`pair_hermes()` emits both `PAIRING_REQUESTED` and `PAIRING_GRANTED` events sequentially with no approval step between them. Honest for milestone 1, but the events become misleading once a real approval flow exists.

`append_summary()` wraps the single `authority_scope` string into a list before passing to `append_hermes_summary()`. The spine function expects `list[str]`. Works, but the type mismatch is implicit and should be documented or normalized at one end.

### Idempotence

Hermes pairing is idempotent by `hermes_id`. Re-pairing returns the existing record unchanged. This means a re-pair cannot refresh the token expiration or update `device_name`. An explicit renew/re-pair flow will be needed later.

### Token Replay

Authority tokens have no nonce or jti. Token reuse is indistinguishable from legitimate use. Appends are append-only with unique UUIDs, so replaying an append creates a duplicate event rather than corrupting state.

---

## Remaining Blockers

### Must address before lane is fully done

**[BLOCKER-1] Control endpoint protection.** The reference contract's milestone 1 boundary states "Hermes CANNOT issue control commands." The current `/miner/start`, `/miner/stop`, `/miner/set_mode` endpoints have no authentication whatsoever — Hermes or any LAN caller can trigger them. One of:

- Add a Hermes-rejection guard to all `/miner/*` endpoints, or
- Add device auth to `/miner/*` endpoints, or
- Explicitly document in the plan that control endpoint protection is deferred to the device-auth milestone

The plan's acceptance criteria cannot be met without one of these.

### Should address before network-facing deployment

**[SEC-1] Token signing.** Authority tokens are unsigned JSON. Before any non-LAN exposure, tokens need HMAC or asymmetric signing.

**[SEC-2] `/hermes/pairings` auth.** Listing all Hermes pairings requires no authentication. Should require at minimum gateway device auth.

**[SEC-3] Pairing approval flow.** `POST /hermes/pair` auto-approves. The emitted `PAIRING_REQUESTED` / `PAIRING_GRANTED` events bracket no real decision.

---

## Milestone Fit

| Plan Item | Status |
|-----------|--------|
| Create `hermes.py` adapter module | Done |
| `HermesConnection` with authority token validation | Done |
| `readStatus` through adapter | Done |
| `appendSummary` through adapter | Done |
| Event filtering (block `user_message`) | Done |
| Hermes pairing endpoint | Done |
| Hermes HTTP endpoints | Done |
| Update CLI with Hermes subcommands | Not in this slice |
| Update gateway client Agent tab | Not in this slice |
| Write tests | Not in this slice |

Plan milestones 1–2 are substantially complete. Milestones 3–4 (client update, tests) remain open.

---

## Recommended Next Steps

1. **Address BLOCKER-1** by either adding Hermes-rejection logic to `/miner/*` endpoints or documenting the deferral.
2. **Write tests** for the adapter functions and daemon endpoints.
3. **Update Agent tab** in the gateway client with Hermes status and approvals.
4. **Sign tokens and add pairing auth** before any network-facing deployment.
