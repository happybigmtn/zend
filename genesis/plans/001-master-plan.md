# Master Execution Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

Zend is an agent-first product that combines encrypted Zcash-based messaging with a mobile gateway into a home miner. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device. The first implementation slice is a thin mobile-shaped command center with an event-backed operations inbox.

## Progress

- [x] (2026-03-19) Bootstrap project structure and specs
- [x] (2026-03-19) Define canonical design system (DESIGN.md)
- [x] (2026-03-19) Define event spine contract
- [x] (2026-03-19) Define product capability spec
- [ ] Implement event spine daemon service
- [ ] Implement Zend home gateway client
- [ ] Implement Hermes adapter for AI summaries
- [ ] Implement secure remote access
- [ ] Implement inbox and conversation UX
- [ ] Write comprehensive tests

## Surprises & Discoveries

- Discovery: The event spine must be the single source of truth; inbox is a derived view.
  Evidence: All events flow through spine; inbox is filtered projection.
- Discovery: Mobile-first requires careful touch target sizing (44px minimum).
  Evidence: Bottom navigation uses min-height: 44px per DESIGN.md.

## Decision Log

- Decision: Use append-only JSONL for event spine storage.
  Rationale: Simple, auditable, no database dependency. File-based append is atomic enough for single-writer local daemon.
  Date/Author: 2026-03-19 / Project Bootstrap

- Decision: Client-side routing for inbox vs. server-side filtering.
  Rationale: The event spine contract explicitly states "inbox is a derived view." Client applies routing rules; no separate inbox API.
  Date/Author: 2026-03-19 / Project Bootstrap

## Outcomes & Retrospective

(To be updated as work proceeds.)

## Context and Orientation

The Zend project has the following key components:

- `services/home-miner-daemon/`: Python daemon managing the miner and event spine
- `apps/zend-home-gateway/`: Mobile-first HTML/JS client
- `references/event-spine.md`: Contract for event storage and routing
- `DESIGN.md`: Visual design system
- `SPEC.md`: Spec writing guide

## Plan of Work

### Phase 1: Foundation
1. Event spine daemon service
2. Basic gateway client with Home tab

### Phase 2: Operations
3. Inbox and conversation UX
4. Hermes adapter

### Phase 3: Remote Access
5. Secure remote access
6. Full integration

### Phase 4: Polish
7. Comprehensive tests
8. Performance validation

## Interfaces and Dependencies

- Daemon exposes: `GET /status`, `GET /spine/events`, `POST /miner/set_mode`, `POST /miner/start`, `POST /miner/stop`
- Gateway client: Single-page HTML/JS with tab navigation
- Event spine: JSONL file with UUID-identified events

## Validation

Each phase produces demonstrable working behavior:
1. Daemon responds to health checks
2. Gateway shows miner status and mode controls
3. Inbox shows filtered events with warm empty states
4. Hermes summaries appear in Agent tab
5. Remote access works from outside LAN
6. All tests pass
