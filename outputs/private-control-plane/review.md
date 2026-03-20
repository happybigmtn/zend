# Private Control Plane Review

**Lane:** `private-control-plane`  
**Reviewed on:** 2026-03-20  
**Verdict:** useful baseline, not yet milestone-1 complete

## Findings

- High: The daemon does not yet enforce pairing-derived authority, and the web
  client bypasses the pairing contract entirely. `services/home-miner-daemon/daemon.py:168-199`
  serves `/status` and `/miner/*` without consulting the pairing store, while
  `apps/zend-home-gateway/index.html:621-790` hard-codes
  `capabilities: ['observe', 'control']` and calls those endpoints directly.
  That means capability-scoped pairing exists in the store and CLI path, but it
  is not yet the end-to-end security boundary for the actual client surface.

- Medium: The operations inbox is not yet routed from the private event spine
  into the user-visible UI. `apps/zend-home-gateway/index.html:537-559` renders
  static `Latest Receipt` and `Inbox` placeholders, and a search for event
  reads in that file only finds the placeholder element IDs, not a projection
  path. The storage contract is present, but the milestone-1 inbox experience
  is still a stub.

- Medium: The event-spine implementation still drifts from the written
  contract. `references/event-spine.md:46-52` says `pairing_granted` carries a
  `pairing_token`, and `references/event-spine.md:107-109` says payloads are
  encrypted. In code, `services/home-miner-daemon/store.py:108-112` creates a
  token but does not persist it in the pairing record payload, and
  `services/home-miner-daemon/spine.py:62-79` appends plaintext JSONL. The
  spine boundary is real, but the encrypted-journal promise is not yet met.

- Medium: Pairing-token state is still only scaffolding.
  `services/home-miner-daemon/store.py:108-142` stores `token_expires_at` and
  `token_used`, but the token lifetime is currently just the creation timestamp
  and there is no replay or expiry enforcement path. That is acceptable for a
  docs-and-scaffold baseline, but not for a complete trust ceremony.

## What Landed

- The minimal inbox architecture contract exists. `references/inbox-contract.md:14-21`
  defines one shared `PrincipalId` across pairing records, event-spine items,
  and future inbox metadata.

- The private event spine exists as a real append-only store.
  `services/home-miner-daemon/spine.py:68-173` can append milestone-1 event
  kinds, and `services/home-miner-daemon/cli.py:170-187` now supports filtered
  event reads without crashing.

- Capability-scoped pairing records exist and now enforce the milestone-1 scope
  vocabulary. `services/home-miner-daemon/store.py:30-71` limits pairings to
  `observe` and `control`, and `services/home-miner-daemon/store.py:115-142`
  persists those validated records under one principal.

## Validation Evidence

I validated the non-network portions of the lane in an isolated temp state
directory because the sandbox does not permit binding a local HTTP socket.

Working directory:

    /tmp/zend-private-control-3-1773983349/worktree/services/home-miner-daemon

Commands run:

    export ZEND_STATE_DIR="$(mktemp -d /tmp/zend-pcp-verify-XXXXXX)"
    python3 cli.py bootstrap --device review-owner
    python3 cli.py pair --device controller-phone --capabilities observe,control
    python3 cli.py pair --device weird-phone --capabilities observe,admin
    python3 cli.py control --client controller-phone --action start
    python3 cli.py events --kind control_receipt --limit 20

Observed results:

- `bootstrap` created one principal and one pairing record under that principal.
- `pair --capabilities observe,control` succeeded.
- `pair --capabilities observe,admin` now fails with
  `Unsupported capability 'admin'. Milestone 1 supports only observe,control`.
- `control --client controller-phone --action start` returned
  `daemon_unavailable` in the sandbox, but still appended a rejected
  `control_receipt` into the spine.
- `events --kind control_receipt` now returns the filtered event instead of
  raising `AttributeError`.

## Milestone Fit

The lane now has a credible first reviewed slice:

- shared principal boundary: present
- private event spine boundary: present, but not encrypted
- capability-scoped pairing record: present in store and CLI paths

The lane is not ready to claim milestone-1 completion because the end-user
client and daemon still do not honor the authority boundary all the way through,
and the inbox UI still does not project the spine.

## Next Blockers

- Move capability enforcement from the CLI wrapper into the daemon-facing
  contract so every client path, including the web UI, is gated by the pairing
  record.
- Add a spine-backed inbox projection so `Latest Receipt` and `Inbox` render
  real pairing, receipt, alert, and Hermes events.
- Replace plaintext local event storage with the encrypted payload model the
  spec already promises.
- Finish the pairing-token lifecycle with persisted token material, expiry, and
  replay protection.
