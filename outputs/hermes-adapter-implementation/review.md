# Hermes Adapter Implementation — Review

**Status:** Plan reviewed, implementation not started
**Reviewed:** 2026-03-22
**Plan source:** Inline (genesis/plans/009-hermes-adapter-implementation.md not on disk)
**Specify stage:** MiniMax-M2.7-highspeed produced 0 tokens — no specification was generated

## Lane State

**Implementation progress: 0%.** No code artifacts were produced. The specify stage generated nothing. The plan exists only in the lane prompt, not on disk.

**What exists (pre-lane, from M1 command center):**
- `spine.py` has `EventKind.HERMES_SUMMARY` and `append_hermes_summary()` — the write path exists
- `store.py` has `GatewayPairing` with capability checking — extensible to Hermes
- `daemon.py` has HTTP routing but no Hermes endpoints and no auth middleware
- `hermes_summary_smoke.sh` calls spine directly — bypasses any adapter

**What the plan promises (not yet built):**
- `hermes.py` adapter module with HermesConnection, connect, read_status, append_summary, get_filtered_events
- 5 new HTTP endpoints in daemon.py
- 8 tests in test_hermes.py
- CLI Hermes subcommands
- Agent tab live connection state

## Correctness Assessment

### Plan is structurally sound with 3 blockers

The plan's 4-milestone decomposition (adapter module, daemon endpoints, client update, tests) is reasonable. The code sketches in the plan are close to correct against the existing codebase. However, three issues must be resolved before implementation can proceed honestly.

### Blocker 1: Authority token model doesn't exist (H2)

The plan's `connect(authority_token: str)` assumes a token that encodes principal_id, capabilities, and expiration. No such token format exists in the codebase. `store.create_pairing_token()` returns a bare UUID with no embedded claims.

**Resolution:** The spec simplifies to pairing-based auth for M1. Hermes authenticates by `hermes_id` lookup in the store, not by token decoding. This matches the LAN-only trust model and avoids building JWT infrastructure for a local-network-only milestone.

### Blocker 2: Daemon has no auth layer — capability boundary is bypassable (H1)

The plan claims "Hermes CANNOT issue control commands (403)" but the daemon's `/miner/start` endpoint has no auth check. Any HTTP client on the LAN can call it. The adapter is a self-imposed constraint within `hermes.py`, not an enforced boundary at the HTTP layer.

**Resolution:** The spec documents this explicitly as an M1 limitation. Implementation should add Hermes auth checking to the `/hermes/*` routes, and the review accepts that `/miner/*` routes remain open for M1. A follow-up plan should add daemon-level auth middleware that gates all routes.

### Blocker 3: `authority_scope` type mismatch (H9)

The plan passes `authority_scope: str` to `append_summary`, but `spine.append_hermes_summary()` expects `authority_scope: list`. This will produce malformed spine events.

**Resolution:** Fixed in spec. `append_summary` must pass `authority_scope` as `list` to match the existing spine interface.

## Milestone Fit

| Milestone | Fit | Notes |
|-----------|-----|-------|
| M1 Adapter Module | Good | Clean module boundary, correct delegation to spine/store |
| M2 Daemon Endpoints | Good | Straightforward HTTP routing addition |
| M3 Client Update | Acceptable | Agent tab update is UI-only, low risk |
| M4 Tests | Good | 8 tests cover the critical boundaries |

The plan fits within the M1 scope. It doesn't over-reach into M2 concerns (internet-facing auth, encrypted transport) and correctly limits Hermes to observe+summarize.

## Nemesis Security Review

### Pass 1 — Trust Boundaries

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| H1 | Daemon HTTP endpoints have no auth — Hermes adapter is bypassable | HIGH | Documented as M1 limitation |
| H2 | Authority token format undefined — no encoding, signing, or claim validation | MEDIUM | Resolved: simplified to pairing-based auth for M1 |
| H3 | `create_pairing_token()` sets expiration to creation time (born expired) | MEDIUM | **Fixed in this review** (24h TTL) |
| H4 | No write-path enforcement beyond adapter code — direct spine calls not gated | LOW | Acceptable: in-process adapter, not a network boundary |
| H5 | Spec says "read-only access to user messages" but plan blocks them entirely | LOW | **Fixed in this review** (updated hermes-adapter.md) |

### Pass 2 — Coupled State & Protocol Surfaces

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| H6 | Hermes pairing shares store namespace with gateway devices — collision possible | MEDIUM | Must resolve before implementation |
| H7 | `get_events` loads full spine on every call — O(n) per Hermes poll | LOW | Acceptable for M1 scale |
| H8 | No replay protection on summary append — duplicate summaries possible | LOW | Acceptable: append-only model, UX concern only |
| H9 | `authority_scope` type mismatch (str vs list) | LOW | Resolved in spec |
| H10 | Hermes auth header is plaintext hermes_id — LAN-spoofable | MEDIUM | Documented as M1 limitation |

### Verdict on Security Posture

The adapter's security model is honest for M1 LAN-only deployment. The critical gap (H1: no daemon auth) means the capability boundary is a *logical contract*, not a *cryptographic enforcement*. This is acceptable given:
- M1 is explicitly LAN-only (DESIGN.md, product spec)
- The adapter establishes the *interface* that M2 will harden
- The plan correctly identifies all M2 security requirements

**Not acceptable for M2 or any network-facing deployment** without:
- Daemon-level auth middleware on all routes
- Signed authority tokens with embedded claims
- Hermes namespace separation in the pairing store

## Source Fixes Made During Review

### Fix 1: `store.py` — Token expiration bug

`services/home-miner-daemon/store.py:create_pairing_token()` set `token_expires_at` to `datetime.now()` (instant expiration). Changed to `datetime.now() + timedelta(hours=24)`.

**Rationale:** Every pairing token was born expired. The Hermes adapter plan depends on token expiration checking. 24h matches LAN-only trust model.

### Fix 2: `references/hermes-adapter.md` — Spec contradiction

Line 73 said "Read-only access to user messages." Changed to "No access to user_message events (filtered at the adapter layer)."

**Rationale:** The plan's event filter blocks user_message entirely. The reference contract should match the stricter behavior, which is the correct security posture for an AI agent.

## Remaining Blockers Before Implementation

1. **H6: Pairing namespace collision.** Decide whether Hermes pairings live in the same store as gateway pairings (with a type discriminator) or in a separate store. Implementation cannot begin on the pairing endpoint until this is resolved.

2. **Plan file not on disk.** `genesis/plans/009-hermes-adapter-implementation.md` doesn't exist. The plan should be committed before implementation so the implementer has a self-contained reference.

3. **Specify stage produced nothing.** The MiniMax run generated 0 tokens. The spec artifact (`outputs/hermes-adapter-implementation/spec.md`) has been written by this review to fill the gap.

## Recommendation

**CONDITIONAL APPROVAL — plan is sound, resolve H6 namespace collision, then proceed to Milestone 1.**

The plan's architecture is correct: in-process adapter, capability-scoped, event-filtered. The security posture is honest for M1. Three issues were found and resolved during review (H3 token bug, H5 spec contradiction, H9 type mismatch). One issue (H6 namespace collision) requires a design decision before the pairing endpoint can be implemented.

After H6 is resolved, implementation should proceed in plan order: adapter module first, then daemon endpoints, then client update, then tests.
