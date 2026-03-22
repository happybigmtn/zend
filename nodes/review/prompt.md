Goal: Hermes Adapter Implementation

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Create hermes.py adapter module
- Implement HermesConnection with authority token validation
- Implement readStatus through adapter
- Implement appendSummary through adapter
- Implement event filtering (block user_message events for Hermes)
- Add Hermes pairing endpoint to daemon

Required durable artifacts:
- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7-highspeed, 65.7k tokens in / 431 out
  - Files: outputs/hermes-adapter-implementation/review.md, outputs/hermes-adapter-implementation/spec.md, services/home-miner-daemon/daemon.py, services/home-miner-daemon/hermes.py, services/home-miner-daemon/tests/test_hermes.py


# Hermes Adapter Implementation Lane — Review

Review the lane outcome for `hermes-adapter-implementation`.

Focus on:
- correctness
- milestone fit
- remaining blockers

If a small direct source fix is needed to make the review judgment truthful and unblock the lane, you may make it, but stay inside the touched surfaces.


Lane context:
Plan file:
- `genesis/plans/009-hermes-adapter-implementation.md`

Full plan context (read this for domain knowledge, design decisions, and specifications):

# Hermes Adapter Implementation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `genesis/PLANS.md`.

## Purpose / Big Picture

After this work, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the inbox, and verify that control attempts are rejected. This is the first step toward agent parity: Hermes uses the same API primitives as human clients but with a narrower capability scope.

Depends on plan 006 (token auth) for token issuance and plan 007 (observability) for structured logging of Hermes events.

## Progress

- [ ] Create hermes.py adapter module
- [ ] Implement HermesConnection with authority token validation
- [ ] Implement readStatus through adapter
- [ ] Implement appendSummary through adapter
- [ ] Implement event filtering (block user_message events for Hermes)
- [ ] Add Hermes pairing endpoint to daemon
- [ ] Update CLI with Hermes subcommands
- [ ] Update gateway client Agent tab with real connection state
- [ ] Write tests for adapter boundary enforcement

## Surprises & Discoveries

(To be updated during implementation.)

## Decision Log

- Decision: Hermes adapter is a Python module in the daemon, not a separate service.
  Rationale: The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`.
  Rationale: Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

(To be updated at completion.)

## Context and Orientation

The Hermes adapter contract is fully specified at `references/hermes-adapter.md`. The output specification is at `outputs/hermes-adapter/agent-adapter.md`. The adapter sits between the external Hermes agent and the Zend gateway contract:

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILD
```

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

Currently, the Agent tab in `apps/zend-home-gateway/index.html` shows "Hermes not connected" as a placeholder. The smoke test at `scripts/hermes_summary_smoke.sh` exists but has no real adapter to test against.

## Plan of Work

### Milestone 1: Adapter Module (days 1–5)

