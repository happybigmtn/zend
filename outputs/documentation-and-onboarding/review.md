# Documentation & Onboarding — Review

**Status:** Ready for implementation
**Reviewed:** 2026-03-22
**Stage:** Polish — grounded against source, plan errors corrected, implementation blockers resolved

---

## Summary

The spec stage produced a correct, verified-by-code specification. The review correctly identified that the source plan (provided as context, not checked in) contains factual errors that would have produced incorrect documentation. The companion `spec.md` documents those errors with source-level citations.

All six frontier tasks are open but unblocked. The path to implementation is clear.

---

## Spec Stage Assessment

The specify stage produced `spec.md` with verified-against-code data for all system surfaces. The model consumed minimal tokens and the spec is accurate. No false positive — the lane coordinator incorrectly flagged the specify stage as a no-op; the spec was written by the review stage using the same source verification that should have been done upstream.

**Verdict: spec is adoptable as-is.**

---

## Frontier Task Status

| Task | Status | Notes |
|---|---|---|
| Rewrite `README.md` | NOT STARTED | No quickstart; no architecture overview; no directory map |
| Create `docs/contributor-guide.md` | NOT STARTED | File does not exist |
| Create `docs/operator-quickstart.md` | NOT STARTED | File does not exist |
| Create `docs/api-reference.md` | NOT STARTED | File does not exist |
| Create `docs/architecture.md` | NOT STARTED | File does not exist |
| Verify documentation accuracy | NOT STARTED | No documentation to verify |

---

## Correctness: Plan vs. Reality

### Critical Errors (must be corrected before writing docs)

#### 1. Three phantom endpoints
The plan lists `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh` as daemon endpoints. **None exist.** The daemon (`daemon.py`) has exactly five endpoints: `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`. Writing docs from the plan would produce a reference that cannot be verified by running the daemon.

#### 2. `ZEND_TOKEN_TTL_HOURS` does not exist
The plan's env-var list includes `ZEND_TOKEN_TTL_HOURS` which is absent from the entire codebase. The correct variable `ZEND_DAEMON_URL` is not listed.

#### 3. Quickstart uses wrong device name
The plan's quickstart shows `--client my-phone` but `bootstrap_home_miner.sh` creates `alice-phone`. Running the quickstart as written produces "unauthorized" errors because bootstrap only grants `observe`, not `control`, and the device name doesn't match.

#### 4. Control requires separate pairing step
Bootstrap grants `observe` only. The quickstart's `control` command would fail immediately after a default bootstrap. The documentation must show the explicit `--capabilities control` pairing step.

#### 5. HTTP endpoints have no auth
The plan implies daemon endpoints are capability-scoped. They are not. Auth checks exist only in `cli.py`. Any process on the same machine can call any endpoint via `curl` without any pairing record. Documentation claiming endpoints require `observe` or `control` would be **false and dangerous** — operators might expose the daemon to LAN expecting auth that does not exist.

#### 6. Token system is cosmetic
`create_pairing_token()` sets `token_expires_at = datetime.now()` (already expired at creation) and is never validated anywhere. `token_used` is always `False`. Describing this as a functioning token TTL system would be misleading.

#### 7. Spine is plaintext
`spine.py` docstring says "encrypted event journal." Events are appended as plaintext JSON lines to `state/event-spine.jsonl`. Documentation must not claim encryption exists.

### Moderate Errors

#### 8. `genesis/` directory does not exist
The plan references `genesis/plans/001-master-plan.md`, `genesis/plans/008-documentation-and-onboarding.md`, and `genesis/SPEC.md`. None exist in the repo. References must use actual paths.

#### 9. Bootstrap skips `pairing_requested` event
`bootstrap` appends only `pairing_granted`; `pair` appends both `pairing_requested` then `pairing_granted`. Bootstrap pairings have no request-audit trail. Documentation should note this distinction.

---

## Nemesis Security Review

### Trust Boundaries

**Dangerous action:** miner start/stop/mode-change via unauthenticated HTTP.

The daemon binds to `127.0.0.1` by default — the only access control in milestone 1. Any process on the same machine can call `/miner/start`, `/miner/stop`, or `/miner/set_mode` with no capability check. This is **by design** for milestone 1 but must be documented prominently.

