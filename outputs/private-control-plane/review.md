# Zend Private Control Plane Review

**Status:** Honest reviewed slice
**Reviewed:** 2026-03-20

## Findings

### 1. High: the local event spine is still plaintext at rest

The milestone 1 contract now correctly routes operational events through one
append-only spine, but the runtime file is not encrypted yet. `SpineEvent`
records are written directly with `json.dumps(asdict(event))` in
`services/home-miner-daemon/spine.py`, so the current slice does not yet satisfy
the full private-data promise from the product spec.

### 2. Medium: inbox routing exists as a backend projection, not an end-to-end inbox surface

This lane now encodes inbox routing in `SURFACE_ROUTES_BY_KIND` and exposes it
through `cli.py events --surface inbox`, which is good milestone progress.
However, `apps/zend-home-gateway/index.html` still only talks to the daemon
status and control endpoints. It does not yet read the spine projection, so the
operations inbox is not wired through to the current UI.

### 3. Medium: pairing-token lifecycle is still placeholder metadata

`services/home-miner-daemon/store.py` now records `token_expires_at` and
`token_used`, but the current slice still does not persist or validate a raw
pairing secret. This means replay protection and a real trust-ceremony token
exchange are still deferred.

## Confirmed In This Slice

- Shared principal contract: pairing records and event-spine events reuse the
  same `PrincipalId`.
- Capability scope contract: only `observe` and `control` are accepted, and
  observe-only clients are denied control.
- Inbox contract: inbox items are defined as a projection of the spine rather
  than a separate canonical store.
- Reference alignment: `references/inbox-contract.md` and
  `references/event-spine.md` now match the current runtime shape.

## Validation Performed

The sandbox does not permit binding a local listening socket, so I could not
exercise the HTTP daemon end to end. I validated the lane at the module and CLI
level instead.

Commands run:

```bash
python3 -m py_compile services/home-miner-daemon/*.py

bash -n scripts/bootstrap_home_miner.sh \
  scripts/pair_gateway_client.sh \
  scripts/read_miner_status.sh \
  scripts/set_mining_mode.sh \
  scripts/hermes_summary_smoke.sh \
  scripts/no_local_hashing_audit.sh

ZEND_STATE_DIR="$(mktemp -d /tmp/zend-pcp-XXXXXX)" \
  python3 services/home-miner-daemon/cli.py pair \
    --device review-phone \
    --capabilities observe,control

ZEND_STATE_DIR="$(mktemp -d /tmp/zend-pcp-XXXXXX)" \
  python3 services/home-miner-daemon/cli.py events --surface inbox --limit 10
```

Representative results:

- Valid pairing returns normalized capabilities: `["observe", "control"]`
- Invalid capability `admin` now raises:
  `Unsupported capability 'admin'. Allowed values: observe, control`
- Observe-only control attempt returns:
  `{"success": false, "error": "unauthorized", ...}`
- Inbox projection returns spine-backed `pairing_granted`,
  `control_receipt`, and `hermes_summary` events

## Milestone Fit

This lane now satisfies the bootstrap goal for an honest reviewed slice:

- the shared `PrincipalId` contract is explicit and implemented
- pairing records are capability-scoped and enforced for milestone 1
- the private event spine is the canonical operational write path
- operations inbox routing is encoded as a real projection helper

The slice is still intentionally partial. It is a contract-ready control-plane
foundation, not the finished private inbox product.

## Remaining Blockers

- Encrypt event-spine payloads at rest or make the local-storage threat model
  explicit and temporary.
- Expose the inbox projection through the daemon and consume it in the mobile
  command-center client.
- Implement real pairing-token issue, transport, consumption, and replay
  protection.
- Add automated tests for pairing replay, spine routing, and authorization
  boundaries once the daemon can be exercised in CI or a less restricted
  sandbox.

## Verdict

Approved as the first honest reviewed slice for `private-control-plane`.
The contract boundary is now real and repo-specific, and the remaining gaps are
clear enough for the next lanes to build on without pretending the privacy story
is already complete.