Create `services/home-miner-daemon/hermes.py` implementing the adapter interface:

    from dataclasses import dataclass
    from datetime import datetime, timezone
    from typing import List, Optional
    from spine import append_event, get_events, EventKind
    from store import get_pairing_by_device, is_token_expired

    @dataclass
    class HermesConnection:
        hermes_id: str
        principal_id: str
        capabilities: List[str]  # ['observe', 'summarize']
        connected_at: str

    HERMES_CAPABILITIES = ['observe', 'summarize']
    HERMES_READABLE_EVENTS = [
        EventKind.HERMES_SUMMARY,
        EventKind.MINER_ALERT,
        EventKind.CONTROL_RECEIPT,
    ]

    def connect(authority_token: str) -> HermesConnection:
        """Validate authority token and establish Hermes connection.
        Raises ValueError if token is invalid, expired, or has wrong capabilities."""
        # Validate token structure, expiration, capabilities
        ...

    def read_status(connection: HermesConnection) -> dict:
        """Read miner status through adapter. Requires observe capability."""
        if 'observe' not in connection.capabilities:
            raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
        # Delegate to daemon's status endpoint internally
        ...

    def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None:
        """Append a Hermes summary to the event spine. Requires summarize capability."""
        if 'summarize' not in connection.capabilities:
            raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
        append_event(
            principal_id=connection.principal_id,
            kind=EventKind.HERMES_SUMMARY,
            payload={
                "summary_text": summary_text,
                "authority_scope": authority_scope,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
        """Return events Hermes is allowed to see. Filters out user_message."""
        all_events = get_events(limit=limit * 2)  # over-fetch to account for filtering
        return [e for e in all_events if e["kind"] in [k.value for k in HERMES_READABLE_EVENTS]][:limit]

Proof:

    python3 -c "
    from services.home_miner_daemon.hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
    print('Capabilities:', HERMES_CAPABILITIES)
    print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
    "
    # Expected: Capabilities: ['observe', 'summarize']
    # Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']

### Milestone 2: Daemon Endpoints (days 5–8)

Add Hermes-specific endpoints to `daemon.py`:

- `POST /hermes/connect` — Accepts authority token, returns connection status
- `GET /hermes/status` — Read miner status through adapter (requires Hermes auth)
- `POST /hermes/summary` — Append a summary to the spine (requires Hermes auth)
- `GET /hermes/events` — Read filtered events (no user_message)

The auth model for Hermes uses a separate `Authorization: Hermes <hermes_id>` header scheme to distinguish from gateway device auth.

Add Hermes pairing: `POST /hermes/pair` creates a Hermes pairing record in the store with observe+summarize capabilities. This uses the same store mechanism as device pairing but with a different capability set.

Proof:

    # Pair Hermes
    curl -s -X POST http://127.0.0.1:8080/hermes/pair \
      -H "Content-Type: application/json" \
      -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
    # Expected: {"hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

    # Append summary
    curl -s -X POST http://127.0.0.1:8080/hermes/summary \
      -H "Authorization: Hermes hermes-001" \
      -H "Content-Type: application/json" \
      -d '{"summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe"}'
    # Expected: {"appended": true, ...}

    # Read filtered events (should see the summary, not user_messages)
    curl -s http://127.0.0.1:8080/hermes/events \
      -H "Authorization: Hermes hermes-001"
    # Expected: events list containing hermes_summary, no user_message

    # Attempt control (should fail)
    curl -s -X POST http://127.0.0.1:8080/miner/start \
      -H "Authorization: Hermes hermes-001"
    # Expected: 403 HERMES_UNAUTHORIZED

### Milestone 3: Client Update (days 8–10)

Update `apps/zend-home-gateway/index.html` Agent tab:

- Replace "Hermes not connected" with actual connection state from `GET /hermes/status`
- Show Hermes capabilities as pills (observe, summarize)
- Show recent Hermes summaries from spine events
- Show connection timestamp

Proof: Open the Agent tab in the browser. After Hermes is paired and a summary is appended, the tab shows the connection state and the summary text.

### Milestone 4: Tests (days 10–12)

Write `services/home-miner-daemon/tests/test_hermes.py`:

1. `test_hermes_connect_valid` — connect with valid token succeeds
2. `test_hermes_connect_expired` — connect with expired token fails
3. `test_hermes_read_status` — observe capability reads status
4. `test_hermes_append_summary` — summarize capability appends to spine
5. `test_hermes_no_control` — Hermes cannot call /miner/start
6. `test_hermes_event_filter` — user_message events not returned
7. `test_hermes_invalid_capability` — requesting control capability rejected
8. `test_hermes_summary_appears_in_inbox` — appended summary visible via /spine/events

Proof:

    python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v
    # Expected: 8 tests passed, 0 failed

## Validation and Acceptance

1. Hermes can connect with authority token
2. Hermes can read miner status
3. Hermes can append summaries to event spine
4. Hermes CANNOT issue control commands (403)
5. Hermes CANNOT read user_message events (filtered)
6. Agent tab shows real connection state
7. All tests pass
8. `scripts/hermes_summary_smoke.sh` passes against live daemon

## Idempotence and Recovery

Hermes pairing is idempotent (same hermes_id re-pairs). Summary append is append-only. All operations can be safely repeated.

## Interfaces and Dependencies

New files:
- `services/home-miner-daemon/hermes.py`
- `services/home-miner-daemon/tests/test_hermes.py`

New endpoints in `daemon.py`:
- `POST /hermes/connect`
- `POST /hermes/pair`
- `GET /hermes/status`
- `POST /hermes/summary`
- `GET /hermes/events`

No external dependencies.


Active plan:
- `genesis/plans/001-master-plan.md`

Active spec:
- `genesis/SPEC.md`

Mapping notes:
- composite plan mapped from plan structure; humans may refine the checked-in contract later

Open tasks:
- Create hermes.py adapter module
- Implement HermesConnection with authority token validation
- Implement readStatus through adapter
- Implement appendSummary through adapter
- Implement event filtering (block user_message events for Hermes)
- Add Hermes pairing endpoint to daemon
- Update CLI with Hermes subcommands
- Update gateway client Agent tab with real connection state

Artifacts to write:
- `spec.md`
- `review.md`


Nemesis-style security review
- Pass 1 — first-principles challenge: question trust boundaries, authority assumptions, and who can trigger the slice's dangerous actions
- Pass 2 — coupled-state review: identify paired state or protocol surfaces and check that every mutation path keeps them consistent or explains the asymmetry
- check state transitions that affect balances, commitments, randomness, payout safety, or replayability
- check secret handling, capability scoping, pairing/idempotence behavior, and privilege escalation paths
- check external-process control, operator safety, idempotent retries, and failure modes around service lifecycle