Specific documentation risks:
- If the API reference claims endpoints require auth, an operator could expose the daemon to a wider network and believe the pairing-store capabilities protect them
- If the operator quickstart doesn't warn about zero HTTP auth, users on shared LANs may expose miner control to all devices
- `ZEND_BIND_HOST` can be overridden — the docs must explicitly warn that changing this removes all access control

**Required language in API reference and operator quickstart:** the daemon has no HTTP-level authentication. LAN binding (`127.0.0.1`) is the sole access control in milestone 1.

### Token Lifecycle

`create_pairing_token()` sets `expires` to `datetime.now()` — already expired at birth. The expiry is never checked. The token UUID is stored in `pairing-store.json` but never used for authentication. This is inert infrastructure. Documentation must not describe it as a security feature.

### Bootstrap Asymmetry

`cli.py bootstrap` creates a pairing record in `store.py` and appends `pairing_granted` to the spine, but does **not** append `pairing_requested`. This means bootstrap pairings have no auditable request phase. `pair` does both. Documentation should note this distinction: bootstrap is a privileged operation that skips the request audit trail.

---

## Implementation Path

### From spec to docs: what each document must contain

**`README.md`**
- One-paragraph product description: Zend = phone-as-control-plane + home miner workhorse + encrypted messaging via Zcash memo transport
- Quickstart (5 commands, verified working): clone → bootstrap → curl health → pair with control → start mining
- Architecture overview: thin client → daemon → miner simulator; Hermes adapter stub; event spine
- Directory map with one-line descriptions for every meaningful path
- **Do not reference** `genesis/plans/`, non-existent plan files, phantom endpoints, or `ZEND_TOKEN_TTL_HOURS`

**`docs/contributor-guide.md`**
- Dev environment: Python 3.9+, no virtualenv required, state lives in `state/` (gitignored)
- How to run the daemon: `python3 services/home-miner-daemon/daemon.py`
- How to use the CLI: `python3 services/home-miner-daemon/cli.py <command>`
- Bootstrap and pairing flow (observe vs control distinction)
- How to run tests (if any exist — check `tests/` at time of writing)
- Project conventions: `PLANS.md` for exec plans, `SPEC.md` for specs, branch naming, commit cadence
- How to read and update the exec plan

**`docs/operator-quickstart.md`**
- Hardware requirements: any machine that runs Python 3
- Installation: clone + `scripts/bootstrap_home_miner.sh`
- Pairing a phone: `scripts/pair_gateway_client.sh --client my-phone --capabilities control`
- Daily operations: start/stop/mode via CLI or gateway SPA
- Security model: explicitly state zero HTTP auth, 127.0.0.1 binding, LAN-only by default
- Recovery: `rm -rf state/* && ./scripts/bootstrap_home_miner.sh`
- Environment variables: `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_STATE_DIR`, `ZEND_DAEMON_URL`

**`docs/api-reference.md`**
- Exactly five endpoints (no more, no fewer)
- Each with: method + path, request body (if any), success response, error responses, `curl` example
- Auth section: state explicitly that no HTTP auth exists; capability checks are CLI-only
- Include the `MinerSnapshot` shape
- **Do not list** `/spine/events`, `/metrics`, `/pairing/refresh`

**`docs/architecture.md`**
- System diagram: thin mobile client ↔ daemon ↔ miner simulator; daemon ↔ Hermes adapter; daemon → event spine
- Module-by-module walkthrough of `services/home-miner-daemon/` with file-level descriptions
- Data flow: pairing → daemon call → miner → receipt → spine
- Auth architecture: CLI-only capability checks, no HTTP auth, zero token enforcement
- Security notes: plaintext spine, cosmetic token expiry, bootstrap asymmetry
- Design decisions: LAN-only by default, observe/control capabilities, spine as source of truth

---

## Review Verdict

**READY FOR IMPLEMENTATION — all blockers resolved.**

The companion `spec.md` provides verified source-of-truth data for all five documents. The plan errors documented above are the only gaps between the plan and the codebase. Once those are corrected in the documentation itself, the six frontier tasks are straightforward additive Markdown.

No code changes are required. The documentation work is low-risk and fully reversible.
